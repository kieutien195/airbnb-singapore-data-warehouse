#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
etl/clean.py – Task 3.3: Làm Sạch và Chuẩn Hóa Dữ Liệu Tầng Silver
==================================================================
1. Ép kiểu chuẩn: price, date, numeric, boolean.
2. Trích xuất đơn vị tiền tệ từ JSON price_quote_raw, kiểm chứng SGD (KPI-02).
3. Kiểm tra tính duy nhất (Uniqueness) theo đúng grain từng bảng:
   - Listings: (id, snapshot_date)
   - Calendar: (listing_id, date, snapshot_date)
   - Reviews: (listing_id, id, snapshot_date) – KHÔNG xóa theo id đơn lẻ.
   - Neighbourhoods: (neighbourhood_group, neighbourhood_name)
4. Bảo toàn tính toàn vẹn nghiệp vụ:
   - KHÔNG thay NULL bằng 0 ở price và review_scores_*.
   - KHÔNG tự ý xóa ngoại lai (outliers) theo IQR.
   - Giữ nguyên phần thập phân của *_avg_ntm.
   - Giữ accommodates là INT (1-16), không parse thành DATE.
5. Xuất thống kê Trước - Sau và tách bản ghi vi phạm (nếu có).

Tác giả : Thái (Data Engineer / ETL)
Phối hợp: Hồng (QA / EDA)
"""

from __future__ import annotations

import argparse
import datetime
import json
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
LOG_FILE = LOG_DIR / "clean.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("clean")


def load_config(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_price(val: Any) -> Optional[float]:
    """Parse chuỗi giá dạng '$86.63' hoặc '$1,250.00' sang số thực float."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace("$", "").replace(",", "").strip()
    if not s or s.lower() == "none" or s.lower() == "nan":
        return np.nan
    try:
        f = float(s)
        return round(f, 2) if np.isfinite(f) else np.nan
    except (ValueError, TypeError):
        return np.nan


def extract_currency_from_json(raw_json: Any) -> Optional[str]:
    """Parse chuỗi JSON tại đường dẫn $.quote.currency."""
    if pd.isna(raw_json):
        return None
    s = str(raw_json).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        data = json.loads(s)
        quote = data.get("quote", {})
        if isinstance(quote, dict):
            curr = quote.get("currency")
            if curr and isinstance(curr, str):
                return curr.strip().upper()
    except Exception:
        pass
    return None


def parse_boolean(val: Any) -> Optional[int]:
    """Ánh xạ cờ boolean: 't'/'true'/'1' -> 1, 'f'/'false'/'0' -> 0, giữ NaN nếu thiếu."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip().lower()
    if s in ("t", "true", "1", "1.0"):
        return 1
    elif s in ("f", "false", "0", "0.0"):
        return 0
    return np.nan


def parse_iso_date(val: Any) -> Optional[str]:
    """Parse chuỗi ngày sang chuẩn ISO YYYY-MM-DD."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "nat"):
        return None
    try:
        dt = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
        if pd.isna(dt):
            return None
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def date_to_sk(date_str: Optional[str]) -> Optional[int]:
    """Chuyển chuỗi YYYY-MM-DD thành khóa đại diện số nguyên YYYYMMDD."""
    if not date_str:
        return None
    try:
        return int(date_str.replace("-", ""))
    except (ValueError, TypeError):
        return None


def positive_id(values: pd.Series) -> pd.Series:
    tokens = values.astype("string").str.strip()
    valid = tokens.str.fullmatch(r"[0-9]{1,19}", na=False)
    valid &= tokens.str.len().lt(19) | tokens.le(str(np.iinfo(np.int64).max))
    ids = tokens.where(valid).astype("Int64")
    return ids.where(ids > 0)


