"""Kiểm tra thiết kế và đối chiếu CSV kết quả MySQL với raw; không kết nối/ghi DB."""
from pathlib import Path
import argparse
import json
import re
import numpy as np
import pandas as pd


def normalized_type(value):
    return str(value).upper().replace("TINYINT(1)", "BOOLEAN").replace(" ", "")


def validate_design(mapping, schema, ddl):
    errors = []
    if not {"table_name", "column_name", "mysql_dtype", "nullable"}.issubset(schema.columns):
        return ["Schema rỗng hoặc thiếu header bắt buộc."]
    if not {"mapping_id", "gold_target_table", "gold_target_column", "gold_mysql_dtype"}.issubset(mapping.columns):
        return ["Mapping rỗng hoặc thiếu header bắt buộc."]
    tables = {"dim_date", "dim_neighbourhood", "dim_listing", "fact_listing_snapshot", "fact_calendar", "fact_review"}
    if set(schema["table_name"]) != tables or schema.empty:
        errors.append("Schema phải có đủ 6 bảng, không được rỗng.")
    if schema.duplicated(["table_name", "column_name"]).any():
        errors.append("Trùng tên cột trong schema.")
    indexed = {(r.table_name, r.column_name): r for r in schema.itertuples()}
    ddl_columns = {}
    for table, body in re.findall(r"CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\n\) ENGINE=", ddl, re.S):
        for line in body.splitlines():
            match = re.match(r"\s*`?(\w+)`?\s+((?:BIGINT|SMALLINT|TINYINT|INT|DECIMAL|VARCHAR|CHAR|BOOLEAN|DATETIME|DATE)(?:\([\d,]+\))?(?: UNSIGNED)?)\s+(NOT NULL|NULL)", line)
            if match:
                ddl_columns[(table, match[1])] = match.groups()[1:]
    if set(ddl_columns) != set(indexed):
        errors.append("Danh sách cột schema CSV không khớp DDL: " + str(sorted(set(ddl_columns) ^ set(indexed))))
    for key in set(ddl_columns) & set(indexed):
        dtype, nullable = ddl_columns[key]
        row = indexed[key]
        if normalized_type(dtype) != normalized_type(row.mysql_dtype) or nullable != row.nullable:
            errors.append(f"CSV/DDL khác kiểu hoặc NULL tại {key}.")
    for row in mapping.itertuples():
        if row.gold_target_table.startswith("N/A"):
            continue
        targets = [x.strip() for x in row.gold_target_table.split(";")]
        columns = [re.sub(r"\s*\(.*", "", x).strip() for x in row.gold_target_column.split(";")]
        types = [x.strip() for x in row.gold_mysql_dtype.split(";")]
        for table in targets:
            for i, column in enumerate(columns):
                key = (table, column)
                if key not in indexed:
                    errors.append(f"{row.mapping_id}: không tồn tại {table}.{column}.")
                elif len(types) in (1, len(columns)):
                    dtype = types[0] if len(types) == 1 else types[i]
                    if normalized_type(dtype) != normalized_type(indexed[key].mysql_dtype):
                        errors.append(f"{row.mapping_id}: khác kiểu tại {table}.{column}.")
    return errors


