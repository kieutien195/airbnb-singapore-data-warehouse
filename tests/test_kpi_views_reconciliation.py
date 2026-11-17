"""Kiểm thử tính toàn vẹn, hiệu năng và đối chiếu Raw-Gold của các KPI Views (Task 4.1)."""
from decimal import Decimal
from pathlib import Path
import json
import os
import sys
import unittest
import numpy as np
import pandas as pd
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.generate_kpi_results import reconcile_regional

load_dotenv(PROJECT_ROOT / ".env", override=True)


class KPIViewsReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.conn = pymysql.connect(
                host=os.getenv("MYSQL_HOST", "127.0.0.1"),
                port=int(os.getenv("MYSQL_PORT", 3306)),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
                database=os.getenv("MYSQL_DATABASE", "airbnb_sg_2026"),
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            cls.raw_dir = PROJECT_ROOT / "data" / "raw"
        except Exception as e:
            raise unittest.SkipTest(f"MySQL unavailable: {e}")

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_all_12_views_exist_in_mysql(self):
        """Kiểm tra sự tồn tại đầy đủ của 12 SQL Views trong schema."""
        expected_views = {
            "vw_kpi01_active_listings",
            "vw_kpi02_median_price_sgd",
            "vw_kpi03_room_type_share",
            "vw_kpi03_regional_room_type_share",
            "vw_kpi04_calendar_availability",
            "vw_kpi04_regional_calendar_availability",
            "vw_kpi05_average_rating",
            "vw_kpi05_regional_average_rating",
            "vw_sup01_median_review_count",
            "vw_sup02_review_records_period",
            "vw_kpi_summary_overall",
            "vw_gold_bi_analytical_base"
        }
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT TABLE_NAME 
                FROM information_schema.views 
                WHERE TABLE_SCHEMA = %s;
            """, (os.getenv("MYSQL_DATABASE", "airbnb_sg_2026"),))
            existing_views = {r.get("TABLE_NAME") or r.get("table_name") for r in cur.fetchall()}
        
        missing = expected_views - existing_views
        self.assertEqual(len(missing), 0, f"Thiếu các View trong MySQL: {missing}")

    def test_02_direct_raw_reconciliation_kpi01_to_kpi05(self):
        """Đối chiếu số liệu giữa RAW CSVs gốc và các SQL View trong MySQL."""
        # 1. Đọc Raw listings
        raw_listings = pd.read_csv(self.raw_dir / "listings.csv.gz", low_memory=False)
        
        # KPI-01: Listings count
        expected_kpi01 = raw_listings["id"].nunique()
        with self.conn.cursor() as cur:
            cur.execute("SELECT active_listings_count FROM vw_kpi01_active_listings;")
            observed_kpi01 = cur.fetchone()["active_listings_count"]
        self.assertEqual(observed_kpi01, expected_kpi01)
        self.assertEqual(observed_kpi01, 3208)

        # KPI-02: Median price SGD
        def parse_currency(val):
            try:
                code = json.loads(val).get("quote", {}).get("currency")
                return code.strip().upper() if isinstance(code, str) else None
            except Exception:
                return None
        
        clean_price = pd.to_numeric(
            raw_listings["price"].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False),
            errors="coerce"
        )
        is_sgd = raw_listings["price_quote_raw"].map(parse_currency) == "SGD"
        valid_price_mask = clean_price.notna() & np.isfinite(clean_price) & (clean_price > 0) & is_sgd
        expected_kpi02 = round(float(clean_price[valid_price_mask].median()), 2)
        expected_price_count = int(valid_price_mask.sum())

        with self.conn.cursor() as cur:
            cur.execute("SELECT median_price_sgd, verified_listings_count FROM vw_kpi02_median_price_sgd;")
            row = cur.fetchone()
            observed_kpi02 = float(row["median_price_sgd"])
            observed_price_count = row["verified_listings_count"]
        
        self.assertEqual(observed_price_count, expected_price_count)
        self.assertEqual(observed_price_count, 2725)
        self.assertAlmostEqual(observed_kpi02, expected_kpi02, places=2)
        self.assertEqual(observed_kpi02, 202.83)

        # KPI-03: Room type share
        expected_room_counts = raw_listings["room_type"].value_counts().to_dict()
        with self.conn.cursor() as cur:
            cur.execute("SELECT room_type, listing_count, room_type_share_pct FROM vw_kpi03_room_type_share;")
            observed_room_rows = cur.fetchall()
        
        observed_room_counts = {r["room_type"]: r["listing_count"] for r in observed_room_rows}
        self.assertEqual(observed_room_counts, expected_room_counts)
        self.assertEqual(observed_room_counts["Private room"], 1827)
        self.assertEqual(observed_room_counts["Entire home/apt"], 1232)
        self.assertEqual(observed_room_counts["Hotel room"], 83)
        self.assertEqual(observed_room_counts["Shared room"], 66)

        # KPI-04: Calendar Available Nights Ratio
        raw_cal = pd.read_csv(self.raw_dir / "calendar.csv.gz", low_memory=False)
        cal_dates = pd.to_datetime(raw_cal["date"])
        in_window = cal_dates.between("2026-09-25", "2027-09-25")
        avail_bool = raw_cal["available"].astype(str).str.strip().str.lower().isin(["t", "true", "1"])
        expected_avail_nights = int((in_window & avail_bool).sum())
        expected_total_nights = int(in_window.sum())
        expected_kpi04 = round(expected_avail_nights * 100.0 / expected_total_nights, 2)

        with self.conn.cursor() as cur:
            cur.execute("SELECT available_nights_count, total_nights_count, available_nights_ratio_pct FROM vw_kpi04_calendar_availability;")
            row = cur.fetchone()
            observed_avail_nights = int(row["available_nights_count"])
            observed_total_nights = int(row["total_nights_count"])
            observed_kpi04 = float(row["available_nights_ratio_pct"])

        self.assertEqual(observed_avail_nights, expected_avail_nights)
        self.assertEqual(observed_total_nights, expected_total_nights)
        self.assertEqual(observed_avail_nights, 900960)
        self.assertEqual(observed_total_nights, 1170950)
        self.assertAlmostEqual(observed_kpi04, expected_kpi04, places=2)
        self.assertEqual(observed_kpi04, 76.94)

        # KPI-05: Rating Score
        raw_ratings = pd.to_numeric(raw_listings["review_scores_rating"], errors="coerce")
        valid_ratings = raw_ratings[raw_ratings.notna() & np.isfinite(raw_ratings) & raw_ratings.between(1, 5)]
        expected_kpi05 = round(float(valid_ratings.mean()), 2)
        expected_rated_count = len(valid_ratings)

        with self.conn.cursor() as cur:
            cur.execute("SELECT rated_listings_count, avg_review_score FROM vw_kpi05_average_rating;")
            row = cur.fetchone()
            observed_rated_count = row["rated_listings_count"]
            observed_kpi05 = float(row["avg_review_score"])

        self.assertEqual(observed_rated_count, expected_rated_count)
        self.assertEqual(observed_rated_count, 1839)
        self.assertAlmostEqual(observed_kpi05, expected_kpi05, places=2)
        self.assertEqual(observed_kpi05, 4.54)

        # SUP-01: Median review count
        raw_reviews_count = pd.to_numeric(raw_listings["number_of_reviews"], errors="coerce").dropna()
        expected_sup01 = round(float(raw_reviews_count.median()), 2)

        with self.conn.cursor() as cur:
            cur.execute("SELECT median_review_count, total_listings_count FROM vw_sup01_median_review_count;")
            row = cur.fetchone()
            observed_sup01 = float(row["median_review_count"])
            observed_total_count = row["total_listings_count"]

        self.assertEqual(observed_total_count, 3208)
        self.assertEqual(observed_sup01, expected_sup01)
        self.assertEqual(observed_sup01, 1.00)

        # SUP-02: Review records
        raw_reviews = pd.read_csv(self.raw_dir / "reviews.csv.gz", low_memory=False)
        in_review_window = raw_reviews["date"].between("2011-05-04", "2026-09-25")
        expected_sup02 = len(raw_reviews.loc[in_review_window, ["listing_id", "id"]].drop_duplicates())

        with self.conn.cursor() as cur:
            cur.execute("SELECT review_records_count FROM vw_sup02_review_records_period;")
            observed_sup02 = cur.fetchone()["review_records_count"]

        self.assertEqual(observed_sup02, expected_sup02)
        self.assertEqual(observed_sup02, 46000)

    def test_03_anti_cartesian_fanout_in_bi_base_view(self):
        """Bảo đảm View BI hoàn toàn không bị tích Descartes (đúng 3,208 dòng)."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) AS total_rows,
                    COUNT(DISTINCT listing_id) AS distinct_listings
                FROM vw_gold_bi_analytical_base;
            """)
            row = cur.fetchone()
        
        self.assertEqual(row["total_rows"], 3208, "LỖI FAN-OUT: Số dòng BI base vượt quá 3,208!")
        self.assertEqual(row["distinct_listings"], 3208, "LỖI TRÙNG LẶP: Có listing_id bị trùng lặp!")

    def test_04_regional_room_type_denominators(self):
        """Bảo đảm mẫu số tỷ trọng loại phòng theo khu vực cộng đủ 100% mỗi vùng."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    neighbourhood_group,
                    SUM(listing_count) AS sum_listings,
                    MAX(regional_total_listings) AS regional_total,
                    ROUND(SUM(room_type_share_pct), 1) AS sum_share_pct
                FROM vw_kpi03_regional_room_type_share
                GROUP BY neighbourhood_group;
            """)
            rows = cur.fetchall()

        for r in rows:
            self.assertEqual(
                r["sum_listings"], 
                r["regional_total"], 
                f"Khu vực {r['neighbourhood_group']} có tổng số listing không khớp mẫu số vùng!"
            )
            self.assertAlmostEqual(
                float(r["sum_share_pct"]), 
                100.0, 
                delta=0.2, 
                msg=f"Khu vực {r['neighbourhood_group']} tổng tỷ trọng khác 100%!"
            )

class RegionalReconciliationTests(unittest.TestCase):
    def test_pymysql_decimal_denominator_matches_numpy_count(self):
        expected = {"Central": (np.int64(9), np.int64(12), 75.0)}
        row = {"region": "Central", "num": 9, "value": Decimal("75.00")}
        for denominator, status in [("12", "PASS"), ("12.5", "FAIL"), ("13", "FAIL")]:
            with self.subTest(denominator=denominator):
                _, result = next(reconcile_regional(
                    [row | {"den": Decimal(denominator)}], expected,
                    ("region",), "num", "den", "value"
                ))
                self.assertEqual(result["reconciliation_status"], status)

    def test_regional_mismatch_in_metric_or_counts_fails(self):
        expected = {"Central": (9, 12, 75.0)}
        row = {"region": "Central", "num": 9, "den": 12, "value": 75.0}
        for field, bad in [("num", 8), ("den", 13), ("value", 76.0)]:
            with self.subTest(field=field):
                _, result = next(reconcile_regional(
                    [row | {field: bad}], expected, ("region",), "num", "den", "value"
                ))
                self.assertEqual(result["reconciliation_status"], "FAIL")
                self.assertEqual(result["expected_raw_value"], 75.0)

    def test_missing_or_duplicate_regional_group_fails(self):
        expected = {"Central": (9, 12, 75.0)}
        row = {"region": "Central", "num": 9, "den": 12, "value": 75.0}
        for rows in ([], [row, row]):
            with self.assertRaises(ValueError):
                list(reconcile_regional(rows, expected, ("region",), "num", "den", "value"))


if __name__ == "__main__":
    unittest.main()
