from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
FACTS = {
    "fact_listing_snapshot": ["listing_id", "snapshot_date"],
    "fact_calendar": ["listing_id", "calendar_date", "snapshot_date"],
    "fact_review": ["listing_id", "review_id", "snapshot_date"],
}
GRAIN = {
    **FACTS,
    "dim_listing": ["listing_id", "snapshot_date"],
    "dim_neighbourhood": ["neighbourhood_group", "neighbourhood_name"],
    "dim_date": ["full_date"],
}
TARGETS = {
    "listings": ("fact_listing_snapshot", {"id": "listing_id"}),
    "calendar": ("fact_calendar", {}),
    "reviews": ("fact_review", {}),
    "neighbourhoods": ("dim_neighbourhood", {}),
}
PRIMARY = dict(zip(GRAIN, ["listing_snapshot_sk", "calendar_sk", "review_sk",
                          "listing_sk", "neighbourhood_sk", "date_sk"]))


def ddl_columns(path):
    """Column names and constraints from the committed warehouse DDL."""
    tables = {}
    for match in re.finditer(r"CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\n\)\s*ENGINE", path.read_text(encoding="utf-8-sig"), re.S):
        tables[match[1]] = {}
        for line in match[2].splitlines():
            col = re.match(r"\s*(\w+)\s+(DATE\b|BIGINT\b|INT\b|SMALLINT\b|TINYINT\b|BOOLEAN\b|DECIMAL\b|VARCHAR\b|CHAR\b|TEXT\b|DATETIME\b|ENUM\b|DOUBLE\b|FLOAT\b|YEAR\b|TIMESTAMP\b)", line)
            if col:
                tables[match[1]][col[1]] = (col[2], "NOT NULL" in line.split("COMMENT", 1)[0])
    if set(GRAIN) - tables.keys():
        raise ValueError("Warehouse DDL is missing a required QA table")
    return tables


def read(path):
    # Read IDs as strings to avoid loss of precision for Airbnb BIGINT IDs.
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False).replace("", pd.NA)


def keys(frame, columns):
    return pd.MultiIndex.from_frame(frame[columns].astype("string"))


def mismatch(frame, parent, columns, parent_columns):
    return int((~keys(frame, columns).isin(keys(parent, parent_columns))).sum())


def invalid_date(series):
    return series.notna() & (
        ~series.astype("string").str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
        | pd.to_datetime(series, format="%Y-%m-%d", errors="coerce").isna()
    )


