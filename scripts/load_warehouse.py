"""Nạp Gold CSV của task 3.4 vào MySQL và đối chiếu trước khi commit."""

from __future__ import annotations

import argparse
import datetime
from hashlib import sha256
from itertools import islice
import logging
import os
from pathlib import Path
import time

import pandas as pd
import pymysql
from dotenv import load_dotenv

if __package__:
    from .verify_warehouse_schema import parse_expected, split_sql, verify_schema
    from .warehouse_validation import compare_metrics, raw_metrics
else:
    from verify_warehouse_schema import parse_expected, split_sql, verify_schema
    from warehouse_validation import compare_metrics, raw_metrics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "2026-09-23"
logger = logging.getLogger("load_warehouse")

GRAINS = {
    "dim_date": ("full_date",),
    "dim_neighbourhood": ("neighbourhood_group", "neighbourhood_name"),
    "dim_listing": ("listing_id", "snapshot_date"),
    "fact_listing_snapshot": ("listing_id", "snapshot_date"),
    "fact_calendar": ("listing_id", "calendar_date", "snapshot_date"),
    "fact_review": ("listing_id", "review_id", "snapshot_date"),
}

def get_connection(autocommit: bool = False) -> pymysql.Connection:
    """Tạo kết nối PyMySQL trực tiếp với cấu hình từ .env."""
    load_dotenv(PROJECT_ROOT / ".env")
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "airbnb_sg_2026")

    if not user or not password:
        raise ValueError("MYSQL_USER và MYSQL_PASSWORD phải được cấu hình trong .env")

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        autocommit=autocommit,
        connect_timeout=10,
    )


