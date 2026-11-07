#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
etl/transform.py – Task 3.4: Mapping và Kiểm tra Quan Hệ Đa Bảng (Gold Ready)
=============================================================================
1. Chuẩn hóa và ánh xạ các trường từ Silver sang mô hình Star Schema / Fact Constellation
   theo đúng docs/source_to_target_mapping.csv và sql/02_warehouse_schema_draft.sql.
2. Sinh khóa đại diện (Surrogate Keys):
   - dim_date (date_sk)
   - dim_neighbourhood (neighbourhood_sk)
   - dim_listing (listing_sk)
   - fact_listing_snapshot (listing_snapshot_sk)
   - fact_calendar (calendar_sk)
   - fact_review (review_sk)
3. Kiểm tra tính toàn vẹn tham chiếu (Referential Integrity) & Khóa mồ côi (Orphan Keys):
   - Calendar(listing_id) -> Listings(id)
   - Reviews(listing_id) -> Listings(id)
   - Listings(neighbourhood) -> Neighbourhoods(neighbourhood)
   - All Dates -> dim_date(date_sk)
4. NGHIÊM CẤM JOIN trực tiếp giữa Calendar và Reviews (tránh Cartesian fan-out).
5. Xuất báo cáo độ phủ quan hệ: outputs/join_coverage.csv.

Tác giả : Thái (Data Engineer / ETL)
Phối hợp: Minh (Data Warehouse / MySQL)
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.ingest import output_path

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "transform.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("transform")