class QA:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.run_id = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.results = []

    def record(self, check, layer, table, rule, observed, bad, owner, evidence="", note="", severity="CRITICAL"):
        self.results.append(dict(
            run_id=self.run_id, snapshot_date=self.snapshot, check_id=check,
            layer=layer, table_name=table, rule=rule, observed=observed,
            failed_count=bad,
            status=("INFO" if severity == "INFO" else
                    "BLOCKED" if bad is None else "FAIL" if bad else "PASS"),
            severity=severity, owner=owner, evidence=evidence, note=note,
        ))

    def shape(self, layer, table, df, grain, required, dates):
        owner = "Minh" if layer == "MySQL" else "Thái"
        expected = set(grain) | set(required) | set(dates)
        missing = sorted(expected - set(df))
        self.record("SCHEMA", layer, table, "Các cột được kiểm tra tồn tại", str(missing), len(missing), owner)
        self.record("NONEMPTY", layer, table, "Có dữ liệu để kiểm tra", len(df), int(df.empty), owner)
        if missing:
            return False
        null_count = int(df[list(required)].isna().any(axis=1).sum()) if required else 0
        self.record("REQUIRED", layer, table, "Trường bắt buộc khác NULL", null_count, null_count, owner)
        dup = int(df.duplicated(grain).sum())
        self.record("GRAIN", layer, table, "Duy nhất: " + ", ".join(grain), dup, dup, owner)
        for column in dates:
            bad = int(invalid_date(df[column]).sum())
            self.record("DATE", layer, table, f"{column}: ngày ISO hợp lệ", bad, bad, owner)
        if "snapshot_date" in df:
            bad = int((~df["snapshot_date"].eq(self.snapshot).fillna(False)).sum())
            self.record("SNAPSHOT", layer, table, "Đúng snapshot", bad, bad, owner)
        return True

    def warehouse(self, layer, tables, contract):
        owner = "Minh" if layer == "MySQL" else "Thái"
        for table, df in tables.items():
            required = [c for c, (_, mandatory) in contract[table].items()
                        if mandatory and (layer == "MySQL" or c != "created_at")]
            dates = [c for c, (kind, _) in contract[table].items() if kind == "DATE"]
            if not self.shape(layer, table, df, GRAIN[table], required, dates):
                continue
            pk = PRIMARY[table]
            bad = int(df[pk].duplicated().sum())
            self.record("SURROGATE", layer, table, "Surrogate key duy nhất", bad, bad, owner)
            if table in FACTS:
                parent_cols = ["listing_sk", "snapshot_date_sk", "neighbourhood_sk", "listing_id"]
                bad = mismatch(df, tables["dim_listing"], parent_cols, parent_cols)
                self.record("FK_LISTING", layer, table, "Khớp cả business key và khóa Listing/Snapshot/Geo", bad, bad, owner)
            if "neighbourhood_sk" in df and table != "dim_neighbourhood":
                bad = mismatch(df, tables["dim_neighbourhood"], ["neighbourhood_sk"], ["neighbourhood_sk"])
                self.record("FK_GEO", layer, table, "Khoá khu vực tồn tại", bad, bad, owner)
            for key, col in [("snapshot_date_sk", "snapshot_date"), ("calendar_date_sk", "calendar_date"), ("review_date_sk", "review_date")]:
                if key in df:
                    bad = mismatch(df, tables["dim_date"], [key, col], ["date_sk", "full_date"])
                    self.record("FK_DATE", layer, table, f"{key} khớp ngày trong dim_date", bad, bad, owner)
            if table == "fact_listing_snapshot":
                price = pd.to_numeric(df.listed_price_sgd, errors="coerce")
                valid = price.gt(0) & np.isfinite(price)
                flag = df.is_price_sgd_verified.astype("string").isin(["1", "True"])
                invalid = (df.listed_price_sgd.notna() & ~(valid & df.quote_currency.eq("SGD").fillna(False))) | flag.ne(df.listed_price_sgd.notna())
                invalid |= ~df.is_price_sgd_verified.astype("string").isin(["0", "1", "True", "False"])
                bad = int(invalid.sum())
                self.record("PRICE", layer, table, "Giá SGD hữu hạn > 0; currency và cờ nhất quán; NULL được phép", bad, bad, owner)
                rating = pd.to_numeric(df.review_scores_rating, errors="coerce")
                bad = int((df.review_scores_rating.notna() & ~rating.between(1, 5).fillna(False)).sum())
                self.record("RATING", layer, table, "Điểm hợp lệ từ 1 đến 5 hoặc NULL", bad, bad, owner)
            if table == "fact_calendar":
                low = pd.to_numeric(df.minimum_nights, errors="coerce")
                high = pd.to_numeric(df.maximum_nights, errors="coerce")
                bad = int((~df.is_available.astype("string").isin(["0", "1", "True", "False"]) | ~(low.ge(1) & high.ge(low)).fillna(False)).sum())
                self.record("CALENDAR_DOMAIN", layer, table, "available 0/1; 1 ≤ minimum_nights ≤ maximum_nights", bad, bad, owner)
            if table == "fact_review":
                bad = int((~df.review_count.astype("string").eq("1").fillna(False) | ~df.has_comment.astype("string").isin(["0", "1", "True", "False"])).sum())
                self.record("REVIEW_DOMAIN", layer, table, "review_count = 1 và has_comment 0/1", bad, bad, owner)
        for table in FACTS:
            frame = tables[table]
            join_keys = ["listing_sk", "snapshot_date_sk", "neighbourhood_sk"]
            counts = tables["dim_listing"].groupby(join_keys, dropna=False).size()
            multiplicity = keys(frame, join_keys).map(counts).fillna(0)
            extra = int(np.maximum(multiplicity.to_numpy() - 1, 0).sum())
            self.record("JOIN_FANOUT", layer, table, "JOIN Fact → dim_listing không nhân dòng", extra, extra, owner)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mysql", action="store_true", help="Kiểm tra thêm bản load MySQL qua .env")
    args = parser.parse_args()
    cfg = yaml.safe_load((ROOT / "etl/config.yaml").read_text(encoding="utf-8"))
    snapshot = date.fromisoformat(str(cfg["project"]["snapshot_date"])).isoformat()
    qa = QA(snapshot)
    paths = {k: ROOT / v for k, v in cfg["paths"].items()}
    contract = ddl_columns(ROOT / "sql/02_warehouse_schema.sql")
    inputs = [paths["gold_dir"] / f"{t}.csv" for t in GRAIN]
    for source, spec in cfg["sources"].items():
        inputs.extend([
            paths["raw_dir"] / spec["file_name"],
            paths["staging_dir"] / f"{spec['staging_table']}.csv",
            paths["silver_dir"] / f"silver_{source}.csv",
        ])
    inputs.extend([paths["outputs_dir"] / "cleaning_audit_summary.csv",
                   paths["rejected_dir"] / "etl_rejected_records.csv"])
    missing = [p.relative_to(ROOT).as_posix() for p in inputs if not p.is_file()]
    if missing:
        qa.record("INPUTS", "ETL", "snapshot", "Đủ dữ liệu full run", len(missing), None,
                  "Thái", note=" | ".join(missing))
        pd.DataFrame(qa.results).to_csv(ROOT / "tests/qa_results.csv", index=False, encoding="utf-8-sig")
        print("BLOCKED: chạy full ETL trước. Xem tests/qa_results.csv.")
        return 2
    gold = {t: read(paths["gold_dir"] / f"{t}.csv") for t in GRAIN}
    qa.warehouse("Gold CSV", gold, contract)
    raw, staged, silver = {}, {}, {}
    counts = []
    audit = read(paths["outputs_dir"] / "cleaning_audit_summary.csv").set_index("dataset")
    rejected = read(paths["rejected_dir"] / "etl_rejected_records.csv")
    for source, spec in cfg["sources"].items():
        raw[source] = r = read(paths["raw_dir"] / spec["file_name"])
        staged[source] = st = read(paths["staging_dir"] / f"{spec['staging_table']}.csv")
        silver[source] = si = read(paths["silver_dir"] / f"silver_{source}.csv")
        target, renames = TARGETS[source]
        natural = spec["natural_key"]
        silver_key = {
            "listings": ["id", "snapshot_date"],
            "calendar": ["listing_id", "calendar_date", "snapshot_date"],
            "reviews": ["listing_id", "review_id", "snapshot_date"],
            "neighbourhoods": ["neighbourhood_group", "neighbourhood_name", "snapshot_date"],
        }[source]
        qa.shape("Staging CSV", source, st, natural + ["snapshot_date"], natural + ["snapshot_date"], ["snapshot_date"])
        qa.shape("Silver CSV", source, si, silver_key, silver_key, [c for c in silver_key if "date" in c])
        raw_diff = abs(len(r) - len(st)) + mismatch(r, st, natural, natural) + mismatch(st, r, natural, natural)
        qa.record("RAW_STAGING", "Reconciliation", source, "Số dòng và khóa nguồn khớp staging", raw_diff, raw_diff, "Thái")
        rej = rejected.loc[rejected.dataset.astype("string").str.lower().eq(source)]
        reasons = Counter(rej.rejection_reason.dropna())
        a = audit.loc[source.capitalize()]
        clean_diff = abs(len(st) - len(si) - len(rej)) + int(rej.rejection_reason.isna().sum())
        clean_diff += sum(int(int(a[c]) != n) for c, n in [("initial_rows", len(st)), ("clean_rows", len(si)), ("rejected_rows", len(rej))])
        qa.record("STAGING_SILVER", "Reconciliation", source, "Staging = Silver + rejected; lý do và audit khớp", clean_diff, clean_diff, "Thái", "outputs/cleaning_audit_summary.csv")
        g = gold[target]
        transformed = si.rename(columns=renames)
        gkeys = GRAIN[target]
        gold_diff = abs(len(si) - len(g)) + mismatch(transformed, g, gkeys, gkeys) + mismatch(g, transformed, gkeys, gkeys)
        qa.record("SILVER_GOLD", "Reconciliation", target, "Số dòng và grain Silver khớp bảng Gold tương ứng", gold_diff, gold_diff, "Thái")
        counts.append(dict(snapshot_date=snapshot, dataset=source, raw_rows=len(r), staging_rows=len(st),
                           silver_rows=len(si), gold_table=target, gold_rows=len(g), rejected_rows=len(rej),
                           rejection_reasons=" | ".join(f"{k}: {v}" for k, v in sorted(reasons.items())) or "Không loại dòng",
                           unexplained_difference=raw_diff + clean_diff + gold_diff))
    # Random sample over distinct listing IDs, repeatable across runs.
    population = sorted(raw["listings"].id.dropna().unique())
    samples = pd.Series(population).sample(n=min(25, len(population)), random_state=37).tolist()
    from etl.clean import extract_currency_from_json, parse_price

    calendar_by_listing = gold["fact_calendar"].groupby("listing_id").size()
    review_by_listing = gold["fact_review"].groupby("listing_id").size()
    potential = int(calendar_by_listing.mul(review_by_listing, fill_value=0).sum())
    qa.record("FACT_JOIN_RISK", "Gold CSV", "fact_calendar + fact_review",
              "Định lượng số dòng INNER JOIN trực tiếp theo listing trong snapshot",
              potential, None, "Minh", note="Đây là minh chứng rủi ro của JOIN fact chi tiết. Tổng hợp từng fact trước khi ghép theo listing và snapshot.",
              severity="INFO")
    sample_rows = []
    for source in ("listings", "calendar", "reviews"):
        target, _ = TARGETS[source]
        raw_id = "id" if source == "listings" else "listing_id"
        frames = [raw[source], staged[source], silver[source], gold[target]]
        grouped = [f.groupby(raw_id if i < 3 else "listing_id", sort=False) for i, f in enumerate(frames)]
        for listing in samples:
            part = [g.get_group(listing) if listing in g.groups else f.iloc[:0] for g, f in zip(grouped, frames)]
            a, b, c, d = part
            if source == "calendar":
                raw_values = Counter(zip(a.date, a.available.str.lower().map({"t": "1", "f": "0"})))
                gold_values = Counter(zip(d.calendar_date, d.is_available))
            elif source == "reviews":
                raw_values = Counter(zip(a.id, a.date))
                gold_values = Counter(zip(d.review_id, d.review_date))
            else:
                raw_values = Counter(zip(a.id, a.room_type))
                dim = gold["dim_listing"]
                gold_values = Counter(zip(dim.loc[dim.listing_id.eq(listing), "listing_id"], dim.loc[dim.listing_id.eq(listing), "room_type"]))
            gold_compare = ["snapshot_date"]
            if source == "listings":
                gold_compare += ["listed_price_sgd", "review_scores_rating", "quote_currency", "is_price_sgd_verified"]
                expected_prices = []
                for raw_price, quote in zip(a.price, a.price_quote_raw):
                    amount = parse_price(raw_price)
                    currency = extract_currency_from_json(quote)
                    expected_prices.append(round(amount, 2) if amount is not None and amount > 0 and currency == "SGD" else None)
                actual_prices = [round(float(x), 2) if pd.notna(x) else None for x in d.listed_price_sgd]
                price_match = expected_prices == actual_prices
            else:
                gold_compare += ["calendar_date", "is_available"] if source == "calendar" else ["review_id", "review_date"]
                price_match = True
            silver_gold_match = Counter(c[gold_compare].fillna("<NULL>").itertuples(index=False, name=None)) == Counter(d[gold_compare].fillna("<NULL>").itertuples(index=False, name=None))
            ok = (len(a) == len(b) == len(c) == len(d) and raw_values == gold_values
                  and silver_gold_match and price_match)
            sample_rows.append(dict(snapshot_date=snapshot, seed=37, listing_id=listing, dataset=source,
                                    raw_rows=len(a), staging_rows=len(b), silver_rows=len(c), gold_rows=len(d),
                                    raw_to_gold_values_match=raw_values == gold_values,
                                    silver_to_gold_values_match=silver_gold_match,
                                    price_rule_matches=price_match if source == "listings" else "",
                                    status="PASS" if ok else "FAIL"))
    bad = sum(row["status"] == "FAIL" for row in sample_rows)
    qa.record("SAMPLE", "Reconciliation", "listing_id", "Mẫu 25 listing seed 37; số dòng và giá trị đại diện", len(sample_rows), bad, "Thái", "tests/data_quality_checks/sample_validation.csv")
    if args.mysql:
        try:
            from etl.db import get_engine
            from sqlalchemy import text
            engine = get_engine()
            if engine is None:
                raise RuntimeError("Missing MySQL configuration")
            try:
                with engine.connect() as conn:
                    live = {}
                    for table in GRAIN:
                        where = "" if table == "dim_date" else " WHERE snapshot_date = :snapshot"
                        live[table] = pd.read_sql(text(f"SELECT * FROM `{table}`" + where), conn, params={"snapshot": snapshot}).astype("string")
                    qa.warehouse("MySQL", live, contract)
                    native = conn.execute(text(
                        "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE()"
                    )).all()
                    native_types = {(t, c): dt for t, c, dt in native}
                    for table, columns in contract.items():
                        bad_dates = [c for c, (kind, _) in columns.items()
                                     if kind == "DATE" and native_types.get((table, c)) != "date"]
                        qa.record("MYSQL_DATE_TYPE", "MySQL", table, "Cột DATE khớp DDL", str(bad_dates), len(bad_dates), "Minh")
                    for table, frame in live.items():
                        grain = GRAIN[table]
                        bad = abs(len(frame) - len(gold[table])) + mismatch(frame, gold[table], grain, grain) + mismatch(gold[table], frame, grain, grain)
                        qa.record("MYSQL_GOLD", "MySQL", table, "Số dòng và khóa khớp Gold CSV", bad, bad, "Minh")
                    for source, spec in cfg["sources"].items():
                        count = conn.execute(text(f"SELECT COUNT(*) FROM `{spec['staging_table']}` WHERE snapshot_date = :snapshot"), {"snapshot": snapshot}).scalar_one()
                        bad = abs(count - len(staged[source]))
                        qa.record("MYSQL_STAGING", "MySQL", spec["staging_table"], "Số dòng staging MySQL khớp file", count, bad, "Thái")
            finally:
                engine.dispose()
        except Exception as exc:
            qa.record("MYSQL_EXECUTION", "MySQL", "warehouse", "Đọc và kiểm tra trực tiếp dữ liệu đã load", "", None, "Minh", note=type(exc).__name__)
    else:
        qa.record("MYSQL_EXECUTION", "MySQL", "warehouse", "Đọc và kiểm tra trực tiếp dữ liệu đã load", "", None, "Minh",
                  "outputs/warehouse_load_summary.csv", "Báo cáo load có sẵn là bằng chứng lịch sử. Chạy --mysql để xác minh lại.")
    out = ROOT / "tests/data_quality_checks"
    history = paths["outputs_dir"] / "warehouse_load_summary.csv"
    if history.is_file():
        prior = read(history).set_index("table_name")
        for table, frame in gold.items():
            count = prior.at[table, "actual_in_mysql"] if table in prior.index else None
            bad = int(pd.isna(count) or int(count) != len(frame))
            qa.record("PRIOR_LOAD_COUNT", "Historical evidence", table, "Số dòng trong báo cáo load kèm ZIP khớp Gold tái tạo", count, bad, "Minh",
                      "outputs/warehouse_load_summary.csv", "Báo cáo kèm ZIP không có run_id/snapshot_date.", severity="REVIEW")
    pd.DataFrame(counts).to_csv(out / "row_count_reconciliation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(sample_rows).to_csv(out / "sample_validation.csv", index=False, encoding="utf-8-sig")
    results = pd.DataFrame(qa.results)
    results.to_csv(ROOT / "tests/qa_results.csv", index=False, encoding="utf-8-sig")
    results.loc[results.status.isin(["FAIL", "BLOCKED"])].to_csv(out / "issues.csv", index=False, encoding="utf-8-sig")
    print(results.status.value_counts().to_string())
    return 1 if results.status.eq("FAIL").any() else (2 if results.status.eq("BLOCKED").any() else 0)


if __name__ == "__main__":
    sys.exit(main())