def iso_dates(values: pd.Series) -> pd.Series:
    tokens = values.astype("string").str.strip()
    parsed = pd.to_datetime(tokens.where(tokens.str.fullmatch(r"\d{4}-\d{2}-\d{2}")),
                            format="%Y-%m-%d", errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d")


def invalid_integer(values: pd.Series, minimum: int, maximum: int) -> pd.Series:
    return ~values.between(minimum, maximum) | values.mod(1).ne(0)


def reject_invalid(raw, clean, checks, rejected):
    for reason, mask in checks.items():
        bad_index = mask.reindex(clean.index).fillna(True)
        if bad_index.any():
            bad = raw.loc[clean.index[bad_index]].copy()
            bad["rejection_reason"] = reason
            rejected.append(bad)
            clean = clean.loc[~bad_index].copy()
    return clean


# ---------------------------------------------------------------------------
# 1. Làm sạch Listings
# ---------------------------------------------------------------------------
def clean_listings(df: pd.DataFrame, snapshot_date: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    logger.info("-> Đang làm sạch Listings...")
    initial_rows = len(df)
    rejected_rows = []

    clean_df = df.copy()

    checks = {}
    for col in ("id", "scrape_id", "host_id"):
        clean_df[col] = positive_id(df[col])
        checks[f"Missing or invalid {col}"] = clean_df[col].isna()
    clean_df["last_scraped"] = iso_dates(df["last_scraped"])
    checks["Missing or invalid last_scraped"] = clean_df["last_scraped"].isna()
    for col in ("room_type", "neighbourhood_cleansed", "neighbourhood_group_cleansed"):
        checks[f"Missing {col}"] = df[col].astype("string").str.strip().fillna("").eq("")
    for col, lower, upper in (("latitude", -90, 90), ("longitude", -180, 180)):
        clean_df[col] = pd.to_numeric(df[col], errors="coerce")
        checks[f"Missing or invalid {col}"] = ~clean_df[col].between(lower, upper)
    for col, lower, upper in (("accommodates", 1, 16), ("number_of_reviews", 0, 2**32 - 1)):
        clean_df[col] = pd.to_numeric(df[col], errors="coerce")
        checks[f"Missing or invalid {col}"] = invalid_integer(clean_df[col], lower, upper)
    for col in df.filter(regex=r"^review_scores_").columns:
        clean_df[col] = pd.to_numeric(df[col], errors="coerce")
        checks[f"Invalid {col} (expected 1–5)"] = df[col].notna() & ~clean_df[col].between(1, 5)
    for col in ("minimum_nights", "maximum_nights"):
        clean_df[col] = pd.to_numeric(df[col], errors="coerce")
        checks[f"Invalid {col}"] = df[col].notna() & invalid_integer(clean_df[col], 1, 2**32 - 1)
    checks["maximum_nights below minimum_nights"] = clean_df["maximum_nights"].lt(clean_df["minimum_nights"])
    for col in ("host_is_superhost", "host_has_profile_pic", "host_identity_verified", "has_availability"):
        if col in df:
            checks[f"Invalid {col}"] = df[col].notna() & df[col].map(parse_boolean).isna()
    # Missing price is allowed. A malformed or nonfinite source value is quarantined.
    clean_df["listed_price_raw_amount"] = df["price"].map(parse_price)
    checks["Invalid listed price"] = df["price"].notna() & clean_df["listed_price_raw_amount"].isna()
    clean_df = reject_invalid(df, clean_df, checks, rejected_rows)

    # Kiểm tra trùng grain (id, snapshot_date)
    dup_mask = clean_df.duplicated(subset=["id"], keep="last")
    if dup_mask.any():
        bad = clean_df[dup_mask].copy()
        bad["rejection_reason"] = "Duplicate id within snapshot"
        rejected_rows.append(bad)
        clean_df = clean_df[~dup_mask]

    # 1. Giá & Xác minh tiền tệ SGD (KPI-02)
    clean_df["quote_currency"] = clean_df["price_quote_raw"].apply(extract_currency_from_json)

    # is_price_sgd_verified = 1 khi price > 0 và quote_currency == 'SGD' (2,725 dòng)
    clean_df["is_price_sgd_verified"] = (
        (clean_df["listed_price_raw_amount"] > 0) & (clean_df["quote_currency"] == "SGD")
    ).astype(int)

    clean_df["listed_price_sgd"] = np.where(
        clean_df["is_price_sgd_verified"] == 1,
        clean_df["listed_price_raw_amount"],
        np.nan,
    )

    # 2. Xử lý Ngày tháng
    for col in ["last_scraped", "calendar_last_scraped", "first_review", "last_review",
                "price_quote_checkin_date", "price_quote_checkout_date"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].apply(parse_iso_date)

    clean_df["snapshot_date"] = snapshot_date
    clean_df["snapshot_date_sk"] = date_to_sk(snapshot_date)

    # 3. Chuẩn hóa Boolean (giữ NULL hợp lệ ở has_availability)
    for b_col in ["host_is_superhost", "host_has_profile_pic", "host_identity_verified", "has_availability"]:
        if b_col in clean_df.columns:
            clean_df[b_col] = clean_df[b_col].apply(parse_boolean)

    # 4. Chuẩn hóa chuỗi (TRIM) & Danh mục room_type
    for s_col in ["name", "host_name", "neighbourhood_cleansed", "neighbourhood_group_cleansed",
                  "property_type", "room_type", "license", "bathrooms_text"]:
        if s_col in clean_df.columns:
            clean_df[s_col] = clean_df[s_col].astype(str).str.strip()
            clean_df[s_col] = clean_df[s_col].replace({"nan": None, "None": None, "": None})

    # 5. Numerics
    # accommodates: giữ số nguyên (1..16), KHÔNG parse thành date
    clean_df["accommodates"] = clean_df["accommodates"].astype(int)

    # Giữ phần thập phân của *_avg_ntm
    clean_df["minimum_nights_avg_ntm"] = pd.to_numeric(clean_df["minimum_nights_avg_ntm"], errors="coerce").round(2)
    clean_df["maximum_nights_avg_ntm"] = pd.to_numeric(clean_df["maximum_nights_avg_ntm"], errors="coerce").round(2)

    # Điểm đánh giá: review_scores_rating (giữ nguyên NULL 1,369 dòng, không thay bằng 0)
    for r_col in ["review_scores_rating", "review_scores_accuracy", "review_scores_cleanliness",
                  "review_scores_checkin", "review_scores_communication", "review_scores_location",
                  "review_scores_value", "reviews_per_month"]:
        if r_col in clean_df.columns:
            clean_df[r_col] = pd.to_numeric(clean_df[r_col], errors="coerce").round(2)

    # Thống kê
    median_price_sgd = clean_df["listed_price_sgd"].dropna().median()
    valid_sgd_count = int(clean_df["is_price_sgd_verified"].sum())

    stats = {
        "dataset": "Listings",
        "initial_rows": initial_rows,
        "clean_rows": len(clean_df),
        "rejected_rows": initial_rows - len(clean_df),
        "null_price_count": int(clean_df["listed_price_sgd"].isna().sum()),
        "valid_sgd_count": valid_sgd_count,
        "median_price_sgd": round(float(median_price_sgd), 2) if not pd.isna(median_price_sgd) else None,
        "null_rating_count": int(clean_df["review_scores_rating"].isna().sum()),
    }

    rejected_df = pd.concat(rejected_rows, ignore_index=True) if rejected_rows else pd.DataFrame()
    return clean_df, rejected_df, stats


# ---------------------------------------------------------------------------
# 2. Làm sạch Calendar
# ---------------------------------------------------------------------------
def clean_calendar(df: pd.DataFrame, snapshot_date: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    logger.info("-> Đang làm sạch Calendar...")
    initial_rows = len(df)
    rejected_rows = []

    clean_df = df.copy()

    clean_df["listing_id"] = positive_id(df["listing_id"])
    clean_df["calendar_date"] = iso_dates(df["date"])
    flags = df["available"].astype("string").str.strip().str.lower()
    clean_df["is_available"] = flags.map({
        "t": 1, "true": 1, "1": 1, "1.0": 1,
        "f": 0, "false": 0, "0": 0, "0.0": 0,
    })
    checks = {
        "Missing or invalid listing_id": clean_df["listing_id"].isna(),
        "Missing or invalid calendar date": clean_df["calendar_date"].isna(),
        "Missing or invalid available": clean_df["is_available"].isna(),
    }
    for col in ("minimum_nights", "maximum_nights"):
        clean_df[col] = pd.to_numeric(df[col], errors="coerce")
        checks[f"Missing or invalid {col}"] = invalid_integer(clean_df[col], 1, 2**32 - 1)
    checks["maximum_nights below minimum_nights"] = clean_df["maximum_nights"].lt(clean_df["minimum_nights"])
    clean_df = reject_invalid(df, clean_df, checks, rejected_rows)
    clean_df["calendar_date_sk"] = clean_df["calendar_date"].str.replace("-", "", regex=False).astype("int64")
    clean_df["snapshot_date"] = snapshot_date
    clean_df["snapshot_date_sk"] = date_to_sk(snapshot_date)
    for col in ("is_available", "minimum_nights", "maximum_nights"):
        clean_df[col] = clean_df[col].astype("int64")

    # Khử trùng theo grain (listing_id, date)
    dup_mask = clean_df.duplicated(subset=["listing_id", "calendar_date"], keep="first")
    if dup_mask.any():
        bad = clean_df[dup_mask].copy()
        bad["rejection_reason"] = "Duplicate listing_id and calendar_date"
        rejected_rows.append(bad)
        clean_df = clean_df[~dup_mask]

    avail_count = int((clean_df["is_available"] == 1).sum())
    unavail_count = int((clean_df["is_available"] == 0).sum())

    stats = {
        "dataset": "Calendar",
        "initial_rows": initial_rows,
        "clean_rows": len(clean_df),
        "rejected_rows": initial_rows - len(clean_df),
        "available_nights": avail_count,
        "unavailable_nights": unavail_count,
        "available_ratio": round(avail_count / len(clean_df) * 100, 2) if len(clean_df) > 0 else 0,
    }

    rejected_df = pd.concat(rejected_rows, ignore_index=True) if rejected_rows else pd.DataFrame()
    return clean_df, rejected_df, stats


# ---------------------------------------------------------------------------
# 3. Làm sạch Reviews
# ---------------------------------------------------------------------------
def clean_reviews(df: pd.DataFrame, snapshot_date: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    logger.info("-> Đang làm sạch Reviews...")
    initial_rows = len(df)
    rejected_rows = []

    clean_df = df.copy()

    checks = {}
    for col in ("listing_id", "id", "reviewer_id"):
        clean_df[col] = positive_id(df[col])
        checks[f"Missing or invalid {col}"] = clean_df[col].isna()
    clean_df["review_date"] = iso_dates(df["date"])
    checks["Missing or invalid review date"] = clean_df["review_date"].isna()
    clean_df = reject_invalid(df, clean_df, checks, rejected_rows)
    clean_df["review_id"] = clean_df["id"].astype("int64")
    clean_df["review_date_sk"] = clean_df["review_date"].str.replace("-", "", regex=False).astype("int64")
    clean_df["snapshot_date"] = snapshot_date
    clean_df["snapshot_date_sk"] = date_to_sk(snapshot_date)

    clean_df["reviewer_name"] = clean_df["reviewer_name"].fillna("Anonymous").astype(str).str.strip().replace({"": "Anonymous"})

    # Xử lý comments: trích cờ has_comment và comment_length
    comments_str = clean_df["comments"].fillna("").astype(str).str.strip()
    clean_df["has_comment"] = np.where((comments_str != "") & (comments_str.str.lower() != "nan"), 1, 0)
    clean_df["comment_length"] = np.where(clean_df["has_comment"] == 1, comments_str.str.len(), 0)

    # KHÔNG xóa theo id đơn lẻ! Chỉ khử trùng theo khóa ghép (listing_id, review_id)
    dup_mask = clean_df.duplicated(subset=["listing_id", "review_id"], keep="first")
    if dup_mask.any():
        bad = clean_df[dup_mask].copy()
        bad["rejection_reason"] = "Duplicate composite key (listing_id, review_id)"
        rejected_rows.append(bad)
        clean_df = clean_df[~dup_mask]

    stats = {
        "dataset": "Reviews",
        "initial_rows": initial_rows,
        "clean_rows": len(clean_df),
        "rejected_rows": initial_rows - len(clean_df),
        "null_comments_count": int((clean_df["has_comment"] == 0).sum()),
        "unique_listings_in_reviews": int(clean_df["listing_id"].nunique()),
    }

    rejected_df = pd.concat(rejected_rows, ignore_index=True) if rejected_rows else pd.DataFrame()
    return clean_df, rejected_df, stats


# ---------------------------------------------------------------------------
# 4. Làm sạch Neighbourhoods
# ---------------------------------------------------------------------------
def clean_neighbourhoods(df: pd.DataFrame, snapshot_date: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    logger.info("-> Đang làm sạch Neighbourhoods...")
    initial_rows = len(df)
    rejected_rows = []

    clean_df = df.copy()
    clean_df["neighbourhood_group"] = clean_df["neighbourhood_group"].astype("string").str.strip().fillna("")
    clean_df["neighbourhood_name"] = clean_df["neighbourhood"].astype("string").str.strip().fillna("")

    invalid_mask = (clean_df["neighbourhood_group"] == "") | (clean_df["neighbourhood_name"] == "")
    if invalid_mask.any():
        bad = clean_df[invalid_mask].copy()
        bad["rejection_reason"] = "Empty neighbourhood_group or neighbourhood"
        rejected_rows.append(bad)
        clean_df = clean_df[~invalid_mask]

    clean_df["snapshot_date"] = snapshot_date

    # Khử trùng theo khóa ghép
    dup_mask = clean_df.duplicated(subset=["neighbourhood_group", "neighbourhood_name"], keep="first")
    if dup_mask.any():
        bad = clean_df[dup_mask].copy()
        bad["rejection_reason"] = "Duplicate neighbourhood"
        rejected_rows.append(bad)
        clean_df = clean_df[~dup_mask]

    stats = {
        "dataset": "Neighbourhoods",
        "initial_rows": initial_rows,
        "clean_rows": len(clean_df),
        "rejected_rows": initial_rows - len(clean_df),
        "unique_groups": int(clean_df["neighbourhood_group"].nunique()),
        "unique_neighbourhoods": int(clean_df["neighbourhood_name"].nunique()),
    }

    rejected_df = pd.concat(rejected_rows, ignore_index=True) if rejected_rows else pd.DataFrame()
    return clean_df, rejected_df, stats


# ---------------------------------------------------------------------------
# Pipeline Làm sạch Chính
# ---------------------------------------------------------------------------
def run_cleaning_pipeline(config_path: Path, sample_size: Optional[int] = None) -> Dict[str, Any]:
    config = load_config(config_path)
    snapshot_date = config["project"]["snapshot_date"]
    staging_dir = output_path(config, "staging_dir", sample_size)
    silver_dir = output_path(config, "silver_dir", sample_size)
    rejected_dir = output_path(config, "rejected_dir", sample_size)
    outputs_dir = output_path(config, "outputs_dir", sample_size)

    for d in [silver_dir, rejected_dir, outputs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  AIRBNB SINGAPORE DATA WAREHOUSE – TASK 3.3: DATA CLEANING (SILVER)")
    print(f"  Snapshot Date: {snapshot_date}")
    print("=" * 70)

    # Read identifiers as strings so a single missing key cannot round a BIGINT.
    dtypes = {col: "string" for col in (
        "id", "listing_id", "scrape_id", "host_id", "reviewer_id", "host_profile_id",
        "latitude", "longitude",
    )}
    staged = {}
    for source, cfg in config["sources"].items():
        path = staging_dir / f"{cfg['staging_table']}.csv"
        staged[source] = pd.read_csv(path, dtype=dtypes, low_memory=False)
        if not staged[source]["snapshot_date"].eq(snapshot_date).all():
            raise ValueError(f"Staging snapshot differs from {snapshot_date}: {path}")

    stg_listings = staged["listings"]
    stg_calendar = staged["calendar"]
    stg_reviews = staged["reviews"]
    stg_neighbourhoods = staged["neighbourhoods"]

    all_rejected = []
    audit_records = []

    # 1. Clean Listings
    silver_listings, rej_list, stat_list = clean_listings(stg_listings, snapshot_date)
    silver_listings.to_csv(silver_dir / "silver_listings.csv", index=False, encoding="utf-8-sig")
    if not rej_list.empty:
        all_rejected.append(rej_list.assign(dataset="Listings"))
    audit_records.append(stat_list)

    # 2. Clean Calendar
    silver_calendar, rej_cal, stat_cal = clean_calendar(stg_calendar, snapshot_date)
    silver_calendar.to_csv(silver_dir / "silver_calendar.csv", index=False, encoding="utf-8-sig")
    if not rej_cal.empty:
        all_rejected.append(rej_cal.assign(dataset="Calendar"))
    audit_records.append(stat_cal)

    # 3. Clean Reviews
    silver_reviews, rej_rev, stat_rev = clean_reviews(stg_reviews, snapshot_date)
    silver_reviews.to_csv(silver_dir / "silver_reviews.csv", index=False, encoding="utf-8-sig")
    if not rej_rev.empty:
        all_rejected.append(rej_rev.assign(dataset="Reviews"))
    audit_records.append(stat_rev)

    # 4. Clean Neighbourhoods
    silver_neighbourhoods, rej_nb, stat_nb = clean_neighbourhoods(stg_neighbourhoods, snapshot_date)
    silver_neighbourhoods.to_csv(silver_dir / "silver_neighbourhoods.csv", index=False, encoding="utf-8-sig")
    if not rej_nb.empty:
        all_rejected.append(rej_nb.assign(dataset="Neighbourhoods"))
    audit_records.append(stat_nb)

    # Lưu bản ghi vi phạm (nếu có)
    if all_rejected:
        combined_rej = pd.concat(all_rejected, ignore_index=True)
        combined_rej.to_csv(rejected_dir / "etl_rejected_records.csv", index=False, encoding="utf-8-sig")
        logger.warning(f"Đã lưu {len(combined_rej)} bản ghi bị từ chối vào: {rejected_dir / 'etl_rejected_records.csv'}")
    else:
        logger.info("Tuyệt vời: 0 bản ghi bị từ chối trên toàn bộ 4 tập dữ liệu.")
        # Tạo file rỗng có header để phục vụ kiểm toán
        pd.DataFrame(columns=["dataset", "rejection_reason"]).to_csv(
            rejected_dir / "etl_rejected_records.csv", index=False
        )

    # Lưu báo cáo kiểm toán trước-sau
    audit_df = pd.DataFrame(audit_records)
    audit_csv = outputs_dir / "cleaning_audit_summary.csv"
    audit_df.to_csv(audit_csv, index=False, encoding="utf-8-sig")
    logger.info(f"Đã lưu báo cáo kiểm toán làm sạch tại: {audit_csv}")

    print("\n" + "=" * 70)
    print("  KẾT QUẢ TỔNG HỢP LÀM SẠCH (TASK 3.3)")
    print("=" * 70)
    for rec in audit_records:
        ds = rec["dataset"]
        init = rec["initial_rows"]
        cln = rec["clean_rows"]
        rej = rec["rejected_rows"]
        print(f"  - {ds:<15}: Ban đầu {init:,} dòng -> Sạch {cln:,} dòng (Loại: {rej})")
    print(f"  * Median Listed Price (SGD): {stat_list.get('median_price_sgd')} SGD")
    print(f"  * Valid SGD Price Count    : {stat_list.get('valid_sgd_count'):,} dòng")
    print(f"  * Available Night Ratio    : {stat_cal.get('available_ratio')}%")
    print("=" * 70)

    return {"status": "SUCCESS", "audit": audit_records}


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 3.3: Làm sạch và chuẩn hóa dữ liệu Silver")
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "etl" / "config.yaml",
        help="Đường dẫn file cấu hình YAML",
    )
    args = parser.parse_args()
    run_cleaning_pipeline(config_path=args.config)


if __name__ == "__main__":
    main()
