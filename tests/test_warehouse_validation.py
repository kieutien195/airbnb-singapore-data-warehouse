"""Regression tests: không để kiểm chứng báo PASS giả."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from warehouse_validation import compare_metrics, validate_design


class ValidationTests(unittest.TestCase):
    def metrics(self):
        return pd.DataFrame([{"snapshot_date": "2026-09-23", "metric": "KPI-05", "group_value": "ALL", "value": 4.5394}])

    def test_changed_rating_fails(self):
        raw = self.metrics(); gold = raw.copy(); gold.loc[0, "value"] = 4.5974
        self.assertEqual(compare_metrics(raw, gold).iloc[0]["status"], "FAIL")

    def test_missing_extra_or_wrong_snapshot_fails(self):
        raw = self.metrics()
        for gold in [raw.iloc[0:0], raw.assign(snapshot_date="2026-09-24"), raw.assign(metric="EXTRA")]:
            self.assertTrue(compare_metrics(raw, gold)["status"].eq("FAIL").any())

    def test_duplicate_keys_and_invalid_values_raise(self):
        raw = self.metrics()
        for gold in [pd.concat([raw, raw]), raw.assign(value="bad"), raw.assign(value=float("inf"))]:
            with self.assertRaises(ValueError):
                compare_metrics(raw, gold)

    def test_null_zero_and_absent_are_different(self):
        raw = self.metrics().assign(value=float("nan"))
        self.assertEqual(compare_metrics(raw, raw.copy()).iloc[0]["status"], "PASS")
        self.assertEqual(compare_metrics(raw, raw.assign(value=0)).iloc[0]["status"], "FAIL")
        self.assertEqual(compare_metrics(raw, raw.iloc[0:0]).iloc[0]["status"], "FAIL")

    def design(self):
        root = Path(__file__).resolve().parents[1]
        return (pd.read_csv(root / "docs/source_to_target_mapping.csv", keep_default_na=False),
                pd.read_csv(root / "docs/warehouse_schema_columns.csv", keep_default_na=False),
                (root / "sql/02_warehouse_schema_draft.sql").read_text(encoding="utf-8"))

    def test_empty_schema_and_invalid_target_fail(self):
        mapping, schema, ddl = self.design()
        self.assertEqual(validate_design(mapping, schema, ddl), [])
        self.assertTrue(validate_design(mapping, pd.DataFrame(), ddl))
        self.assertTrue(validate_design(mapping, schema.iloc[0:0], ddl))
        mapping.loc[mapping.mapping_id.eq("MAP-107"), "gold_target_column"] = "snapshot_date; snapshot_date_sk"
        self.assertTrue(any("MAP-107" in e for e in validate_design(mapping, schema, ddl)))

    def test_schema_type_or_nullable_mismatch_fails(self):
        mapping, schema, ddl = self.design()
        for field, value in [("mysql_dtype", "VARCHAR(5)"), ("nullable", "NULL")]:
            changed = schema.copy(); changed.loc[0, field] = value
            self.assertTrue(validate_design(mapping, changed, ddl))

    def test_generator_rejects_changed_raw_rating(self):
        import task_2_4_2_5_mapping_and_schema as generator
        if not (generator.RAW_DIR / "listings.csv.gz").exists():
            self.skipTest("Integration regression cần data/raw của snapshot chuẩn.")
        mapping, schema, _ = self.design()
        original_read_csv = pd.read_csv
        def changed_read(path, *args, **kwargs):
            data = original_read_csv(path, *args, **kwargs)
            if Path(path).name == "listings.csv.gz":
                data.loc[data.review_scores_rating.notna(), "review_scores_rating"] = 4.5974
            return data
        with patch.object(generator.pd, "read_csv", side_effect=changed_read):
            result = generator.verify_against_raw_data(mapping, schema)
        self.assertEqual(result.set_index("check_id").loc["V-11", "status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
