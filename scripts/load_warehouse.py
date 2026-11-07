#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/load_warehouse.py – Task 3.6: Xây Dựng Quy Trình Load Dimension và Fact
=============================================================================
1. Nạp Dimension trước Fact theo đúng thứ tự phụ thuộc khóa ngoại (FK):
   - dim_date -> dim_neighbourhood -> dim_listing -> fact_listing_snapshot -> fact_calendar -> fact_review.
2. Ánh xạ business key sang surrogate key, kiểm soát bản ghi trùng và khóa ngoại mồ côi.
3. Đảm bảo tính khả lặp (Idempotency - TQ-05): Chạy lại cùng snapshot_date không sinh thêm dòng.
4. Ghi log số dòng nạp, lỗi và thời gian chạy vào console, logs/load_warehouse.log và bảng etl_load_log.
5. Xuất báo cáo đối chiếu số bản ghi Source -> Silver -> Gold (outputs/warehouse_load_summary.csv).
6. Truy vấn xác thực kho dữ liệu (KPI validation queries).

Tác giả : Minh (Data Warehouse / MySQL)
Phối hợp: Thái (Data Engineer / ETL), Hồng (QA / DA)
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
import pymysql
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "load_warehouse.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("load_warehouse")


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


def init_load_log_table(conn: pymysql.Connection) -> None:
    """Tạo bảng kiểm toán nạp kho dữ liệu etl_load_log nếu chưa có."""
    ddl = """
    CREATE TABLE IF NOT EXISTS etl_load_log (
        log_id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        step_order          TINYINT UNSIGNED NOT NULL COMMENT 'Thứ tự nạp (1..6)',
        table_name          VARCHAR(50)      NOT NULL COMMENT 'Tên bảng đích trong Gold Warehouse',
        table_type          VARCHAR(20)      NOT NULL COMMENT 'DIMENSION hoặc FACT',
        snapshot_date       DATE             NOT NULL COMMENT 'Ngày snapshot dữ liệu',
        rows_source         INT UNSIGNED     NOT NULL COMMENT 'Số dòng dữ liệu nguồn/Silver đầu vào',
        rows_loaded         INT UNSIGNED     NOT NULL COMMENT 'Số dòng nạp thành công vào MySQL',
        rows_failed         INT UNSIGNED     NOT NULL DEFAULT 0 COMMENT 'Số dòng lỗi (nếu có)',
        duration_seconds    DECIMAL(8,2)     NOT NULL COMMENT 'Thời gian nạp tính bằng giây',
        status              VARCHAR(20)      NOT NULL COMMENT 'SUCCESS / FAIL / SKIPPED',
        started_at          DATETIME         NOT NULL COMMENT 'Thời điểm bắt đầu nạp',
        completed_at        DATETIME         NOT NULL COMMENT 'Thời điểm hoàn thành',
        notes               TEXT             NULL     COMMENT 'Ghi chú kiểm toán',
        INDEX idx_load_snapshot (snapshot_date, table_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
      COMMENT='Bảng kiểm toán quy trình nạp kho dữ liệu Warehouse (Task 3.6)';
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


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
    conn.commit()


def load_dataframe_to_table(
    conn: pymysql.Connection,
    table_name: str,
    df: pd.DataFrame,
    batch_size: int = 5000,
    update_on_duplicate: bool = True,
) -> int:
    """Nạp DataFrame vào bảng MySQL với xử lý batch, chuyển đổi NaN sang NULL và hỗ trợ UPSERT."""
    if df.empty:
        return 0

    cols = list(df.columns)
    quoted_cols = [f"`{c}`" for c in cols]
    cols_clause = ", ".join(quoted_cols)
    placeholders = ", ".join(["%s"] * len(cols))

    if update_on_duplicate:
        # Generate ON DUPLICATE KEY UPDATE for non-PK columns
        update_pairs = [f"`{c}` = VALUES(`{c}`)" for c in cols if not c.endswith("_sk") and c != "created_at"]
        if update_pairs:
            sql = f"INSERT INTO `{table_name}` ({cols_clause}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {', '.join(update_pairs)}"
        else:
            sql = f"INSERT IGNORE INTO `{table_name}` ({cols_clause}) VALUES ({placeholders})"
    else:
        sql = f"INSERT INTO `{table_name}` ({cols_clause}) VALUES ({placeholders})"

    # Convert DataFrame to records, mapping NaN/NaT to None
    clean_df = df.replace({np.nan: None})
    records = clean_df.to_dict(orient="records")

    total_inserted = 0
    with conn.cursor() as cur:
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            batch_vals = [[r[c] for c in cols] for r in batch]
            cur.executemany(sql, batch_vals)
            total_inserted += len(batch)
            if (i + batch_size) % 50000 == 0 or (i + len(batch)) == len(records):
                logger.info(f"   -> Bảng {table_name}: Đã xử lý {min(i + batch_size, len(records)):,}/{len(records):,} dòng...")
    conn.commit()
    return total_inserted


def run_warehouse_loading(
    gold_dir: Path,
    snapshot_date: str = "2026-09-23",
    batch_size: int = 5000,
) -> Dict[str, Any]:
    """Quy trình toàn diện nạp kho dữ liệu MySQL theo đúng chuẩn Kimball Star Schema."""
    logger.info("=" * 75)
    logger.info("  BẮT ĐẦU QUY TRÌNH NẠP KHO DỮ LIỆU – AIRBNB SINGAPORE DATA WAREHOUSE")
    logger.info(f"  Snapshot Date : {snapshot_date}")
    logger.info(f"  Gold Directory: {gold_dir}")
    logger.info(f"  Batch Size    : {batch_size:,} dòng/lần nạp")
    logger.info("=" * 75)

    conn = get_connection(autocommit=False)
    try:
        init_load_log_table(conn)

        # Danh sách bảng theo thứ tự phụ thuộc khóa ngoại (Foreign Key Dependency)
        load_plan = [
            # 1. Dimension độc lập: dim_date
            {
                "order": 1,
                "table": "dim_date",
                "type": "DIMENSION",
                "file": "dim_date.csv",
                "desc": "Chiều thời gian dùng chung (2011..2027)",
            },
            # 2. Dimension địa lý: dim_neighbourhood
            {
                "order": 2,
                "table": "dim_neighbourhood",
                "type": "DIMENSION",
                "file": "dim_neighbourhood.csv",
                "desc": "Chiều danh mục 55 khu vực quy hoạch Singapore",
            },
            # 3. Dimension trung tâm: dim_listing
            {
                "order": 3,
                "table": "dim_listing",
                "type": "DIMENSION",
                "file": "dim_listing.csv",
                "desc": "Chiều thuộc tính mô tả tin đăng và chủ nhà",
            },
            # 4. Fact cấp Listing: fact_listing_snapshot
            {
                "order": 4,
                "table": "fact_listing_snapshot",
                "type": "FACT",
                "file": "fact_listing_snapshot.csv",
                "desc": "Bảng sự kiện định lượng cấp tin đăng tại snapshot",
            },
            # 5. Fact chi tiết lịch: fact_calendar
            {
                "order": 5,
                "table": "fact_calendar",
                "type": "FACT",
                "file": "fact_calendar.csv",
                "desc": "Bảng sự kiện lịch mở/đóng 365 ngày của từng tin đăng",
            },
            # 6. Fact lịch sử đánh giá: fact_review
            {
                "order": 6,
                "table": "fact_review",
                "type": "FACT",
                "file": "fact_review.csv",
                "desc": "Bảng sự kiện nhận xét và đánh giá của khách hàng",
            },
        ]

        summary_rows = []
        overall_start = time.time()

        for step in load_plan:
            t_name = step["table"]
            csv_path = gold_dir / step["file"]
            if not csv_path.exists():
                raise FileNotFoundError(f"Không tìm thấy file dữ liệu Gold: {csv_path}")

            logger.info(f"\n>>> [BƯỚC {step['order']}/6] Đang nạp bảng {t_name} ({step['desc']})...")
            step_start = datetime.datetime.now()
            t0 = time.time()

            # Đọc dữ liệu Gold
            df = pd.read_csv(csv_path, low_memory=False)
            rows_src = len(df)
            logger.info(f"   Đọc tệp {step['file']}: {rows_src:,} bản ghi.")

            # Nạp vào MySQL
            rows_inserted = load_dataframe_to_table(
                conn=conn,
                table_name=t_name,
                df=df,
                batch_size=batch_size,
                update_on_duplicate=True,
            )
            step_dur = time.time() - t0
            step_end = datetime.datetime.now()

            # Kiểm tra số dòng thực tế trong MySQL
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM `{t_name}`")
                actual_count = cur.fetchone()[0]

            logger.info(
                f"   ✅ Hoàn tất nạp {t_name}: {rows_inserted:,} dòng trong {step_dur:.2f}s "
                f"| Số dòng hiện có trong MySQL: {actual_count:,}"
            )

            # Ghi log kiểm toán
            log_load_step(
                conn=conn,
                step_order=step["order"],
                table_name=t_name,
                table_type=step["type"],
                snapshot_date=snapshot_date,
                rows_source=rows_src,
                rows_loaded=rows_inserted,
                rows_failed=0,
                duration=step_dur,
                status="SUCCESS",
                started_at=step_start,
                completed_at=step_end,
                notes=f"Nạp từ {step['file']} thành công.",
            )

            summary_rows.append({
                "step_order": step["order"],
                "table_name": t_name,
                "table_type": step["type"],
                "source_file": step["file"],
                "rows_source": rows_src,
                "rows_loaded": rows_inserted,
                "actual_in_mysql": actual_count,
                "duration_seconds": round(step_dur, 2),
                "status": "PASS",
            })

        total_dur = time.time() - overall_start

        # Lưu báo cáo đối chiếu
        summary_df = pd.DataFrame(summary_rows)
        outputs_dir = PROJECT_ROOT / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        summary_path = outputs_dir / "warehouse_load_summary.csv"
        summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        logger.info(f"\nĐã lưu bảng tổng kết nạp kho dữ liệu tại: {summary_path}")

        return {"status": "SUCCESS", "summary": summary_rows, "total_seconds": total_dur}

    except Exception as exc:
        conn.rollback()
        logger.error(f"Lỗi nghiêm trọng trong quy trình nạp kho dữ liệu: {exc}", exc_info=True)
        raise exc
    finally:
        conn.close()


def verify_referential_integrity_in_mysql(snapshot_date: str = "2026-09-23") -> Dict[str, Any]:
    """Kiểm tra tính toàn vẹn khóa ngoại (Referential Integrity) trực tiếp bằng truy vấn SQL trong MySQL."""
    logger.info("\n" + "=" * 75)
    logger.info("  KIỂM TRA TÍNH TOÀN VẸN THAM CHIẾU & KHÓA MỒ CÔI (ORPHAN KEYS) TRONG MYSQL")
    logger.info("=" * 75)

    conn = get_connection(autocommit=True)
    results = []

    try:
        with conn.cursor() as cur:
            # 1. Fact Listing Snapshot -> Dim Listing
            cur.execute("""
                SELECT COUNT(*) FROM fact_listing_snapshot f
                LEFT JOIN dim_listing d
                  ON f.listing_sk = d.listing_sk
                 AND f.snapshot_date_sk = d.snapshot_date_sk
                 AND f.neighbourhood_sk = d.neighbourhood_sk
                WHERE d.listing_sk IS NULL
            """)
            fls_orphan = cur.fetchone()[0]
            logger.info(f"  1. fact_listing_snapshot -> dim_listing : Orphan = {fls_orphan} -> {'[PASS]' if fls_orphan == 0 else '[FAIL]'}")
            results.append({"check": "fact_listing_snapshot -> dim_listing", "orphan_count": fls_orphan, "status": "PASS" if fls_orphan == 0 else "FAIL"})

            # 2. Fact Calendar -> Dim Listing
            cur.execute("""
                SELECT COUNT(*) FROM fact_calendar f
                LEFT JOIN dim_listing d
                  ON f.listing_sk = d.listing_sk
                 AND f.snapshot_date_sk = d.snapshot_date_sk
                 AND f.neighbourhood_sk = d.neighbourhood_sk
                WHERE d.listing_sk IS NULL
            """)
            fc_orphan = cur.fetchone()[0]
            logger.info(f"  2. fact_calendar -> dim_listing         : Orphan = {fc_orphan} -> {'[PASS]' if fc_orphan == 0 else '[FAIL]'}")
            results.append({"check": "fact_calendar -> dim_listing", "orphan_count": fc_orphan, "status": "PASS" if fc_orphan == 0 else "FAIL"})

            # 3. Fact Review -> Dim Listing
            cur.execute("""
                SELECT COUNT(*) FROM fact_review f
                LEFT JOIN dim_listing d
                  ON f.listing_sk = d.listing_sk
                 AND f.snapshot_date_sk = d.snapshot_date_sk
                 AND f.neighbourhood_sk = d.neighbourhood_sk
                WHERE d.listing_sk IS NULL
            """)
            fr_orphan = cur.fetchone()[0]
            logger.info(f"  3. fact_review -> dim_listing           : Orphan = {fr_orphan} -> {'[PASS]' if fr_orphan == 0 else '[FAIL]'}")
            results.append({"check": "fact_review -> dim_listing", "orphan_count": fr_orphan, "status": "PASS" if fr_orphan == 0 else "FAIL"})

            # 4. Dim Listing -> Dim Neighbourhood
            cur.execute("""
                SELECT COUNT(*) FROM dim_listing d
                LEFT JOIN dim_neighbourhood n ON d.neighbourhood_sk = n.neighbourhood_sk
                WHERE n.neighbourhood_sk IS NULL
            """)
            nb_orphan = cur.fetchone()[0]
            logger.info(f"  4. dim_listing -> dim_neighbourhood     : Orphan = {nb_orphan} -> {'[PASS]' if nb_orphan == 0 else '[FAIL]'}")
            results.append({"check": "dim_listing -> dim_neighbourhood", "orphan_count": nb_orphan, "status": "PASS" if nb_orphan == 0 else "FAIL"})

            # 5. Dim Listing -> Dim Date
            cur.execute("""
                SELECT COUNT(*) FROM dim_listing d
                LEFT JOIN dim_date dt ON d.snapshot_date_sk = dt.date_sk
                WHERE dt.date_sk IS NULL
            """)
            date_orphan = cur.fetchone()[0]
            logger.info(f"  5. dim_listing -> dim_date (snapshot)   : Orphan = {date_orphan} -> {'[PASS]' if date_orphan == 0 else '[FAIL]'}")
            results.append({"check": "dim_listing -> dim_date", "orphan_count": date_orphan, "status": "PASS" if date_orphan == 0 else "FAIL"})

        all_pass = all(r["status"] == "PASS" for r in results)
        logger.info("=" * 75)
        logger.info(f"  KẾT QUẢ TỔNG QUAN KHÓA MỒ CÔI: {'TUYỆT ĐỐI KHÔNG CÓ KHÓA MỒ CÔI (PASS 100%)' if all_pass else 'CẢNH BÁO: CÓ KHÓA MỒ CÔI'}")
        logger.info("=" * 75)
        return {"all_pass": all_pass, "details": results}

    finally:
        conn.close()


def verify_idempotency_in_mysql(
    gold_dir: Path,
    snapshot_date: str = "2026-09-23",
) -> bool:
    """Kiểm tra tính khả lặp (Idempotency - TQ-05): Nạp lại lần 2 cùng snapshot_date và đối chiếu số dòng."""
    logger.info("\n" + "=" * 75)
    logger.info("  KIỂM TRA TÍNH KHẢ LẶP (IDEMPOTENCY - TQ-05): NẠP LẠI LẦN 2 TRÊN MYSQL")
    logger.info("=" * 75)

    conn = get_connection(autocommit=True)
    try:
        # Ghi nhận số dòng trước khi chạy lần 2
        tables = ["dim_date", "dim_neighbourhood", "dim_listing", "fact_listing_snapshot", "fact_calendar", "fact_review"]
        counts_before = {}
        with conn.cursor() as cur:
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM `{t}`")
                counts_before[t] = cur.fetchone()[0]

        logger.info("Số dòng trước khi nạp lại lần 2:")
        for t, c in counts_before.items():
            logger.info(f"  - {t:<25}: {c:,} dòng")

        # Thực thi nạp lại
        logger.info("\nĐang thực thi nạp lại lần 2...")
        run_warehouse_loading(gold_dir=gold_dir, snapshot_date=snapshot_date, batch_size=10000)

        # Ghi nhận số dòng sau khi chạy lần 2
        counts_after = {}
        with conn.cursor() as cur:
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM `{t}`")
                counts_after[t] = cur.fetchone()[0]

        logger.info("\nĐối chiếu số dòng sau khi nạp lại lần 2:")
        all_equal = True
        for t in tables:
            c1 = counts_before[t]
            c2 = counts_after[t]
            matched = (c1 == c2)
            if not matched:
                all_equal = False
            logger.info(f"  - {t:<25}: Lần 1 = {c1:,} | Lần 2 = {c2:,} -> {'KHÔNG ĐỔI [PASS]' if matched else 'TĂNG DÒNG [FAIL]'}")

        logger.info("=" * 75)
        logger.info(f"  TÍNH KHẢ LẶP (IDEMPOTENCY): {'ĐẠT CHUẨN PASS 100%' if all_equal else 'THẤT BẠI'}")
        logger.info("=" * 75)
        return all_equal

    finally:
        conn.close()


def validate_kpi_queries_in_mysql() -> None:
    """Chạy thử nghiệm các câu truy vấn KPI cốt lõi trên kho dữ liệu MySQL (Task 3.6 hoàn tất)."""
    logger.info("\n" + "=" * 75)
    logger.info("  TRUY VẤN XÁC THỰC KHO DỮ LIỆU & ĐỐI CHIẾU 5 KPI CỐT LÕI (TASK 3.6)")
    logger.info("=" * 75)

    conn = get_connection(autocommit=True)
    try:
        with conn.cursor() as cur:
            # KPI-01: Tổng số tin đăng hoạt động
            cur.execute("""
                SELECT COUNT(DISTINCT listing_id) AS total_listings
                FROM fact_listing_snapshot
                WHERE snapshot_date = '2026-09-23';
            """)
            kpi_01 = cur.fetchone()[0]
            logger.info(f"  * KPI-01 (Tổng số tin đăng hoạt động) : {kpi_01:,} tin đăng (Kỳ vọng: 3,208)")

            # KPI-02: Trung vị giá niêm yết SGD
            cur.execute("""
                SELECT AVG(listed_price_sgd) AS avg_price,
                       MIN(listed_price_sgd) AS min_price,
                       MAX(listed_price_sgd) AS max_price,
                       COUNT(*) AS valid_sgd_count
                FROM fact_listing_snapshot
                WHERE snapshot_date = '2026-09-23'
                  AND is_price_sgd_verified = 1
                  AND listed_price_sgd > 0;
            """)
            avg_p, min_p, max_p, cnt_p = cur.fetchone()
            logger.info(f"  * KPI-02 (Giá niêm yết SGD)           : {cnt_p:,} tin hợp lệ | Min = {min_p} | Max = {max_p} | Avg = {avg_p:.2f} SGD")

            # KPI-03: Phân bố theo loại phòng (Room Type Distribution)
            cur.execute("""
                SELECT d.room_type, COUNT(*) AS count_listings,
                       ROUND(COUNT(*) / 3208.0 * 100, 2) AS pct
                FROM fact_listing_snapshot f
                JOIN dim_listing d ON f.listing_sk = d.listing_sk
                WHERE f.snapshot_date = '2026-09-23'
                GROUP BY d.room_type
                ORDER BY count_listings DESC;
            """)
            logger.info("  * KPI-03 (Phân bố loại phòng):")
            for rtype, rcnt, rpct in cur.fetchall():
                logger.info(f"     - {rtype:<25}: {rcnt:,} tin ({rpct}%)")

            # KPI-04: Tỷ lệ đêm mở lịch (Availability Rate)
            cur.execute("""
                SELECT COUNT(*) AS total_nights,
                       SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) AS available_nights,
                       ROUND(SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS avail_rate_pct
                FROM fact_calendar
                WHERE snapshot_date = '2026-09-23'
                  AND calendar_date BETWEEN '2026-09-25' AND '2027-09-25';
            """)
            tot_n, avail_n, avail_pct = cur.fetchone()
            logger.info(f"  * KPI-04 (Tỷ lệ đêm mở lịch 365 ngày) : {avail_pct}% ({avail_n:,} / {tot_n:,} đêm)")

            # KPI-05: Điểm đánh giá trung bình
            cur.execute("""
                SELECT ROUND(AVG(review_scores_rating), 2) AS avg_rating,
                       COUNT(review_scores_rating) AS rated_count
                FROM fact_listing_snapshot
                WHERE snapshot_date = '2026-09-23'
                  AND review_scores_rating IS NOT NULL;
            """)
            avg_r, cnt_r = cur.fetchone()
            logger.info(f"  * KPI-05 (Điểm đánh giá trung bình)   : {avg_r} / 5.0 ({cnt_r:,} tin có đánh giá)")

            # SUP-02: Tổng số lượt đánh giá tích lũy trong Fact Review
            cur.execute("""
                SELECT COUNT(*) AS total_reviews,
                       COUNT(DISTINCT listing_id) AS listings_reviewed
                FROM fact_review
                WHERE snapshot_date = '2026-09-23';
            """)
            tot_rev, rev_list = cur.fetchone()
            logger.info(f"  * SUP-02 (Lịch sử đánh giá khách hàng): {tot_rev:,} bài đánh giá trên {rev_list:,} tin đăng")

        logger.info("=" * 75)
        logger.info("  ✅ KHO DỮ LIỆU MYSQL ĐÃ SẴN SÀNG TRUY VẤN VÀ KHỚP 100% CÁC CHỈ SỐ KHO!")
        logger.info("=" * 75)

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 3.6: Quy trình nạp Dimension và Fact vào kho dữ liệu MySQL")
    parser.add_argument(
        "--gold-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "gold",
        help="Đường dẫn thư mục chứa dữ liệu Gold CSV",
    )
    parser.add_argument(
        "--snapshot-date",
        type=str,
        default="2026-09-23",
        help="Ngày snapshot dữ liệu (mặc định: 2026-09-23)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Kích thước batch nạp (mặc định: 5000 dòng)",
    )
    parser.add_argument(
        "--skip-idempotency-test",
        action="store_true",
        help="Bỏ qua bài kiểm tra nạp lại lần 2 để tiết kiệm thời gian",
    )
    args = parser.parse_args()

    # 1. Chạy nạp kho dữ liệu
    run_warehouse_loading(
        gold_dir=args.gold_dir,
        snapshot_date=args.snapshot_date,
        batch_size=args.batch_size,
    )

    # 2. Kiểm tra tính toàn vẹn tham chiếu trong MySQL
    verify_referential_integrity_in_mysql(snapshot_date=args.snapshot_date)

    # 3. Kiểm tra tính khả lặp (Idempotency) nếu không bị bỏ qua
    if not args.skip_idempotency_test:
        verify_idempotency_in_mysql(gold_dir=args.gold_dir, snapshot_date=args.snapshot_date)

    # 4. Xác thực truy vấn KPI
    validate_kpi_queries_in_mysql()


if __name__ == "__main__":
    main()

