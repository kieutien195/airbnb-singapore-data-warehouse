from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "2026-09-23"
CAL_START, CAL_END = "2026-09-25", "2027-09-25"
REV_START, REV_END = "2011-05-04", "2026-09-25"
REGION, ROOM = "Central Region", "Private room"
KEYS = ["snapshot_date", "kpi_id", "region", "room_type"]
VALUES = ["metric_value", "sample_count", "support_value"]
INTEGER_KPIS = {"KPI-01", "SUP-02"}
HINTS = {
    "KPI-01": "Kiểm tra DISTINCT listing_id và snapshot.",
    "KPI-02": "Kiểm tra SGD, cờ xác minh, giá dương, NULL và median.",
    "KPI-03": "Kiểm tra room_type, JOIN khu vực và mẫu số listing hợp lệ.",
    "KPI-04": "Kiểm tra kỳ Calendar, cờ 0/1 và tử số/mẫu số đêm.",
    "KPI-05": "Kiểm tra rating 1–5, NULL, tổng điểm và số listing có điểm.",
    "SUP-01": "Giữ số review 0, loại NULL, kiểm tra median chẵn/lẻ.",
    "SUP-02": "Kiểm tra kỳ Reviews, khóa ghép listing_id/review_id và phạm vi listing.",
}


def silver_frame(path, columns, grain):
    frame = pd.read_csv(path, usecols=columns, dtype="string", encoding="utf-8-sig")
    frame = frame.loc[frame["snapshot_date"].eq(SNAPSHOT).fillna(False)].copy()
    if frame.empty:
        raise ValueError(f"{path.name}: không có dòng cho snapshot {SNAPSHOT}")
    if frame[grain].isna().any().any() or frame.duplicated(grain).any():
        raise ValueError(f"{path.name}: khóa thiếu hoặc trùng theo {grain}")
    return frame


def compute_silver(directory):
    l = silver_frame(
        directory / "silver_listings.csv",
        ["id", "snapshot_date", "room_type", "neighbourhood_group_cleansed",
         "listed_price_sgd", "quote_currency", "is_price_sgd_verified",
         "review_scores_rating", "number_of_reviews"],
        ["id"],
    ).rename(columns={"id": "listing_id", "neighbourhood_group_cleansed": "region"})
    c = silver_frame(
        directory / "silver_calendar.csv",
        ["listing_id", "snapshot_date", "calendar_date", "is_available"],
        ["listing_id", "calendar_date"],
    )
    r = silver_frame(
        directory / "silver_reviews.csv",
        ["listing_id", "review_id", "snapshot_date", "review_date"],
        ["listing_id", "review_id"],
    )
    rows = []

    def add(kpi, value, sample, support=None, region="ALL", room="ALL"):
        rows.append(dict(zip(KEYS + VALUES, [SNAPSHOT, kpi, region, room, value, sample, support])))

    price = pd.to_numeric(l["listed_price_sgd"], errors="coerce").astype(float)
    price = price[price.gt(0) & np.isfinite(price)
                  & l["quote_currency"].eq("SGD").fillna(False).astype(bool)
                  & l["is_price_sgd_verified"].isin(["1", "True"]).astype(bool)]
    review_count = pd.to_numeric(l["number_of_reviews"], errors="coerce").astype(float)
    review_count = review_count[review_count.ge(0) & np.isfinite(review_count)]
    l["rating"] = pd.to_numeric(l["review_scores_rating"], errors="coerce").astype(float)
    rated = l[l["rating"].between(1, 5)]
    rooms = l[l["room_type"].notna() & l["room_type"].ne("")]
    c = c[c["calendar_date"].between(CAL_START, CAL_END).fillna(False)].copy()
    c["available"] = c["is_available"].map({"0": 0, "1": 1})
    c = c.dropna(subset=["available"])
    r = r[r["review_date"].between(REV_START, REV_END).fillna(False)]
    subset = l.loc[l["region"].eq(REGION) & l["room_type"].eq(ROOM), "listing_id"]
    filtered_reviews = r[r["listing_id"].isin(subset)]
    filtered_counts = review_count[review_count.index.isin(subset.index)]

    add("KPI-01", l["listing_id"].nunique(), len(l))
    add("KPI-02", price.median(), len(price))
    add("KPI-04", c["available"].mean() * 100, len(c), c["available"].sum())
    add("KPI-05", rated["rating"].mean(), len(rated), rated["rating"].sum() if len(rated) else None)
    add("SUP-01", review_count.median(), len(review_count))
    add("SUP-02", len(r), r["listing_id"].nunique())
    add("SUP-01", filtered_counts.median(), len(filtered_counts), region=REGION, room=ROOM)
    add("SUP-02", len(filtered_reviews), filtered_reviews["listing_id"].nunique(), region=REGION, room=ROOM)

    for room, group in rooms.groupby("room_type"):
        add("KPI-03", len(group) * 100 / len(rooms), len(rooms), len(group), room=room)
    for region, regional_rooms in rooms.groupby("region"):
        for room, group in regional_rooms.groupby("room_type"):
            add("KPI-03", len(group) * 100 / len(regional_rooms),
                len(regional_rooms), len(group), region, room)
    c = c.merge(l[["listing_id", "region"]], on="listing_id", validate="many_to_one")
    for region, group in c.groupby("region"):
        add("KPI-04", group["available"].mean() * 100, len(group), group["available"].sum(), region)
    for region, group in rated.groupby("region"):
        add("KPI-05", group["rating"].mean(), len(group), group["rating"].sum(), region)
    return pd.DataFrame(rows)