def log_load_step(
    conn: pymysql.Connection,
    step_order: int,
    table_name: str,
    table_type: str,
    snapshot_date: str,
    rows_source: int,
    rows_loaded: int,
    rows_failed: int,
    duration: float,
    status: str,
    started_at: datetime.datetime,
    completed_at: datetime.datetime,
    notes: str = "",
) -> None:
    """Ghi bản ghi kiểm toán vào bảng etl_load_log."""
    sql = """
    INSERT INTO etl_load_log (
        step_order, table_name, table_type, snapshot_date,
        rows_source, rows_loaded, rows_failed, duration_seconds,
        status, started_at, completed_at, notes
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                step_order,
                table_name,
                table_type,
                snapshot_date,
                rows_source,
                rows_loaded,
                rows_failed,
                round(duration, 2),
                status,
                started_at.strftime("%Y-%m-%d %H:%M:%S"),
                completed_at.strftime("%Y-%m-%d %H:%M:%S"),
                notes,
            ),
        )


def read_gold(gold_dir: Path, snapshot_date: str, schema: dict, expected: pd.DataFrame) -> dict:
    """Validate the whole delivery before opening a write connection."""
    if snapshot_date != SNAPSHOT:
        raise ValueError(f"Task 3.6 supports snapshot {SNAPSHOT}; got {snapshot_date}.")
    frames = {}
    counts = expected.set_index(["metric", "group_value"])["value"]
    expected_counts = {
        "dim_date": 6209,
        "dim_listing": counts["LISTING_ROWS", "ALL"],
        "fact_listing_snapshot": counts["LISTING_ROWS", "ALL"],
        "fact_calendar": counts["CALENDAR_ROWS", "ALL"],
        "fact_review": counts["REVIEW_ROWS", "ALL"],
    }
    for table, grain in GRAINS.items():
        frame = pd.read_csv(gold_dir / f"{table}.csv", dtype=str, keep_default_na=False)
        columns = [c for c in schema[table]["columns"] if c["name"] != "created_at"]
        names = {c["name"] for c in columns}
        if set(frame.columns) != names:
            raise ValueError(f"{table}: invalid CSV columns: {sorted(set(frame.columns) ^ names)}")
        if frame.empty or (table in expected_counts and len(frame) != expected_counts[table]):
            raise ValueError(f"{table}: unexpected row count {len(frame)}.")
        if "snapshot_date" in frame and not frame["snapshot_date"].eq(snapshot_date).all():
            raise ValueError(f"{table}: CSV snapshot does not match {snapshot_date}.")
        for col in columns:
            if col["nullable"] == "NO" and frame[col["name"]].eq("").any():
                raise ValueError(f"{table}: empty required column {col['name']}.")
        if frame.duplicated(list(grain)).any():
            raise ValueError(f"{table}: duplicate business grain.")
        for date, key in (("full_date", "date_sk"), ("snapshot_date", "snapshot_date_sk"),
                          ("calendar_date", "calendar_date_sk"), ("review_date", "review_date_sk")):
            if key in frame and not frame[date].str.replace("-", "", regex=False).eq(frame[key]).all():
                raise ValueError(f"{table}: {date} differs from {key}.")
        frames[table] = frame

    areas = frames["dim_neighbourhood"]
    if areas["neighbourhood_sk"].ne("0").sum() != 55:
        raise ValueError("dim_neighbourhood: expected all 55 source neighbourhoods.")
    listings = frames["dim_listing"]
    if areas["neighbourhood_sk"].duplicated().any() or listings["listing_sk"].duplicated().any():
        raise ValueError("Duplicate CSV dimension key.")
    if not listings["neighbourhood_sk"].isin(areas["neighbourhood_sk"]).all():
        raise ValueError("dim_listing: unknown CSV neighbourhood key.")
    parent = listings.set_index("listing_id")
    for table in ("fact_listing_snapshot", "fact_calendar", "fact_review"):
        frame = frames[table]
        for col in ("listing_sk", "neighbourhood_sk"):
            if not frame["listing_id"].map(parent[col]).eq(frame[col]).all():
                raise ValueError(f"{table}: {col} differs from the CSV parent listing.")
    return frames


def upsert(cursor, table: str, frame: pd.DataFrame, batch_size: int) -> None:
    cols = list(frame.columns)
    names = ", ".join(f"`{col}`" for col in cols)
    markers = ", ".join(["%s"] * len(cols))
    protected = set(GRAINS[table]) | {"date_sk"}
    updates = ", ".join(f"`{col}`=VALUES(`{col}`)" for col in cols if col not in protected)
    sql = f"INSERT INTO `{table}` ({names}) VALUES ({markers}) ON DUPLICATE KEY UPDATE {updates}"
    values = (tuple(None if value == "" else value for value in row)
              for row in frame.itertuples(index=False, name=None))
    while batch := list(islice(values, batch_size)):
        cursor.executemany(sql, batch)


FACT_PRIMARY_KEYS = {
    "fact_listing_snapshot": "listing_snapshot_sk",
    "fact_calendar": "calendar_sk",
    "fact_review": "review_sk",
}


def load_tables(cursor, frames: dict, snapshot_date: str, batch_size: int) -> list:
    summaries = []
    area_keys = {}
    listing_keys = {}
    listing_areas = {}
    for table, source in frames.items():
        started = datetime.datetime.now()
        start = time.monotonic()
        frame = source
        if table == "dim_neighbourhood":
            cursor.execute("SELECT neighbourhood_group, neighbourhood_name FROM dim_neighbourhood")
            existing = {name: group for group, name in cursor.fetchall()}
            if any(name in existing and existing[name] != group
                   for group, name in zip(source["neighbourhood_group"], source["neighbourhood_name"])):
                raise ValueError("Existing neighbourhood name maps to a different group.")
            frame = source.drop(columns="neighbourhood_sk")
        elif table == "dim_listing":
            frame = source.drop(columns="listing_sk").assign(
                neighbourhood_sk=source["neighbourhood_sk"].map(area_keys))
        elif table.startswith("fact_"):
            frame = source.drop(columns=FACT_PRIMARY_KEYS[table]).assign(
                listing_sk=source["listing_id"].map(listing_keys),
                neighbourhood_sk=source["listing_id"].map(listing_areas),
            )
        if table in FACT_PRIMARY_KEYS and frame[["listing_sk", "neighbourhood_sk"]].isna().any().any():
            raise ValueError(f"{table}: listing or neighbourhood was not resolved in MySQL.")
        upsert(cursor, table, frame, batch_size)
        if table == "dim_date":
            cursor.execute("SELECT date_sk, full_date FROM dim_date")
            dates = {str(key): str(day) for key, day in cursor.fetchall()}
            actual = sum(dates.get(key) == day for key, day in zip(source["date_sk"], source["full_date"]))
        elif table == "dim_neighbourhood":
            cursor.execute("SELECT neighbourhood_group, neighbourhood_name, neighbourhood_sk FROM dim_neighbourhood")
            db_keys = {(group, name): sk for group, name, sk in cursor.fetchall()}
            area_keys = {local: db_keys[group, name] for local, group, name in zip(
                source["neighbourhood_sk"], source["neighbourhood_group"], source["neighbourhood_name"])}
            actual = len(area_keys)
        else:
            if table == "dim_listing":
                cursor.execute(
                    "SELECT listing_id, listing_sk, neighbourhood_sk FROM dim_listing WHERE snapshot_date=%s",
                    (snapshot_date,),
                )
                for listing_id, sk, area in cursor.fetchall():
                    listing_keys[str(listing_id)] = sk
                    listing_areas[str(listing_id)] = area
            cursor.execute(f"SELECT COUNT(*) FROM `{table}` WHERE snapshot_date=%s", (snapshot_date,))
            actual = cursor.fetchone()[0]
        if actual != len(source):
            raise ValueError(f"{table}: CSV has {len(source)} rows, matched MySQL rows {actual}.")
        logger.info("%s: %s matched rows", table, actual)
        summaries.append((table, actual, time.monotonic() - start, started))
    return summaries


def verify_metrics(cursor, expected: pd.DataFrame, context: dict) -> pd.DataFrame:
    sql = PROJECT_ROOT / "sql" / "03_validate_gold_against_raw.sql"
    statements = split_sql(sql.read_text(encoding="utf-8"))
    for name, value in context.items():
        variable = "snapshot" if name == "snapshot_date" else name
        cursor.execute(f"SET @{variable} = %s", (value,))
    cursor.execute(statements[-1])
    observed = pd.DataFrame(cursor.fetchall(), columns=["snapshot_date", "metric", "group_value", "value"])
    observed["snapshot_date"] = observed["snapshot_date"].astype(str)
    result = compare_metrics(expected, observed)
    failures = result[result["status"].ne("PASS")]
    if not failures.empty:
        raise ValueError("Raw/MySQL reconciliation failed:\n" + failures.to_string(index=False))
    return result


def run_warehouse_loading(
    gold_dir: Path, snapshot_date: str = SNAPSHOT, batch_size: int = 5000,
    *, check_rerun: bool = False,
) -> dict:
    if batch_size <= 0:
        raise ValueError("Batch size must be positive.")
    if snapshot_date != SNAPSHOT:
        raise ValueError(f"Task 3.6 supports snapshot {SNAPSHOT}.")
    sql_dir = PROJECT_ROOT / "sql"
    schema = parse_expected((sql_dir / "02_warehouse_schema.sql").read_text(encoding="utf-8"))
    expected, context = raw_metrics(PROJECT_ROOT / "data/raw", PROJECT_ROOT / "docs/source_inventory.csv")
    if context["snapshot_date"] != snapshot_date:
        raise ValueError("Raw inventory snapshot differs from the requested snapshot.")
    frames = read_gold(gold_dir, snapshot_date, schema, expected)
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE(), @@SESSION.foreign_key_checks, @@SESSION.sql_mode")
            database, fk_checks, sql_mode = cursor.fetchone()
            if fk_checks != 1 or not {"STRICT_TRANS_TABLES", "STRICT_ALL_TABLES"}.intersection(sql_mode.split(",")):
                raise ValueError("Gold load requires enabled foreign keys and strict SQL mode.")
            lock_name = sha256(f"{database}:warehouse".encode()).hexdigest()
            cursor.execute("SELECT GET_LOCK(%s, 30)", (lock_name,))
            if cursor.fetchone()[0] != 1:
                raise RuntimeError("Could not acquire warehouse load lock.")
            verify_schema(conn, database, schema)
            cursor.execute(split_sql((sql_dir / "03_load_warehouse.sql").read_text(encoding="utf-8"))[0])
            cursor.execute(
                "SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME='etl_load_log'",
                (database,),
            )
            if cursor.fetchone()[0] != "InnoDB":
                raise RuntimeError("etl_load_log must use InnoDB.")
            conn.begin()
            summary = load_tables(cursor, frames, snapshot_date, batch_size)
            metrics = verify_metrics(cursor, expected, context)
            if check_rerun:
                load_tables(cursor, frames, snapshot_date, batch_size)
                verify_metrics(cursor, expected, context)
                logger.info("Replaying the same CSVs preserved row counts and reconciliation metrics.")
            rows = []
            for order, (table, count, duration, started) in enumerate(summary, 1):
                kind = "FACT" if table.startswith("fact_") else "DIMENSION"
                log_load_step(conn, order, table, kind, snapshot_date, len(frames[table]),
                              count, 0, duration, "SUCCESS", started, datetime.datetime.now())
                rows.append(dict(step_order=order, table_name=table, table_type=kind, source_file=f"{table}.csv",
                                 rows_source=len(frames[table]), rows_loaded=count, actual_in_mysql=count,
                                 duration_seconds=round(duration, 2), status="PASS"))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        # Closing the session releases the named lock after commit or rollback.
        conn.close()

    outputs = PROJECT_ROOT / "outputs"
    outputs.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(outputs / "warehouse_load_summary.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(outputs / "warehouse_raw_vs_gold.csv", index=False, encoding="utf-8-sig")
    logger.info("Committed %d tables; %d Raw/MySQL checks passed.", len(rows), len(metrics))
    return {"status": "SUCCESS", "summary": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-dir", type=Path, default=PROJECT_ROOT / "data/processed/gold")
    parser.add_argument("--snapshot-date", default=SNAPSHOT, choices=[SNAPSHOT])
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--skip-idempotency-test", action="store_true")
    args = parser.parse_args()
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(
                            log_dir / "load_warehouse.log", encoding="utf-8")])
    try:
        run_warehouse_loading(args.gold_dir, args.snapshot_date, args.batch_size,
                              check_rerun=not args.skip_idempotency_test)
    except Exception as exc:
        logger.error("Warehouse load failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