def load_config(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# 1. Sinh Bảng Chiều Thời Gian: dim_date (2011-01-01 .. 2027-12-31)
# ---------------------------------------------------------------------------
def build_dim_date(start_date: str = "2011-01-01", end_date: str = "2027-12-31") -> pd.DataFrame:
    logger.info(f"-> Đang sinh bảng chiều thời gian dim_date ({start_date} đến {end_date})...")
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    
    df = pd.DataFrame({"full_date_dt": dates})
    df["date_sk"] = df["full_date_dt"].dt.strftime("%Y%m%d").astype(int)
    df["full_date"] = df["full_date_dt"].dt.strftime("%Y-%m-%d")
    df["day_of_month"] = df["full_date_dt"].dt.day.astype(int)
    df["day_of_week_iso"] = df["full_date_dt"].dt.dayofweek + 1  # 1=Monday .. 7=Sunday
    df["day_name"] = df["full_date_dt"].dt.day_name()
    df["is_weekend"] = df["day_of_week_iso"].isin([6, 7]).astype(int)
    df["week_of_year"] = df["full_date_dt"].dt.isocalendar().week.astype(int)
    df["month_num"] = df["full_date_dt"].dt.month.astype(int)
    df["month_name"] = df["full_date_dt"].dt.month_name()
    df["year_month"] = df["full_date_dt"].dt.strftime("%Y-%m")
    df["quarter_num"] = df["full_date_dt"].dt.quarter.astype(int)
    df["year_quarter"] = df["full_date_dt"].dt.year.astype(str) + "-Q" + df["quarter_num"].astype(str)
    df["year_num"] = df["full_date_dt"].dt.year.astype(int)
    
    df.drop(columns=["full_date_dt"], inplace=True)
    return df


# ---------------------------------------------------------------------------
# 2. Xây dựng dim_neighbourhood
# ---------------------------------------------------------------------------
def build_dim_neighbourhood(silver_nb: pd.DataFrame, snapshot_date: str) -> pd.DataFrame:
    logger.info("-> Đang xây dựng dim_neighbourhood...")
    df = silver_nb.copy()
    df = df.sort_values(by=["neighbourhood_group", "neighbourhood_name"]).reset_index(drop=True)
    df["neighbourhood_sk"] = np.arange(1, len(df) + 1, dtype=int)
    df["snapshot_date"] = snapshot_date
    
    cols = ["neighbourhood_sk", "neighbourhood_group", "neighbourhood_name", "snapshot_date"]
    return df[cols]


# ---------------------------------------------------------------------------
# 3. Xây dựng dim_listing & fact_listing_snapshot
# ---------------------------------------------------------------------------
def build_listing_dimensions_and_fact(
    silver_listings: pd.DataFrame,
    dim_nb: pd.DataFrame,
    snapshot_date: str,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    logger.info("-> Đang ánh xạ dim_listing và fact_listing_snapshot...")
    df = silver_listings.copy()
    
    # 1. Tra cứu neighbourhood_sk
    nb_lookup = dim_nb.set_index(["neighbourhood_group", "neighbourhood_name"])["neighbourhood_sk"].to_dict()
    df["neighbourhood_sk"] = df.apply(
        lambda r: nb_lookup.get((r.get("neighbourhood_group_cleansed"), r.get("neighbourhood_cleansed")), 0),
        axis=1,
    )
    # Gán surrogate key cho listing (1..N)
    df = df.sort_values(by=["id"]).reset_index(drop=True)
    df["listing_sk"] = np.arange(1, len(df) + 1, dtype=np.int64)
    df["listing_id"] = df["id"].astype(np.int64)
    df["snapshot_date_sk"] = int(snapshot_date.replace("-", ""))
    
    # 2. Tạo dim_listing (Thuộc tính mô tả)
    dim_listing_cols = [
        "listing_sk", "listing_id", "snapshot_date", "snapshot_date_sk", "neighbourhood_sk",
        "scrape_id", "last_scraped", "calendar_last_scraped", "source", "name",
        "listing_url", "picture_url", "property_type", "room_type", "accommodates",
        "bedrooms", "beds", "bathrooms_text", "latitude", "longitude", "has_availability",
        "license", "host_id", "host_profile_id", "host_name", "host_location",
        "host_is_superhost", "host_has_profile_pic", "host_identity_verified",
        "hosts_time_as_user_years", "hosts_time_as_user_months", "hosts_time_as_host_years",
        "hosts_time_as_host_months", "first_review", "last_review",
    ]
    
    # Đổi tên khớp với schema DDL
    dim_listing = df[[c for c in dim_listing_cols if c in df.columns]].copy()
    dim_listing.rename(
        columns={
            "last_scraped": "last_scraped_date",
            "calendar_last_scraped": "calendar_last_scraped_date",
            "source": "source_type",
            "name": "listing_name",
            "first_review": "first_review_date",
            "last_review": "last_review_date",
        },
        inplace=True,
    )

    # 3. Tạo fact_listing_snapshot (Thước đo định lượng)
    df["listing_snapshot_sk"] = np.arange(1, len(df) + 1, dtype=np.int64)
    
    fact_cols = [
        "listing_snapshot_sk", "listing_sk", "neighbourhood_sk", "snapshot_date_sk",
        "listing_id", "snapshot_date", "listed_price_raw_amount", "quote_currency",
        "is_price_sgd_verified", "listed_price_sgd", "price_quote_price_per_night",
        "price_quote_total_price", "price_quote_checkin_date", "price_quote_checkout_date",
        "minimum_nights", "maximum_nights", "minimum_minimum_nights", "maximum_minimum_nights",
        "minimum_maximum_nights", "maximum_maximum_nights", "minimum_nights_avg_ntm",
        "maximum_nights_avg_ntm", "availability_30", "availability_60", "availability_90",
        "availability_365", "availability_eoy", "number_of_reviews", "number_of_reviews_ltm",
        "number_of_reviews_l30d", "number_of_reviews_ly", "reviews_per_month",
        "review_scores_rating", "review_scores_accuracy", "review_scores_cleanliness",
        "review_scores_checkin", "review_scores_communication", "review_scores_location",
        "review_scores_value", "host_listings_count", "calculated_host_listings_count",
        "calculated_host_listings_count_entire_homes", "calculated_host_listings_count_private_rooms",
        "calculated_host_listings_count_shared_rooms", "estimated_occupancy_l365d",
        "estimated_revenue_l365d",
    ]
    
    fact_listing = df[[c for c in fact_cols if c in df.columns]].copy()
    
    return dim_listing, fact_listing


# ---------------------------------------------------------------------------
# 4. Xây dựng fact_calendar
# ---------------------------------------------------------------------------
def build_fact_calendar(silver_cal: pd.DataFrame, dim_listing: pd.DataFrame) -> pd.DataFrame:
    logger.info("-> Đang ánh xạ fact_calendar...")
    # Lookup listing_sk và neighbourhood_sk từ dim_listing
    lookup = dim_listing.set_index("listing_id")[["listing_sk", "neighbourhood_sk"]].to_dict(orient="index")
    
    cal = silver_cal.copy()
    
    # Vectorized lookup
    listing_sks = cal["listing_id"].map(lambda x: lookup[x]["listing_sk"] if x in lookup else np.nan)
    nb_sks = cal["listing_id"].map(lambda x: lookup[x]["neighbourhood_sk"] if x in lookup else np.nan)
    
    cal["listing_sk"] = listing_sks
    cal["neighbourhood_sk"] = nb_sks
    cal["calendar_sk"] = np.arange(1, len(cal) + 1, dtype=np.int64)
    
    cols = [
        "calendar_sk", "listing_sk", "neighbourhood_sk", "calendar_date_sk",
        "snapshot_date_sk", "listing_id", "calendar_date", "snapshot_date",
        "is_available", "minimum_nights", "maximum_nights",
    ]
    return cal[cols]


# ---------------------------------------------------------------------------
# 5. Xây dựng fact_review
# ---------------------------------------------------------------------------
def build_fact_review(silver_rev: pd.DataFrame, dim_listing: pd.DataFrame) -> pd.DataFrame:
    logger.info("-> Đang ánh xạ fact_review...")
    lookup = dim_listing.set_index("listing_id")[["listing_sk", "neighbourhood_sk"]].to_dict(orient="index")
    
    rev = silver_rev.copy()
    
    listing_sks = rev["listing_id"].map(lambda x: lookup[x]["listing_sk"] if x in lookup else np.nan)
    nb_sks = rev["listing_id"].map(lambda x: lookup[x]["neighbourhood_sk"] if x in lookup else np.nan)
    
    rev["listing_sk"] = listing_sks
    rev["neighbourhood_sk"] = nb_sks
    rev["review_sk"] = np.arange(1, len(rev) + 1, dtype=np.int64)
    rev["review_count"] = 1
    
    cols = [
        "review_sk", "listing_sk", "neighbourhood_sk", "review_date_sk",
        "snapshot_date_sk", "listing_id", "review_id", "review_date",
        "snapshot_date", "reviewer_id", "reviewer_name", "has_comment",
        "comment_length", "review_count",
    ]
    return rev[cols]


# ---------------------------------------------------------------------------
# 6. Kiểm tra Toàn Vẹn Tham Chiếu (Referential Integrity & Orphan Check)
# ---------------------------------------------------------------------------
def check_join_coverage_and_orphans(
    silver_listings: pd.DataFrame,
    silver_cal: pd.DataFrame,
    silver_rev: pd.DataFrame,
    silver_nb: pd.DataFrame,
    dim_date: pd.DataFrame,
) -> pd.DataFrame:
    logger.info("-> Đang kiểm tra tính toàn vẹn tham chiếu và tỷ lệ orphan key...")

    coverage_rows = []
    main_listings = silver_listings["id"]

    # 1. Calendar -> Listings
    total_cal = len(silver_cal)
    cal_matched = int(silver_cal["listing_id"].isin(main_listings).sum())
    cal_orphan_count = total_cal - cal_matched
    cal_rate = round(cal_matched / total_cal * 100, 4) if total_cal else 100.0

    coverage_rows.append({
        "relationship_id": "REL-01",
        "relationship_name": "Calendar to Listings (1-N)",
        "parent_table": "dim_listing",
        "child_table": "fact_calendar",
        "foreign_key": "listing_id",
        "total_child_records": total_cal,
        "matched_records": cal_matched,
        "orphan_records": cal_orphan_count,
        "match_rate_pct": cal_rate,
        "status": "PASS" if cal_orphan_count == 0 else "FAIL",
        "notes": "Dòng thiếu listing cha được ghi vào etl_orphan_records.csv.",
    })

    # 2. Reviews -> Listings
    total_rev = len(silver_rev)
    rev_matched = int(silver_rev["listing_id"].isin(main_listings).sum())
    rev_orphan_count = total_rev - rev_matched
    rev_rate = round(rev_matched / total_rev * 100, 4) if total_rev else 100.0

    coverage_rows.append({
        "relationship_id": "REL-02",
        "relationship_name": "Reviews to Listings (1-N)",
        "parent_table": "dim_listing",
        "child_table": "fact_review",
        "foreign_key": "listing_id",
        "total_child_records": total_rev,
        "matched_records": rev_matched,
        "orphan_records": rev_orphan_count,
        "match_rate_pct": rev_rate,
        "status": "PASS" if rev_orphan_count == 0 else "FAIL",
        "notes": "Dòng thiếu listing cha được ghi vào etl_orphan_records.csv.",
    })

    # 3. Listings -> Neighbourhoods
    total_list = len(silver_listings)
    list_areas = zip(silver_listings["neighbourhood_group_cleansed"], silver_listings["neighbourhood_cleansed"])
    valid_areas = set(zip(silver_nb["neighbourhood_group"], silver_nb["neighbourhood_name"]))
    area_matched = sum(area in valid_areas for area in list_areas)
    area_orphan_count = total_list - area_matched
    area_rate = round(area_matched / total_list * 100, 4) if total_list else 100.0

    coverage_rows.append({
        "relationship_id": "REL-03",
        "relationship_name": "Listings to Neighbourhoods (N-1)",
        "parent_table": "dim_neighbourhood",
        "child_table": "dim_listing",
        "foreign_key": "(neighbourhood_group, neighbourhood_name)",
        "total_child_records": total_list,
        "matched_records": area_matched,
        "orphan_records": area_orphan_count,
        "match_rate_pct": area_rate,
        "status": "PASS" if area_orphan_count == 0 else "WARN",
        "notes": "Khu vực không khớp được ánh xạ vào Unknown Neighbourhood (SK=0).",
    })

    # 4. Dates to dim_date
    date_keys = dim_date["date_sk"]
    matched = 0
    total = 0
    for frame, key in (
        (silver_listings, "snapshot_date_sk"), (silver_cal, "calendar_date_sk"),
        (silver_cal, "snapshot_date_sk"), (silver_rev, "review_date_sk"),
        (silver_rev, "snapshot_date_sk"),
    ):
        matched += int(frame[key].isin(date_keys).sum())
        total += len(frame)
    coverage_rows.append({
        "relationship_id": "REL-04",
        "relationship_name": "Event and Snapshot Dates to dim_date",
        "parent_table": "dim_date",
        "child_table": "fact_listing_snapshot & fact_calendar & fact_review",
        "foreign_key": "snapshot_date_sk, calendar_date_sk, review_date_sk",
        "total_child_records": total,
        "matched_records": matched,
        "orphan_records": total - matched,
        "match_rate_pct": round(matched / total * 100, 4) if total else 100.0,
        "status": "PASS" if matched == total else "FAIL",
        "notes": "Đếm từng tham chiếu ngày sự kiện và snapshot.",
    })

    return pd.DataFrame(coverage_rows)


# ---------------------------------------------------------------------------
# Pipeline Transform Chính
# ---------------------------------------------------------------------------
def run_transform_pipeline(config_path: Path, sample_size: Optional[int] = None) -> Dict[str, Any]:
    config = load_config(config_path)
    snapshot_date = config["project"]["snapshot_date"]
    silver_dir = output_path(config, "silver_dir", sample_size)
    gold_dir = output_path(config, "gold_dir", sample_size)
    outputs_dir = output_path(config, "outputs_dir", sample_size)

    for d in [gold_dir, outputs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  AIRBNB SINGAPORE DATA WAREHOUSE – TASK 3.4: TRANSFORM & MULTI-TABLE MAPPING")
    print(f"  Snapshot Date: {snapshot_date}")
    print("=" * 70)

    # Đọc dữ liệu Silver
    logger.info("Đang đọc dữ liệu Silver đã làm sạch...")
    silver_listings = pd.read_csv(
        silver_dir / "silver_listings.csv", low_memory=False,
        dtype={"host_profile_id": "string"},
    )
    silver_calendar = pd.read_csv(silver_dir / "silver_calendar.csv", low_memory=False)
    silver_reviews = pd.read_csv(silver_dir / "silver_reviews.csv", low_memory=False)
    silver_neighbourhoods = pd.read_csv(silver_dir / "silver_neighbourhoods.csv")

    for name, frame in (("listings", silver_listings), ("calendar", silver_calendar),
                        ("reviews", silver_reviews), ("neighbourhoods", silver_neighbourhoods)):
        if not frame["snapshot_date"].eq(snapshot_date).all():
            raise ValueError(f"Silver {name} snapshot differs from {snapshot_date}")

    dim_date = build_dim_date()
    coverage_df = check_join_coverage_and_orphans(
        silver_listings, silver_calendar, silver_reviews, silver_neighbourhoods, dim_date
    )
    orphan_rows = []
    for name, frame in (("Calendar", silver_calendar), ("Reviews", silver_reviews)):
        missing_parent = ~frame["listing_id"].isin(silver_listings["id"])
        orphan_rows.append(frame.loc[missing_parent].assign(
            dataset=name, rejection_reason="Missing listing in snapshot"
        ))

    pd.concat(orphan_rows, ignore_index=True).to_csv(
        outputs_dir / "etl_orphan_records.csv", index=False, encoding="utf-8-sig"
    )
    if sample_size is not None:
        # Independent sample limits can omit a valid parent from the listing sample.
        child_failures = coverage_df["relationship_id"].isin(["REL-01", "REL-02"]) & coverage_df["status"].eq("FAIL")
        coverage_df.loc[child_failures, "status"] = "WARN"
        silver_calendar = silver_calendar.loc[silver_calendar["listing_id"].isin(silver_listings["id"])]
        silver_reviews = silver_reviews.loc[silver_reviews["listing_id"].isin(silver_listings["id"])]

    join_coverage_path = outputs_dir / "join_coverage.csv"
    coverage_df.to_csv(join_coverage_path, index=False, encoding="utf-8-sig")
    if sample_size is None:
        tests_dir = PROJECT_ROOT / "tests"
        tests_dir.mkdir(exist_ok=True)
        coverage_df.to_csv(tests_dir / "join_coverage.csv", index=False, encoding="utf-8-sig")
    if coverage_df["status"].eq("FAIL").any():
        raise RuntimeError(f"Gold coverage failed; see {join_coverage_path}")

    dim_neighbourhood = build_dim_neighbourhood(silver_neighbourhoods, snapshot_date)
    if coverage_df.loc[coverage_df["relationship_id"].eq("REL-03"), "orphan_records"].iloc[0]:
        unknown = pd.DataFrame([{
            "neighbourhood_sk": 0, "neighbourhood_group": "Unknown",
            "neighbourhood_name": "Unknown Neighbourhood", "snapshot_date": snapshot_date,
        }])
        dim_neighbourhood = pd.concat([dim_neighbourhood, unknown], ignore_index=True)
    dim_listing, fact_listing_snapshot = build_listing_dimensions_and_fact(
        silver_listings, dim_neighbourhood, snapshot_date
    )
    fact_calendar = build_fact_calendar(silver_calendar, dim_listing)
    fact_review = build_fact_review(silver_reviews, dim_listing)

    for name, frame in (
        ("dim_date", dim_date), ("dim_neighbourhood", dim_neighbourhood),
        ("dim_listing", dim_listing), ("fact_listing_snapshot", fact_listing_snapshot),
        ("fact_calendar", fact_calendar), ("fact_review", fact_review),
    ):
        frame.to_csv(gold_dir / f"{name}.csv", index=False, encoding="utf-8-sig")

    print("\n" + "=" * 70)
    print("  KẾT QUẢ TỔNG HỢP MAPPING & QUAN HỆ ĐA BẢNG (TASK 3.4)")
    print("=" * 70)
    print(f"  - dim_date               : {len(dim_date):,} dòng ({dim_date['full_date'].min()} .. {dim_date['full_date'].max()})")
    print(f"  - dim_neighbourhood      : {len(dim_neighbourhood):,} dòng")
    print(f"  - dim_listing            : {len(dim_listing):,} dòng")
    print(f"  - fact_listing_snapshot  : {len(fact_listing_snapshot):,} dòng")
    print(f"  - fact_calendar          : {len(fact_calendar):,} dòng")
    print(f"  - fact_review            : {len(fact_review):,} dòng")
    print("\n  KIỂM TRA TÍNH TOÀN VẸN THAM CHIẾU (ORPHAN KEYS):")
    for _, row in coverage_df.iterrows():
        print(f"  * {row['relationship_name']:<32}: {row['match_rate_pct']}% khớp (Orphan = {row['orphan_records']}) -> [{row['status']}]")
    print("=" * 70)

    return {"status": "SUCCESS", "coverage": coverage_df.to_dict(orient="records")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 3.4: Mapping và kiểm tra quan hệ đa bảng")
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "etl" / "config.yaml",
        help="Đường dẫn file cấu hình YAML",
    )
    args = parser.parse_args()
    run_transform_pipeline(config_path=args.config)


if __name__ == "__main__":
    main()
