"""Regression checks for the source schema and semantic type rules."""
import importlib.util
from pathlib import Path
import unittest
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dictionary_kpi", ROOT / "scripts/data_dictionary_kpi.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DictionaryRegressionTests(unittest.TestCase):
    def test_semantic_type_regressions(self):
        self.assertIn("số nguyên", module.transformation("accommodates", "int64"))
        for name in ("price_quote_checkin_date", "price_quote_checkout_date", "host_since"):
            self.assertIn("DATE", module.transformation(name, "float64"))
        for name in ("host_response_time", "host_thumbnail_url", "neighbourhood", "host_neighbourhood"):
            self.assertIn("VARCHAR/TEXT", module.transformation(name, "float64"))
        for name in module.BOOLEAN_COLUMNS:
            self.assertIn("TRUE", module.transformation(name, "float64"))
        for name in ("minimum_nights_avg_ntm", "maximum_nights_avg_ntm"):
            self.assertIn("phần thập phân", module.transformation(name, "float64"))
        self.assertNotIn("accommodates", module.DATE_COLUMNS)

    def test_generated_dictionary_reconciles_to_raw(self):
        dictionary = pd.read_csv(ROOT / "docs/data_dictionary/data_dictionary_all_sources.csv").fillna("")
        self.assertFalse(dictionary.duplicated(["source_name", "column_name"]).any())
        for name, path in module.SOURCES.items():
            raw = pd.read_csv(path, low_memory=False)
            rows = dictionary[dictionary.source_name == name]
            self.assertEqual(set(rows.column_name), set(raw.columns))
            separate = pd.read_csv(ROOT / "docs/data_dictionary" / f"data_dictionary_{name.lower()}.csv").fillna("")
            self.assertEqual(rows.to_dict("records"), separate.to_dict("records"))
            for _, row in rows.iterrows():
                self.assertEqual(row.row_count_source, len(raw))
                self.assertEqual(row.null_count, int(raw[row.column_name].isna().sum()))
        self.assertEqual(len(dictionary), 103)

    def test_duplicate_keys_do_not_count_missing_keys_as_duplicates(self):
        frame = pd.DataFrame({"listing_id": [1, 1, 1, None], "id": [2, 2, 3, 2]})
        self.assertEqual(module._count_duplicate_excess(frame, ["listing_id", "id"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
