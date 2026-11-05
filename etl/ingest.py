#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
etl/ingest.py – Task 3.2: Module Ingestion Dữ Liệu Nguồn vào Raw/Staging
======================================================================
1. Đọc CSV / CSV.GZ theo file cấu hình (etl/config.yaml), mã hóa utf-8-sig.
2. Xử lý theo chunk cho tập dữ liệu lớn (Calendar > 1.17 triệu dòng).
3. Hỗ trợ chạy thử mẫu (--sample N) trước khi nạp đầy đủ.
4. Đảm bảo tính khả lặp (Idempotency - TQ-05): Xóa partition snapshot trước khi nạp.
5. Ghi log kiểm toán chi tiết (console, file logs/ingest.log và bảng etl_ingest_log).

Tác giả : Thái (Data Engineer / ETL)
Phối hợp: Minh (MySQL / Warehouse)
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
from typing import Any, Dict, Optional

import pandas as pd
import yaml

# Đảm bảo import được etl.db
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.db import (
    create_staging_tables_ddl,
    delete_snapshot_partition,
    get_engine,
    is_db_available,
)

# ---------------------------------------------------------------------------
# Cấu hình logging
# ---------------------------------------------------------------------------
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "ingest.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ingest")


def load_config(config_path: Path) -> Dict[str, Any]:
    """Nạp file cấu hình YAML."""
    if not config_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình tại {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def log_ingest_result(
    engine: Any,
    source_name: str,
    file_name: str,
    snapshot_date: str,
    rows_read: int,
    rows_inserted: int,
    rows_failed: int,
    status: str,
    execution_seconds: float,
    started_at: datetime.datetime,
    completed_at: datetime.datetime,
    error_message: Optional[str] = None,
) -> None:
    """Ghi log kiểm toán vào MySQL nếu có kết nối."""
    if engine is None:
        return
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO etl_ingest_log (
                        source_name, file_name, snapshot_date,
                        rows_read, rows_inserted, rows_failed,
                        status, execution_seconds, started_at, completed_at, error_message
                    ) VALUES (
                        :source_name, :file_name, :snapshot_date,
                        :rows_read, :rows_inserted, :rows_failed,
                        :status, :execution_seconds, :started_at, :completed_at, :error_message
                    )
                    """
                ),
                {
                    "source_name": source_name,
                    "file_name": file_name,
                    "snapshot_date": snapshot_date,
                    "rows_read": rows_read,
                    "rows_inserted": rows_inserted,
                    "rows_failed": rows_failed,
                    "status": status,
                    "execution_seconds": round(execution_seconds, 2),
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "error_message": error_message,
                },
            )
    except Exception as exc:
        logger.warning(f"Không thể ghi log vào MySQL etl_ingest_log: {exc}")


def ingest_source(
    source_name: str,
    source_cfg: Dict[str, Any],
    project_cfg: Dict[str, Any],
    sample_size: Optional[int] = None,
    save_staging_files: bool = True,
) -> Dict[str, Any]:
    """
    Thực hiện ingestion cho một nguồn dữ liệu:
    - Đọc CSV/GZ theo chunk
    - Bổ sung metadata (snapshot_date, source_file, ingested_at)
    - Nạp vào MySQL (nếu có) và xuất file Staging
    """
    started_at = datetime.datetime.now()
    t0 = time.time()

    raw_dir = PROJECT_ROOT / project_cfg["paths"]["raw_dir"]
    staging_dir = PROJECT_ROOT / project_cfg["paths"]["staging_dir"]
    staging_dir.mkdir(parents=True, exist_ok=True)

    file_name = source_cfg["file_name"]
    file_path = raw_dir / file_name
    snapshot_date = project_cfg["project"]["snapshot_date"]
    table_name = source_cfg["staging_table"]
    compression = source_cfg.get("compression")
    encoding = source_cfg.get("encoding", "utf-8-sig")
    chunk_size = source_cfg.get("chunk_size", 50000)

    if not file_path.is_file():
        raise FileNotFoundError(f"File nguồn không tồn tại: {file_path}")

    logger.info(f"=== Bắt đầu Ingestion: {source_name} ({file_name}) ===")
    if sample_size:
        logger.info(f"Chế độ chạy thử mẫu (Sample mode): tối đa {sample_size} dòng.")

    # 1. Kiểm tra kết nối MySQL & Áp dụng Idempotency
    db_ok = is_db_available()
    engine = get_engine() if db_ok else None

    if db_ok and sample_size is None:
        delete_snapshot_partition(table_name, snapshot_date)

    total_rows_read = 0
    total_rows_inserted = 0
    total_rows_failed = 0
    chunks_processed = 0

    # Danh sách buffer lưu dữ liệu staging cho file xuất ra
    staging_data_frames = []

    try:
        # Nếu sample_size nhỏ hơn chunk_size thì dùng sample_size làm chunk
        actual_chunk_size = chunk_size if sample_size is None else min(chunk_size, sample_size)

        reader = pd.read_csv(
            file_path,
            compression=compression,
            encoding=encoding,
            chunksize=actual_chunk_size,
            low_memory=False,
        )

        for chunk_df in reader:
            if sample_size is not None and total_rows_read >= sample_size:
                break

            current_chunk = chunk_df
            if sample_size is not None and (total_rows_read + len(current_chunk)) > sample_size:
                needed = sample_size - total_rows_read
                current_chunk = current_chunk.iloc[:needed]

            rows_in_chunk = len(current_chunk)
            total_rows_read += rows_in_chunk

            # Bổ sung 3 cột metadata kiểm toán
            current_chunk = current_chunk.copy()
            current_chunk["snapshot_date"] = snapshot_date
            current_chunk["source_file"] = file_name
            current_chunk["ingested_at"] = started_at.strftime("%Y-%m-%d %H:%M:%S")

            # Nạp vào MySQL Staging nếu có kết nối
            if db_ok and engine is not None:
                try:
                    current_chunk.to_sql(
                        name=table_name,
                        con=engine,
                        if_exists="append",
                        index=False,
                        method="multi",
                        chunksize=1000,
                    )
                    total_rows_inserted += rows_in_chunk
                except Exception as db_exc:
                    logger.error(f"Lỗi ghi chunk vào MySQL: {db_exc}")
                    total_rows_failed += rows_in_chunk
            else:
                total_rows_inserted += rows_in_chunk

            # Lưu vào bộ nhớ để xuất file staging
            if save_staging_files:
                staging_data_frames.append(current_chunk)

            chunks_processed += 1
            if chunks_processed % 5 == 0 or total_rows_read >= source_cfg.get("expected_rows", 0):
                logger.info(f"  -> Đã đọc {total_rows_read:,} dòng ({chunks_processed} chunks)...")

        # Xuất file staging Parquet & CSV (dành cho kiểm toán & chạy offline)
        if save_staging_files and staging_data_frames:
            combined_staging_df = pd.concat(staging_data_frames, ignore_index=True)
            out_parquet = staging_dir / f"{table_name}.parquet"
            out_csv = staging_dir / f"{table_name}.csv"
            
            try:
                combined_staging_df.to_parquet(out_parquet, index=False)
            except Exception:
                pass  # Nếu thiếu pyarrow thì bỏ qua parquet
            combined_staging_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
            logger.info(f"Đã lưu Staging data tại: {out_csv} ({len(combined_staging_df):,} dòng)")

        elapsed = time.time() - t0
        status = "SUCCESS" if total_rows_failed == 0 else "PARTIAL"
        completed_at = datetime.datetime.now()

        # Kiểm tra đối chiếu số dòng đọc và kỳ vọng
        expected_rows = source_cfg.get("expected_rows")
        if sample_size is None and expected_rows and total_rows_read != expected_rows:
            logger.warning(
                f"CẢNH BÁO: Số dòng đọc ({total_rows_read:,}) khác số dòng kỳ vọng ({expected_rows:,})!"
            )

        logger.info(
            f"Hoàn tất Ingestion {source_name}: Đọc {total_rows_read:,} dòng | "
            f"Nạp {total_rows_inserted:,} dòng | Thất bại: {total_rows_failed} | "
            f"Thời gian: {elapsed:.2f}s | Trạng thái: {status}"
        )

        log_ingest_result(
            engine=engine,
            source_name=source_name,
            file_name=file_name,
            snapshot_date=snapshot_date,
            rows_read=total_rows_read,
            rows_inserted=total_rows_inserted,
            rows_failed=total_rows_failed,
            status=status,
            execution_seconds=elapsed,
            started_at=started_at,
            completed_at=completed_at,
        )

        return {
            "source_name": source_name,
            "file_name": file_name,
            "rows_read": total_rows_read,
            "rows_inserted": total_rows_inserted,
            "rows_failed": total_rows_failed,
            "status": status,
            "execution_seconds": elapsed,
        }

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error(f"Thất bại khi Ingest {source_name}: {exc}", exc_info=True)
        log_ingest_result(
            engine=engine,
            source_name=source_name,
            file_name=file_name,
            snapshot_date=snapshot_date,
            rows_read=total_rows_read,
            rows_inserted=total_rows_inserted,
            rows_failed=total_rows_read - total_rows_inserted,
            status="FAILED",
            execution_seconds=elapsed,
            started_at=started_at,
            completed_at=datetime.datetime.now(),
            error_message=str(exc),
        )
        raise exc


def run_ingest_pipeline(
    config_path: Path,
    sample_size: Optional[int] = None,
    target_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Chạy toàn bộ pipeline ingestion theo cấu hình."""
    config = load_config(config_path)

    print("=" * 70)
    print("  AIRBNB SINGAPORE DATA WAREHOUSE – TASK 3.2: INGESTION PIPELINE")
    print(f"  Snapshot Date: {config['project']['snapshot_date']}")
    print(f"  Target DB    : {config['database']['default_database']}")
    print("=" * 70)

    # Khởi tạo bảng Staging nếu có kết nối MySQL
    if is_db_available():
        logger.info("Kết nối MySQL khả dụng. Đang kiểm tra DDL bảng Staging...")
        create_staging_tables_ddl()
    else:
        logger.warning(
            "MySQL hiện chưa kết nối được qua .env. "
            "Pipeline sẽ chạy ở chế độ File-based Staging (lưu vào data/processed/staging/)."
        )

    sources = config["sources"]
    if target_source and target_source.lower() != "all":
        if target_source not in sources:
            raise ValueError(f"Nguồn '{target_source}' không hợp lệ. Chọn: {list(sources.keys())}")
        sources = {target_source: sources[target_source]}

    results = {}
    total_start = time.time()

    for sname, scfg in sources.items():
        res = ingest_source(
            source_name=sname,
            source_cfg=scfg,
            project_cfg=config,
            sample_size=sample_size,
        )
        results[sname] = res

    total_time = time.time() - total_start
    print("\n" + "=" * 70)
    print("  KẾT QUẢ TỔNG HỢP INGESTION (TASK 3.2)")
    print("=" * 70)
    for sname, r in results.items():
        print(f"  - {sname.upper():<16}: Đọc {r['rows_read']:,} | Nạp {r['rows_inserted']:,} | Trạng thái: {r['status']} ({r['execution_seconds']:.2f}s)")
    print(f"  Tổng thời gian: {total_time:.2f}s")
    print("=" * 70)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 3.2: Ingestion pipeline vào Staging")
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "etl" / "config.yaml",
        help="Đường dẫn file cấu hình YAML (mặc định: etl/config.yaml)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Chạy thử mẫu với N dòng đầu tiên của mỗi file (ví dụ: --sample 500)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="all",
        help="Chỉ định nguồn nạp (listings, calendar, reviews, neighbourhoods, hoặc all)",
    )
    args = parser.parse_args()

    run_ingest_pipeline(
        config_path=args.config,
        sample_size=args.sample,
        target_source=args.source,
    )


if __name__ == "__main__":
    main()
