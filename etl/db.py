# etl/db.py
# Module quản lý kết nối và thao tác MySQL an toàn cho quy trình ETL
# Tuân thủ: Bảo mật credentials qua .env, Idempotency (xóa partition snapshot trước khi insert)

from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine

from scripts.verify_staging_schema import (
    execute_ddl, parse_expected_ddl, split_sql_statements, verify_schema,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_db_config() -> Dict[str, Any]:
    """Nạp cấu hình MySQL an toàn từ .env, không bao giờ in password."""
    load_dotenv(PROJECT_ROOT / ".env")
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", ""),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "airbnb_sg_2026"),
        "charset": "utf8mb4",
    }


def get_engine() -> Optional[Engine]:
    """Tạo SQLAlchemy engine nếu có đủ thông tin xác thực."""
    cfg = get_db_config()
    if not cfg["user"] and not cfg["password"]:
        logger.warning("MYSQL_USER hoặc MYSQL_PASSWORD chưa được cấu hình trong .env.")
        return None

    if not cfg["user"] or not cfg["password"]:
        raise ValueError("MYSQL_USER and MYSQL_PASSWORD must be configured together")

    url = URL.create(
        "mysql+pymysql",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["database"],
        query={"charset": cfg["charset"]},
    )
    return create_engine(url, pool_pre_ping=True, hide_parameters=True,
                         connect_args={"connect_timeout": 5})


def create_staging_tables_ddl(engine: Engine) -> None:
    """Apply and verify the Task 3.1 contract before replacing any snapshot."""
    ddl = (PROJECT_ROOT / "sql" / "01_staging_schema.sql").read_text(encoding="utf-8")
    expected = parse_expected_ddl(ddl)
    raw_connection = engine.raw_connection()
    try:
        connection = raw_connection.driver_connection
        execute_ddl(connection, split_sql_statements(ddl))
        verify_schema(connection, engine.url.database, expected)
    finally:
        raw_connection.close()
    with engine.begin() as conn:
        conn.execute(text(
        """
        CREATE TABLE IF NOT EXISTS etl_ingest_log (
            log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            source_name VARCHAR(50) NOT NULL,
            file_name VARCHAR(100) NOT NULL,
            snapshot_date DATE NOT NULL,
            rows_read INT UNSIGNED NOT NULL,
            rows_inserted INT UNSIGNED NOT NULL,
            rows_failed INT UNSIGNED NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL,
            execution_seconds DECIMAL(8,2) NOT NULL,
            started_at DATETIME NOT NULL,
            completed_at DATETIME NOT NULL,
            error_message TEXT NULL,
            INDEX idx_ingest_snapshot (snapshot_date, source_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """
        ))


@contextmanager
def replace_snapshot(engine: Engine, table_name: str, snapshot_date: str):
    """Serialize retries for the same table/snapshot and roll back on failure."""
    identity = f"{engine.url.database}:{table_name}:{snapshot_date}"
    lock_name = sha256(identity.encode()).hexdigest()
    with engine.connect() as conn:
        acquired = conn.execute(
            text("SELECT GET_LOCK(:name, 30)"), {"name": lock_name}
        ).scalar()
        try:
            if acquired != 1:
                raise RuntimeError(f"Could not lock staging snapshot: {identity}")
            conn.commit()
            with conn.begin():
                conn.execute(
                    text(f"DELETE FROM {table_name} WHERE snapshot_date = :snapshot"),
                    {"snapshot": snapshot_date},
                )
                yield conn
        finally:
            if acquired == 1:
                try:
                    conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": lock_name})
                except Exception:
                    conn.invalidate()
                    logger.warning("Could not release the staging lock on the existing connection")
