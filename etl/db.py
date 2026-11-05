# etl/db.py
# Module quản lý kết nối và thao tác MySQL an toàn cho quy trình ETL
# Tuân thủ: Bảo mật credentials qua .env, Idempotency (xóa partition snapshot trước khi insert)

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine

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
    if not cfg["user"] or not cfg["password"]:
        logger.warning("MYSQL_USER hoặc MYSQL_PASSWORD chưa được cấu hình trong .env.")
        return None

    try:
        url = URL.create(
            "mysql+pymysql",
            username=cfg["user"],
            password=cfg["password"],
            host=cfg["host"],
            port=cfg["port"],
            database=cfg["database"],
            query={"charset": cfg["charset"]},
        )
        engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
        return engine
    except Exception as exc:
        logger.error(f"Lỗi khi khởi tạo SQLAlchemy engine: {type(exc).__name__}")
        return None


def is_db_available() -> bool:
    """Kiểm tra kết nối thực tế tới MySQL."""
    engine = get_engine()
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return True
    except Exception as exc:
        logger.info(f"Không thể kết nối MySQL ({type(exc).__name__}). Chế độ offline/file-based sẽ được kích hoạt.")
        return False
    finally:
        engine.dispose()


def delete_snapshot_partition(table_name: str, snapshot_date: str) -> int:
    """Đảm bảo tính khả lặp (Idempotency - TQ-05): Xóa dữ liệu cũ của snapshot trước khi nạp lại."""
    engine = get_engine()
    if engine is None:
        return 0
    try:
        with engine.begin() as conn:
            # Kiểm tra bảng có tồn tại không
            table_check = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = :tname"
                ),
                {"tname": table_name},
            ).scalar()
            if table_check:
                result = conn.execute(
                    text(f"DELETE FROM {table_name} WHERE snapshot_date = :sdate"),
                    {"sdate": snapshot_date},
                )
                deleted_rows = result.rowcount
                logger.info(f"Idempotency: Đã xóa {deleted_rows} dòng cũ của snapshot {snapshot_date} tại {table_name}.")
                return deleted_rows
        return 0
    except Exception as exc:
        logger.warning(f"Lỗi khi xóa partition {table_name}: {exc}")
        return 0
    finally:
        engine.dispose()


