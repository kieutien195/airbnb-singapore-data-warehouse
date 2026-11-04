"""Các trường hợp có thể làm sai mẫu giá hoặc số đếm review."""
import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from eda_support import prepare_prices, compare_prices, reconcile_reviews


class EDASupportTests(unittest.TestCase):
    def test_prices_currency_positive_finite_and_same_sample(self):
        data = pd.DataFrame({"id": range(7),
            "price": ["$1,200.50", "$10", "$100", "$0", "-$5", "inf", None],
            "price_quote_price_per_night": [1200.5, None, 50, 1, 5, 2, 3],
            "price_quote_raw": ['{"quote":{"currency":"SGD"}}'] * 7})
        data.loc[2, "price_quote_raw"] = '{"quote":{"currency":"USD"}}'
        original = data.copy(deep=True)
        prices = prepare_prices(data)
        self.assertEqual(prices["listed_price_sgd"].dropna().tolist(), [1200.5, 10])
        comparison = compare_prices(prices).iloc[0]
        self.assertEqual(comparison["matched_listing_count"], 1)
        self.assertEqual(comparison["listed_median_same_sample_sgd"], 1200.5)
        self.assertEqual(comparison["quote_median_same_sample_sgd"], 1200.5)
        pd.testing.assert_frame_equal(original, data)

    def test_unknown_currency_is_excluded_and_not_filled(self):
        data = pd.DataFrame({"id": [1, 2, 3], "price": ["$5", "bad", "$3"],
            "price_quote_price_per_night": [5, 6, 3], "price_quote_raw": [None, "{", "{}"]})
        prices = prepare_prices(data)
        self.assertTrue(prices["listed_price_sgd"].isna().all())
        self.assertEqual(prices["currency"].tolist(), ["MISSING_JSON", "INVALID_JSON", "MISSING_CURRENCY"])
        self.assertEqual(compare_prices(prices).iloc[0]["matched_listing_count"], 0)

    def test_review_composite_keys_missing_zero_and_orphan(self):
        listings = pd.DataFrame({"id": [1, 2, 3, 4], "number_of_reviews": [1, 2, None, 0],
            "neighbourhood_cleansed": ["A", "A", "B", "B"], "room_type": ["R"] * 4})
        reviews = pd.DataFrame({"listing_id": [1, 1, 2, 2, 2, 99],
            "id": [7, 7, 7, 8, 9, 10],
            "date": ["2020-01-01"] * 4 + ["invalid", "2020-01-01"]})
        result, summary, groups = reconcile_reviews(listings, reviews)
        self.assertEqual(result["observed_review_records"].tolist(), [1, 2, 0, 0])
        self.assertTrue(pd.isna(result.loc[2, "listing_review_count"]))
        self.assertEqual(result["comparison_status"].tolist(), ["MATCH", "MATCH", "LISTINGS_COUNT_MISSING_OR_INVALID", "MATCH"])
        self.assertEqual(summary.iloc[0]["review_records_not_linked_to_listings"], 1)
        self.assertEqual(summary.iloc[0]["valid_review_rows"], 5)
        self.assertEqual(summary.iloc[0]["unique_review_keys"], 4)
        self.assertEqual(groups.query("group_dimension == 'room_type'").iloc[0]["median_listing_review_count"], 1)

    def test_review_mismatch_kept_and_duplicate_listings_rejected(self):
        listings = pd.DataFrame({"id": [1], "number_of_reviews": [10],
            "neighbourhood_cleansed": ["A"], "room_type": ["R"]})
        reviews = pd.DataFrame({"listing_id": [1], "id": [7], "date": ["2020-01-01"]})
        result, summary, _ = reconcile_reviews(listings, reviews)
        self.assertEqual(result.iloc[0]["difference_listing_minus_file"], 9)
        self.assertEqual(summary.iloc[0]["different_listings"], 1)
        with self.assertRaises(ValueError):
            reconcile_reviews(pd.concat([listings, listings]), reviews)


if __name__ == "__main__":
    unittest.main()
