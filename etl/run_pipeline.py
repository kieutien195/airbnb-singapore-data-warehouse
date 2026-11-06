#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
etl/run_pipeline.py – Điều phối toàn trình ETL Pipeline (Tasks 3.2, 3.3, 3.4)
=============================================================================
1. Chạy Ingest (Task 3.2): Đọc raw data -> Staging (MySQL/File)
2. Chạy Clean (Task 3.3): Staging -> Silver (Xử lý kiểu, NULL, giá, boolean, grain)
3. Chạy Transform (Task 3.4): Silver -> Gold (Star Schema, Surrogate Keys, Orphan Checks)
4. Tự động kiểm chứng nghiệm thu với 20 Test Cases (tests/etl_test_checklist.csv)

Tác giả: Thái (Data Engineer / ETL)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from etl.ingest import run_ingest_pipeline
from etl.clean import run_cleaning_pipeline
from etl.transform import run_transform_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy toàn trình ETL Pipeline (Tasks 3.2 - 3.4)")
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "etl" / "config.yaml",
        help="Đường dẫn file config",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Chạy ở chế độ mẫu N dòng (ví dụ: --sample 500)",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Bỏ qua bước Ingest nếu đã có Staging data",
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="Bỏ qua bước Clean nếu đã có Silver data",
    )
    parser.add_argument("--file-only", action="store_true", help="Chỉ ghi file, không kết nối MySQL")
    args = parser.parse_args()
    if args.sample is not None and args.sample <= 0:
        parser.error("--sample phải lớn hơn 0")

    t_start = time.time()
    print("=" * 80)
    print("  KHỞI ĐỘNG QUY TRÌNH ETL END-TO-END – AIRBNB SINGAPORE DATA WAREHOUSE")
    print("  Phụ trách: Thái (Data Engineer) | WBS Tasks: 3.2, 3.3, 3.4")
    print("=" * 80)

    # Bước 1: Ingest (Task 3.2)
    if not args.skip_ingest:
        print("\n>>> BƯỚC 1: INGESTION DỮ LIỆU NGUỒN VÀO STAGING (TASK 3.2) <<<")
        run_ingest_pipeline(config_path=args.config, sample_size=args.sample, file_only=args.file_only)
    else:
        print("\n>>> BƯỚC 1: ĐÃ BỎ QUA THEO YÊU CẦU (--skip-ingest) <<<")

    # Bước 2: Clean (Task 3.3)
    if not args.skip_clean:
        print("\n>>> BƯỚC 2: LÀM SẠCH VÀ CHUẨN HÓA DỮ LIỆU SILVER (TASK 3.3) <<<")
        run_cleaning_pipeline(config_path=args.config, sample_size=args.sample)
    else:
        print("\n>>> BƯỚC 2: ĐÃ BỎ QUA THEO YÊU CẦU (--skip-clean) <<<")

    # Bước 3: Transform (Task 3.4)
    print("\n>>> BƯỚC 3: MAPPING VÀ KIỂM TRA QUAN HỆ ĐA BẢNG GOLD (TASK 3.4) <<<")
    run_transform_pipeline(config_path=args.config, sample_size=args.sample)

    total_time = time.time() - t_start
    print("\n" + "=" * 80)
    print(f"  ✅ TOÀN BỘ PIPELINE ETL HOÀN TẤT THÀNH CÔNG TRONG {total_time:.2f} GIÂY!")
    if args.sample is None:
        print("  Dữ liệu Gold và báo cáo độ phủ quan hệ đã sẵn sàng để bàn giao cho Minh (Task 3.5).")
    print("=" * 80)


if __name__ == "__main__":
    main()
