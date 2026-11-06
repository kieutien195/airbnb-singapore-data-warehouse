import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import yaml
from sqlalchemy import create_engine, event, text

from etl import ingest, transform
from etl.clean import clean_calendar, clean_listings, clean_reviews

SNAPSHOT = "2026-09-23"


class EtlRegressionTest(unittest.TestCase):
    def test_calendar_rejects_bad_inputs_and_preserves_bigint(self):
        row = dict(listing_id="1371380025584025715", date="2026-09-25",
                   available="f", minimum_nights=1, maximum_nights=20)
        changes = [
            {"available": "INVALID"}, {"minimum_nights": None},
            {"maximum_nights": 0}, {"date": "2026-02-30"}, {"listing_id": "bad"},
        ]
        df = pd.DataFrame([row, *(row | change for change in changes)])
        clean, rejected, audit = clean_calendar(df, SNAPSHOT)
        self.assertEqual(clean["listing_id"].tolist(), [1371380025584025715])
        self.assertEqual(clean["is_available"].tolist(), [0])
        self.assertEqual(len(rejected), 5)
        self.assertEqual(audit["rejected_rows"], 5)

    def test_listings_quarantines_invalid_rating_price_and_accommodates(self):
        row = dict(id="1371380025584025715", scrape_id="20260923225116",
                   host_id="1234", last_scraped=SNAPSHOT, room_type="Private room",
                   neighbourhood_cleansed="Bedok", neighbourhood_group_cleansed="East Region",
                   latitude="1.3", longitude="103.9", accommodates=2, number_of_reviews=0,
                   review_scores_rating=None, minimum_nights=None, maximum_nights=None,
                   minimum_nights_avg_ntm=None, maximum_nights_avg_ntm=None,
                   price=None, price_quote_raw=None)
        changes = [{"review_scores_rating": 6}, {"price": "inf"}, {"accommodates": None}]
        df = pd.DataFrame([row, *(row | change for change in changes)])
        clean, rejected, audit = clean_listings(df, SNAPSHOT)
        self.assertTrue(clean["review_scores_rating"].isna().all())
        self.assertTrue(clean["listed_price_sgd"].isna().all())
        self.assertEqual(len(clean), 1)
        self.assertEqual(len(rejected), 3)
        self.assertEqual(audit["rejected_rows"], 3)

    def test_reviews_reject_missing_reviewer_and_keep_composite_grain(self):
        row = dict(listing_id="1", id="10", reviewer_id="3", date=SNAPSHOT,
                   reviewer_name="Test", comments=None)
        df = pd.DataFrame([row, row | {"listing_id": "2"}, row | {"reviewer_id": None}])
        clean, rejected, _ = clean_reviews(df, SNAPSHOT)
        self.assertEqual(clean["listing_id"].tolist(), [1, 2])
        self.assertEqual(len(rejected), 1)

    def test_coverage_counts_rows_and_gold_is_not_written_on_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("gold", "silver"):
                (root / name).mkdir()
            old_gold = root / "gold" / "dim_date.csv"
            old_gold.write_text("previous output", encoding="utf-8")
            frames = {
                "listings": pd.DataFrame({
                    "id": [1, 2], "neighbourhood_group_cleansed": ["East", "East"],
                    "neighbourhood_cleansed": ["Bedok", "New"],
                }),
                "calendar": pd.DataFrame({"listing_id": [3], "calendar_date_sk": [20260925]}),
                "reviews": pd.DataFrame({"listing_id": [1], "review_date_sk": [20260922]}),
                "neighbourhoods": pd.DataFrame({"neighbourhood_group": ["East"], "neighbourhood_name": ["Bedok"]}),
            }
            for name, frame in frames.items():
                frame.assign(snapshot_date=SNAPSHOT, snapshot_date_sk=20260923).to_csv(
                    root / "silver" / f"silver_{name}.csv", index=False
                )
            config = root / "config.yaml"
            config.write_text(yaml.safe_dump({
                "project": {"snapshot_date": SNAPSHOT},
                "paths": {key + "_dir": str(root / key) for key in ("gold", "silver", "outputs")},
            }), encoding="utf-8")
            with patch.object(transform, "PROJECT_ROOT", root):
                with self.assertRaisesRegex(RuntimeError, "Gold coverage failed"):
                    transform.run_transform_pipeline(config)
            self.assertEqual(old_gold.read_text(encoding="utf-8"), "previous output")
            self.assertEqual(len(list((root / "gold").iterdir())), 1)
            coverage = pd.read_csv(root / "outputs/join_coverage.csv").set_index("relationship_id")
            self.assertEqual(coverage.loc["REL-03", "orphan_records"], 1)
            self.assertEqual(coverage.loc["REL-03", "status"], "WARN")
            orphans = pd.read_csv(root / "outputs/etl_orphan_records.csv")
            self.assertEqual(orphans["listing_id"].tolist(), [3])

    def test_failed_second_chunk_rolls_back_partition_and_retry_replaces_it(self):
        # SQLite supplies real transactions. Stub only the MySQL advisory lock functions.
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)

        @event.listens_for(engine, "connect")
        def add_lock_functions(connection, _):
            connection.create_function("GET_LOCK", 2, lambda *_: 1)
            connection.create_function("RELEASE_LOCK", 1, lambda *_: 1)

        with engine.begin() as conn:
            conn.execute(text("""CREATE TABLE stg_calendar (
                listing_id INTEGER CHECK (listing_id > 0), snapshot_date TEXT,
                source_file TEXT, ingested_at TEXT
            )"""))
            conn.execute(text("INSERT INTO stg_calendar VALUES (99, :date, '', '')"), {"date": SNAPSHOT})
            conn.execute(text("INSERT INTO stg_calendar VALUES (98, '2026-09-22', '', '')"))

        with tempfile.TemporaryDirectory() as folder, patch.object(ingest, "log_ingest_result"):
            root = Path(folder)
            file = root / "calendar.csv"
            project = {"paths": {"raw_dir": folder, "staging_dir": folder},
                       "project": {"snapshot_date": SNAPSHOT}}
            source = {"file_name": file.name, "staging_table": "stg_calendar", "chunk_size": 1}

            file.write_text("listing_id\n1\n-1\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "CHECK constraint failed"):
                ingest.ingest_source("calendar", source, project, engine=engine)
            self.assertFalse((root / "stg_calendar.csv").exists())
            with engine.connect() as conn:
                self.assertEqual(conn.execute(text("SELECT listing_id FROM stg_calendar ORDER BY 1")).scalars().all(), [98, 99])

            file.write_text("listing_id\n1\n2\n", encoding="utf-8")
            for _ in range(2):
                result = ingest.ingest_source("calendar", source, project, engine=engine)
                self.assertEqual(result["status"], "SUCCESS")
            with engine.connect() as conn:
                self.assertEqual(conn.execute(text("SELECT listing_id FROM stg_calendar ORDER BY 1")).scalars().all(), [1, 2, 98])


if __name__ == "__main__":
    unittest.main()