def numeric(value):
    if pd.isna(value) or str(value).strip() in {"", "NULL"}:
        return None
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValueError("Giá trị SQL không hữu hạn")
    return parsed


def compare(expected, sql):
    if not set(KEYS + VALUES).issubset(sql.columns):
        raise ValueError("CSV Workbench thiếu header: " + ", ".join(KEYS + VALUES))
    sql = sql[KEYS + VALUES].copy()
    if sql.empty or sql[KEYS].isna().any().any() or sql[KEYS].eq("").any().any():
        raise ValueError("CSV Workbench rỗng hoặc thiếu khóa đối chiếu")
    if sql.duplicated(KEYS).any():
        raise ValueError("CSV Workbench có khóa chỉ tiêu trùng")
    joined = expected.merge(sql, on=KEYS, how="outer", suffixes=("_silver", "_sql"),
                            indicator=True, validate="one_to_one")
    rows = []
    for _, row in joined.iterrows():
        record = {col: row[col] for col in KEYS}
        kpi = row["kpi_id"]
        differences = []
        rounded_matches = []
        for column in VALUES:
            s = numeric(row[f"{column}_silver"])
            q = numeric(row[f"{column}_sql"])
            record[f"{column}_silver"] = s
            record[f"{column}_sql"] = q
            record[f"{column}_delta_sql_minus_silver"] = q - s if s is not None and q is not None else None
            rounded = (
                (column == "metric_value" and kpi not in INTEGER_KPIS)
                or (column == "support_value" and kpi == "KPI-05")
            )
            compared = s.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if rounded and s is not None else s
            record[f"{column}_silver_at_sql_precision"] = compared
            record[f"{column}_comparison_delta"] = (
                q - compared if q is not None and compared is not None else None
            )
            if compared != q:
                differences.append(column)
            elif s != q:
                rounded_matches.append(column)
        side = row["_merge"]
        notes = (
            ["Thiếu dòng kết quả SQL"] if side == "left_only"
            else ["Dòng SQL ngoài phạm vi Silver"] if side == "right_only"
            else differences
        )
        record.update(status="FAIL" if notes else "PASS",
                      match_type=("MISMATCH" if notes else
                                  "MATCH_AT_SQL_PRECISION" if rounded_matches else "EXACT"),
                      rounded_fields=" | ".join(rounded_matches),
                      note=" | ".join(notes),
                      investigation=HINTS.get(kpi, "Kiểm tra phạm vi SQL") if notes else "",
                      owner_to_confirm="Hồng + Minh (xác định nguồn lệch)" if notes else "",
                      retest_status="PENDING" if notes else "",
                      calendar_window=f"{CAL_START}..{CAL_END}" if kpi == "KPI-04" else "",
                      review_window=f"{REV_START}..{REV_END}" if kpi == "SUP-02" else "")
        rows.append(record)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sql-csv", required=True, type=Path)
    parser.add_argument("--silver-dir", type=Path, default=ROOT / "data/processed/silver")
    parser.add_argument("--output", type=Path, default=ROOT / "tests/KPI_reconciliation.csv")
    parser.add_argument("--previous", type=Path, help="Báo cáo 4.2 trước sửa để theo dõi kết quả kiểm tra lại")
    args = parser.parse_args()
    try:
        expected = compute_silver(args.silver_dir)
        sql = pd.read_csv(args.sql_csv, dtype="string", encoding="utf-8-sig",
                          keep_default_na=False)
        report = compare(expected, sql)
        if args.previous:
            previous = pd.read_csv(args.previous, dtype="string", encoding="utf-8-sig")
            before = previous[KEYS + ["status"]].rename(columns={"status": "previous_status"})
            report = report.merge(before, on=KEYS, how="left", validate="one_to_one")
            report["retest_status"] = report["status"].where(report["previous_status"].eq("FAIL").fillna(False), "")
    except (OSError, ValueError, KeyError, InvalidOperation) as exc:
        report = pd.DataFrame([dict(snapshot_date=SNAPSHOT, status="BLOCKED", note=str(exc),
                                    owner_to_confirm="Hồng + Minh")])
    report.insert(0, "checked_at_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    report["sql_export_file"] = args.sql_csv.name
    report["sql_export_sha256"] = (
        hashlib.sha256(args.sql_csv.read_bytes()).hexdigest() if args.sql_csv.is_file() else ""
    )
    report.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(report["status"].value_counts().to_string())
    print(f"Report: {args.output}")
    return 2 if report.status.eq("BLOCKED").any() else int(report.status.eq("FAIL").any())


if __name__ == "__main__":
    raise SystemExit(main())