def create_staging_tables_ddl() -> None:
    """Tạo bảng Staging và Log kiểm toán trong MySQL nếu chưa tồn tại."""
    engine = get_engine()
    if engine is None:
        return

    ddl_statements = [
        # 1. Bảng Ingest Log
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
        """,
        # 2. Bảng stg_neighbourhoods
        """
        CREATE TABLE IF NOT EXISTS stg_neighbourhoods (
            neighbourhood_group VARCHAR(100) NULL,
            neighbourhood VARCHAR(150) NULL,
            snapshot_date DATE NOT NULL,
            source_file VARCHAR(100) NOT NULL,
            ingested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_stg_nb_group (neighbourhood_group),
            INDEX idx_stg_nb_snap (snapshot_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """,
        # 3. Bảng stg_calendar
        """
        CREATE TABLE IF NOT EXISTS stg_calendar (
            listing_id BIGINT UNSIGNED NULL,
            date VARCHAR(20) NULL,
            available VARCHAR(10) NULL,
            minimum_nights VARCHAR(20) NULL,
            maximum_nights VARCHAR(20) NULL,
            snapshot_date DATE NOT NULL,
            source_file VARCHAR(100) NOT NULL,
            ingested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_stg_cal_listing (listing_id),
            INDEX idx_stg_cal_date (date),
            INDEX idx_stg_cal_snap (snapshot_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """,
        # 4. Bảng stg_reviews
        """
        CREATE TABLE IF NOT EXISTS stg_reviews (
            listing_id BIGINT UNSIGNED NULL,
            id BIGINT UNSIGNED NULL,
            date VARCHAR(20) NULL,
            reviewer_id BIGINT UNSIGNED NULL,
            reviewer_name VARCHAR(255) NULL,
            comments MEDIUMTEXT NULL,
            snapshot_date DATE NOT NULL,
            source_file VARCHAR(100) NOT NULL,
            ingested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_stg_rev_listing (listing_id),
            INDEX idx_stg_rev_id (id),
            INDEX idx_stg_rev_snap (snapshot_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """,
        # 5. Bảng stg_listings (Lưu cấu trúc thô của 90 cột)
        """
        CREATE TABLE IF NOT EXISTS stg_listings (
            id BIGINT UNSIGNED NULL,
            listing_url TEXT NULL,
            scrape_id BIGINT UNSIGNED NULL,
            last_scraped VARCHAR(30) NULL,
            source VARCHAR(100) NULL,
            name VARCHAR(500) NULL,
            description LONGTEXT NULL,
            neighborhood_overview LONGTEXT NULL,
            picture_url TEXT NULL,
            host_id BIGINT UNSIGNED NULL,
            host_url TEXT NULL,
            host_profile_id BIGINT UNSIGNED NULL,
            host_profile_url TEXT NULL,
            host_name VARCHAR(255) NULL,
            host_since VARCHAR(30) NULL,
            hosts_time_as_user_years INT NULL,
            hosts_time_as_user_months INT NULL,
            hosts_time_as_host_years INT NULL,
            hosts_time_as_host_months INT NULL,
            host_location VARCHAR(255) NULL,
            host_about LONGTEXT NULL,
            host_response_time VARCHAR(100) NULL,
            host_response_rate VARCHAR(50) NULL,
            host_acceptance_rate VARCHAR(50) NULL,
            host_is_superhost VARCHAR(10) NULL,
            host_thumbnail_url TEXT NULL,
            host_picture_url TEXT NULL,
            host_neighbourhood VARCHAR(255) NULL,
            host_listings_count INT NULL,
            host_total_listings_count INT NULL,
            host_verifications TEXT NULL,
            host_has_profile_pic VARCHAR(10) NULL,
            host_identity_verified VARCHAR(10) NULL,
            neighbourhood VARCHAR(255) NULL,
            neighbourhood_cleansed VARCHAR(150) NULL,
            neighbourhood_group_cleansed VARCHAR(100) NULL,
            latitude DECIMAL(10,7) NULL,
            longitude DECIMAL(10,7) NULL,
            property_type VARCHAR(150) NULL,
            room_type VARCHAR(100) NULL,
            accommodates INT NULL,
            bathrooms VARCHAR(50) NULL,
            bathrooms_text VARCHAR(100) NULL,
            bedrooms DECIMAL(6,2) NULL,
            beds DECIMAL(6,2) NULL,
            amenities LONGTEXT NULL,
            price VARCHAR(100) NULL,
            price_quote_checkin_date VARCHAR(30) NULL,
            price_quote_checkout_date VARCHAR(30) NULL,
            price_quote_total_price DECIMAL(14,2) NULL,
            price_quote_price_per_night DECIMAL(12,2) NULL,
            price_quote_raw LONGTEXT NULL,
            minimum_nights INT NULL,
            maximum_nights INT NULL,
            minimum_minimum_nights INT NULL,
            maximum_minimum_nights INT NULL,
            minimum_maximum_nights INT NULL,
            maximum_maximum_nights INT NULL,
            minimum_nights_avg_ntm DECIMAL(10,2) NULL,
            maximum_nights_avg_ntm DECIMAL(10,2) NULL,
            calendar_updated VARCHAR(100) NULL,
            has_availability VARCHAR(10) NULL,
            availability_30 INT NULL,
            availability_60 INT NULL,
            availability_90 INT NULL,
            availability_365 INT NULL,
            calendar_last_scraped VARCHAR(30) NULL,
            number_of_reviews INT NULL,
            number_of_reviews_ltm INT NULL,
            number_of_reviews_l30d INT NULL,
            availability_eoy INT NULL,
            number_of_reviews_ly INT NULL,
            estimated_occupancy_l365d INT NULL,
            estimated_revenue_l365d DECIMAL(14,2) NULL,
            first_review VARCHAR(30) NULL,
            last_review VARCHAR(30) NULL,
            review_scores_rating DECIMAL(4,2) NULL,
            review_scores_accuracy DECIMAL(4,2) NULL,
            review_scores_cleanliness DECIMAL(4,2) NULL,
            review_scores_checkin DECIMAL(4,2) NULL,
            review_scores_communication DECIMAL(4,2) NULL,
            review_scores_location DECIMAL(4,2) NULL,
            review_scores_value DECIMAL(4,2) NULL,
            license VARCHAR(255) NULL,
            instant_bookable VARCHAR(10) NULL,
            calculated_host_listings_count INT NULL,
            calculated_host_listings_count_entire_homes INT NULL,
            calculated_host_listings_count_private_rooms INT NULL,
            calculated_host_listings_count_shared_rooms INT NULL,
            reviews_per_month DECIMAL(8,2) NULL,
            snapshot_date DATE NOT NULL,
            source_file VARCHAR(100) NOT NULL,
            ingested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_stg_list_id (id),
            INDEX idx_stg_list_snap (snapshot_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """,
    ]

    try:
        with engine.begin() as conn:
            for sql in ddl_statements:
                conn.execute(text(sql))
        logger.info("Tạo/kiểm tra các bảng Staging thành công.")
    except Exception as exc:
        logger.error(f"Lỗi khi tạo staging tables: {exc}")
    finally:
        engine.dispose()