def raw_metrics(raw_dir, inventory_path, review_start=None, review_end=None):
    inventory = pd.read_csv(inventory_path, dtype=str)
    dates = inventory["snapshot_date"].dropna().unique()
    if len(dates) != 1:
        raise ValueError("Chọn đúng một snapshot trong inventory trước khi đối chiếu.")
    snapshot = str(dates[0])
    listings = pd.read_csv(Path(raw_dir) / "listings.csv.gz", low_memory=False)
    calendar = pd.read_csv(Path(raw_dir) / "calendar.csv.gz", low_memory=False)
    reviews = pd.read_csv(Path(raw_dir) / "reviews.csv.gz", low_memory=False)
    if listings["id"].isna().any() or listings["id"].duplicated().any():
        raise ValueError("Listings.id thiếu hoặc trùng; không được tính KPI từ mẫu bị nhân bản.")
    records = []
    def add(metric, value, group="ALL"):
        records.append({"snapshot_date": snapshot, "metric": metric, "group_value": group,
                        "value": round(float(value), 4) if pd.notna(value) else np.nan})
    price = pd.to_numeric(listings["price"].astype("string").str.replace("$", "", regex=False).str.replace(",", "", regex=False), errors="coerce")
    def currency(value):
        try:
            quote = json.loads(value).get("quote", {})
            code = quote.get("currency")
            return code.strip().upper() if isinstance(code, str) else None
        except (TypeError, ValueError, AttributeError):
            return None
    valid_price = price.notna() & np.isfinite(price) & price.gt(0) & listings["price_quote_raw"].map(currency).eq("SGD")
    rating = pd.to_numeric(listings["review_scores_rating"], errors="coerce")
    rating = rating[rating.notna() & np.isfinite(rating) & rating.between(1, 5)]
    counts = pd.to_numeric(listings["number_of_reviews"], errors="coerce")
    counts = counts[counts.notna() & np.isfinite(counts) & counts.ge(0) & counts.mod(1).eq(0)]
    cal_dates = pd.to_datetime(calendar["date"], errors="coerce")
    cal_start, cal_end = cal_dates.min(), cal_dates.max()
    available = calendar["available"].astype("string").str.strip().str.lower()
    mapped = available.map({"t": 1, "true": 1, "1": 1, "f": 0, "false": 0, "0": 0})
    cal_valid = cal_dates.between(cal_start, cal_end) & mapped.notna()
    review_dates = pd.to_datetime(reviews["date"], errors="coerce")
    start = pd.Timestamp(review_start) if review_start else review_dates.min()
    end = pd.Timestamp(review_end) if review_end else review_dates.max()
    valid_review = review_dates.between(start, end)
    for column in ("listing_id", "id"):
        number = pd.to_numeric(reviews[column], errors="coerce")
        valid_review &= number.notna() & np.isfinite(number) & number.gt(0) & number.mod(1).eq(0)
    add("KPI-01", listings["id"].nunique())
    add("KPI-02", price[valid_price].median())
    add("PRICE_VALID_COUNT", valid_price.sum())
    for room, n in listings.groupby("room_type", dropna=False).size().items():
        if pd.isna(room):
            raise ValueError("room_type NULL cần xử lý/định nghĩa nhóm Unknown trước khi đối chiếu.")
        add("KPI-03_COUNT", n, str(room))
        add("KPI-03_PERCENT", n / len(listings) * 100, str(room))
    add("KPI-04", mapped[cal_valid].mean() * 100)
    add("AVAILABLE_NIGHTS", mapped[cal_valid].sum())
    add("VALID_CALENDAR_NIGHTS", cal_valid.sum())
    add("KPI-05", rating.mean())
    add("RATING_VALID_COUNT", len(rating))
    add("SUP-01", counts.median())
    add("REVIEW_COUNT_VALID_LISTINGS", len(counts))
    add("SUP-02", len(reviews.loc[valid_review, ["listing_id", "id"]].drop_duplicates()))
    add("LISTING_ROWS", len(listings))
    add("CALENDAR_ROWS", len(calendar))
    add("REVIEW_ROWS", len(reviews))
    add("PRICE_NULL_COUNT", len(listings) - int(valid_price.sum()))
    add("RATING_NULL_COUNT", listings["review_scores_rating"].isna().sum())
    add("DUP_LISTING_GRAIN", listings.duplicated(["id"]).sum())
    add("DUP_CALENDAR_GRAIN", calendar.duplicated(["listing_id", "date"]).sum())
    add("DUP_REVIEW_GRAIN", reviews.duplicated(["listing_id", "id"]).sum())
    for name, child in [("CALENDAR", calendar), ("REVIEW", reviews)]:
        add(f"ORPHAN_{name}_LISTING", (~child["listing_id"].isin(listings["id"])).sum())
    context = {"snapshot_date": snapshot, "calendar_start": str(cal_start.date()),
               "calendar_end": str(cal_end.date()), "review_start": str(start.date()), "review_end": str(end.date())}
    return pd.DataFrame(records), context


def compare_metrics(expected, observed):
    keys = ["snapshot_date", "metric", "group_value"]
    for name, data in [("raw", expected), ("Gold CSV", observed)]:
        if not set(keys + ["value"]).issubset(data.columns):
            raise ValueError(f"{name}: thiếu cột {keys + ['value']}")
        if data[keys].isna().any().any() or data.duplicated(keys).any():
            raise ValueError(f"{name}: khóa đối chiếu thiếu/trùng.")
    joined = expected.merge(observed, on=keys, how="outer", suffixes=("_raw", "_gold"), indicator=True)
    # NULL hợp lệ phải được xuất thành ô rỗng hoặc NULL, không biến lỗi parse thành NULL.
    for column in ("value_raw", "value_gold"):
        original = joined[column]
        converted = pd.to_numeric(original, errors="coerce")
        if (original.notna() & converted.isna()).any() or np.isinf(converted.dropna()).any():
            raise ValueError(f"{column}: có giá trị không phải số hữu hạn.")
        joined[column] = converted
    joined["difference_gold_minus_raw"] = joined["value_gold"] - joined["value_raw"]
    both_null = joined["value_gold"].isna() & joined["value_raw"].isna()
    equal = both_null | joined["difference_gold_minus_raw"].abs().le(0.00005)
    joined["status"] = np.where(joined["_merge"].eq("both") & equal, "PASS", "FAIL")
    return joined.drop(columns="_merge")


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-csv", type=Path, help="CSV kết quả SELECT MySQL đã xuất, có header")
    parser.add_argument("--review-start")
    parser.add_argument("--review-end")
    parser.add_argument("--output-dir", type=Path, default=root / "tests" / "gold_reconciliation")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    expected, context = raw_metrics(root / "data/raw", root / "docs/source_inventory.csv", args.review_start, args.review_end)
    expected.to_csv(args.output_dir / "raw_expected_metrics.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "comparison_context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Phạm vi bắt buộc dùng giống nhau ở MySQL:", json.dumps(context, ensure_ascii=False))
    if not args.gold_csv:
        print("Đã xuất baseline raw. Gold/MySQL: NOT_RUN; chưa có CSV đối chiếu.")
        return 0
    gold = pd.read_csv(args.gold_csv, dtype={"snapshot_date": str, "metric": str, "group_value": str}, keep_default_na=False, na_values=["", "NULL"])
    comparison = compare_metrics(expected, gold)
    comparison.to_csv(args.output_dir / "raw_vs_gold.csv", index=False, encoding="utf-8-sig")
    failed = comparison["status"].eq("FAIL")
    print(comparison.loc[failed].to_string(index=False) if failed.any() else "PASS: mọi chỉ tiêu và mẫu số trong CSV khớp raw ở độ chính xác 4 số lẻ.")
    print("Đây là đối chiếu kết quả tổng hợp; vẫn cần kiểm thử dữ liệu từng dòng và chạy lại pipeline.")
    return int(failed.any())


if __name__ == "__main__":
    raise SystemExit(main())
