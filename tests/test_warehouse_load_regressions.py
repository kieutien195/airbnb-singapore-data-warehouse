import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from scripts import load_warehouse as loader
from scripts.verify_warehouse_schema import normalize_check, verify_checks


class WarehouseLoadTest(unittest.TestCase):
    def test_same_check_name_with_different_expression_fails(self):
        expected = {"chk": normalize_check("rating IS NULL OR (rating BETWEEN 1.00 AND 5.00)")}
        verify_checks("fact", expected, [("chk", "((`rating` is null) or (`rating` between 1 and 5))", "YES")])
        with self.assertRaisesRegex(RuntimeError, "CHECK expressions differ"):
            verify_checks("fact", expected, [("chk", "rating IS NULL OR rating BETWEEN 1 AND 6", "YES")])
        with self.assertRaisesRegex(RuntimeError, "not enforced"):
            verify_checks("fact", expected, [("chk", "rating IS NULL OR rating BETWEEN 1 AND 5", "NO")])

    def test_check_accepts_parenthesized_signed_scientific_literal(self):
        expected = normalize_check("latitude BETWEEN -90.0 AND 90.0")
        self.assertEqual(normalize_check("((latitude between (-9e1) and (9e1)))"), expected)
        self.assertNotEqual(normalize_check("((latitude between (-8e1) and (9e1)))"), expected)

    def test_fact_uses_database_keys_and_omits_csv_primary_key(self):
        date = loader.SNAPSHOT
        frames = {
            "dim_neighbourhood": pd.DataFrame([{
                "neighbourhood_sk": "0", "neighbourhood_group": "Unknown",
                "neighbourhood_name": "Unknown Neighbourhood", "snapshot_date": date,
            }]),
            "dim_listing": pd.DataFrame([{
                "listing_sk": "1", "neighbourhood_sk": "0", "listing_id": "123",
                "snapshot_date": date,
            }]),
            "fact_review": pd.DataFrame([{
                "listing_sk": "1", "review_sk": "1", "neighbourhood_sk": "0",
                "listing_id": "123", "review_id": "5", "snapshot_date": date,
            }]),
        }
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [], [("Unknown", "Unknown Neighbourhood", 88)], [(123, 99, 88)],
        ]
        cursor.fetchone.return_value = (1,)
        with patch.object(loader, "upsert") as upsert:
            loader.load_tables(cursor, frames, date, 1)
        fact = upsert.call_args.args[2]
        self.assertNotIn("review_sk", fact.columns)
        self.assertEqual(fact.loc[0, ["listing_sk", "neighbourhood_sk"]].tolist(), [99, 88])

    def test_wrong_count_stops_load(self):
        source = pd.DataFrame([{"listing_id": "123", "snapshot_date": loader.SNAPSHOT}])
        cursor = MagicMock()
        cursor.fetchall.return_value = [(123, 99, 88)]
        cursor.fetchone.return_value = (0,)
        frame = source.assign(listing_sk="1", neighbourhood_sk="0")
        with patch.object(loader, "upsert"):
            with self.assertRaisesRegex(ValueError, "matched MySQL rows 0"):
                loader.load_tables(cursor, {"dim_listing": frame}, loader.SNAPSHOT, 1)

    def test_reconciliation_failure_rolls_back_before_commit(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [("test", 1, "STRICT_TRANS_TABLES"), (1,), ("InnoDB",)]
        with patch.multiple(
            loader, get_connection=MagicMock(return_value=conn),
            raw_metrics=MagicMock(return_value=(pd.DataFrame(), {"snapshot_date": loader.SNAPSHOT})),
            read_gold=MagicMock(return_value={}), verify_schema=MagicMock(),
            load_tables=MagicMock(), verify_metrics=MagicMock(side_effect=ValueError("KPI-02 mismatch")),
        ):
            with self.assertRaisesRegex(ValueError, "KPI-02 mismatch"):
                loader.run_warehouse_loading(Path("."))
        conn.begin.assert_called_once()
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_missing_input_stops_before_database_connection(self):
        with patch.object(loader, "raw_metrics", return_value=(pd.DataFrame(), {"snapshot_date": loader.SNAPSHOT})):
            with patch.object(loader, "read_gold", side_effect=FileNotFoundError("fact_review.csv")):
                with patch.object(loader, "get_connection") as connect:
                    with self.assertRaises(FileNotFoundError):
                        loader.run_warehouse_loading(Path("."))
        connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
