#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
smoke_test.py – Task 1.4: Kiểm tra môi trường Python và kết nối MySQL
======================================================================

Script xác nhận:
  1. Virtual‑environment đang hoạt động.
  2. Tất cả thư viện trong requirements.txt import được.
  3. Đọc thành công từng file CSV / CSV.GZ trong data/raw bằng Pandas.
  4. (Tuỳ chọn) Kết nối MySQL thông qua biến môi trường trong .env.

Cách chạy (từ thư mục gốc dự án):
    python smoke_test.py            # bỏ qua MySQL nếu chưa cài
    python smoke_test.py --mysql    # bắt buộc kiểm tra MySQL

Tác giả : Thái – Data Engineer
Task    : 1.4 – Cài Python, thư viện xử lý và kiểm tra kết nối
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Đảm bảo stdout xử lý được tiếng Việt trên Windows (cp1252 → utf-8)
# ---------------------------------------------------------------------------
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass  # Python < 3.7, bỏ qua

# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

EXPECTED_RAW_FILES = [
    "listings.csv.gz",
    "calendar.csv.gz",
    "reviews.csv.gz",
    "neighbourhoods.csv",
]

# ---------------------------------------------------------------------------
# Tiện ích in kết quả
# ---------------------------------------------------------------------------
_pass_count = 0
_fail_count = 0
_warn_count = 0


def _ok(msg: str) -> None:
    global _pass_count
    _pass_count += 1
    print(f"  [PASS] {msg}")


def _fail(msg: str) -> None:
    global _fail_count
    _fail_count += 1
    print(f"  [FAIL] {msg}")


def _warn(msg: str) -> None:
    global _warn_count
    _warn_count += 1
    print(f"  [WARN] {msg}")


def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# 1. Kiểm tra Python & virtual‑environment
# ---------------------------------------------------------------------------
def check_python() -> None:
    _header("1. Python & Virtual Environment")
    print(f"  Python version : {sys.version}")
    print(f"  Executable     : {sys.executable}")

    # Kiểm tra phiên bản tối thiểu (>= 3.11 theo README)
    if sys.version_info >= (3, 11):
        _ok(f"Python {sys.version_info.major}.{sys.version_info.minor} >= 3.11")
    else:
        _warn(
            f"Python {sys.version_info.major}.{sys.version_info.minor} < 3.11 – "
            "README yêu cầu Python 3.11+. Có thể vẫn chạy được nhưng nên nâng cấp."
        )

    # Kiểm tra virtual‑environment
    in_venv = (
        hasattr(sys, "real_prefix")                          # virtualenv
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)  # venv
    )
    if in_venv:
        _ok("Đang chạy trong virtual environment")
    else:
        _warn(
            "Không phát hiện virtual environment. "
            "Hãy tạo venv theo hướng dẫn trong README trước khi cài thư viện."
        )


# ---------------------------------------------------------------------------
# 2. Kiểm tra import thư viện
# ---------------------------------------------------------------------------
def check_imports() -> None:
    _header("2. Import thư viện")

    libs = {
        "pandas":              "pandas",
        "numpy":               "numpy",
        "sqlalchemy":          "sqlalchemy",
        "pymysql":             "pymysql",
        "dotenv (python-dotenv)": "dotenv",
        "jupyterlab":          "jupyterlab",
        "matplotlib":          "matplotlib",
        "seaborn":             "seaborn",
    }

    for display_name, module_name in libs.items():
        try:
            mod = __import__(module_name)
            version = getattr(mod, "__version__", "n/a")
            _ok(f"{display_name} – version {version}")
        except ImportError:
            _fail(f"{display_name} – KHÔNG import được. Chạy: pip install -r requirements.txt")


# ---------------------------------------------------------------------------
# 3. Đọc file CSV / CSV.GZ trong data/raw
# ---------------------------------------------------------------------------
def check_raw_data() -> None:
    _header("3. Đọc dữ liệu thô (data/raw)")

    try:
        import pandas as pd
    except ImportError:
        _fail("Không import được pandas – bỏ qua phần đọc dữ liệu.")
        return

    if not RAW_DATA_DIR.is_dir():
        _fail(f"Thư mục {RAW_DATA_DIR.relative_to(PROJECT_ROOT)} không tồn tại.")
        return

    for fname in EXPECTED_RAW_FILES:
        fpath = RAW_DATA_DIR / fname
        if not fpath.is_file():
            _fail(f"{fname} – không tìm thấy file")
            continue

        try:
            compression = "gzip" if fname.endswith(".gz") else None
            df = pd.read_csv(fpath, compression=compression, nrows=5)
            size_mb = fpath.stat().st_size / (1024 * 1024)
            _ok(
                f"{fname} – đọc thành công | "
                f"{len(df.columns)} cột, file {size_mb:.2f} MB"
            )
            # In ra 5 cột đầu tiên để minh chứng
            preview_cols = list(df.columns[:5])
            print(f"          Các cột đầu: {preview_cols}")
        except Exception as exc:
            _fail(f"{fname} – lỗi khi đọc: {exc}")

    # Đọc đầy đủ một file nhỏ để chứng minh dữ liệu hợp lệ
    nb_path = RAW_DATA_DIR / "neighbourhoods.csv"
    if nb_path.is_file():
        try:
            df_nb = pd.read_csv(nb_path)
            _ok(
                f"neighbourhoods.csv – đọc đầy đủ {len(df_nb)} dòng, "
                f"{len(df_nb.columns)} cột"
            )
        except Exception as exc:
            _fail(f"neighbourhoods.csv – lỗi đọc đầy đủ: {exc}")


# ---------------------------------------------------------------------------
# 4. Kiểm tra kết nối MySQL (tuỳ chọn)
# ---------------------------------------------------------------------------
def check_mysql(required: bool = False) -> None:
    _header("4. Kết nối MySQL")

    # Đọc biến môi trường từ .env (nếu có)
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"

    try:
        from dotenv import load_dotenv
        if env_file.is_file():
            load_dotenv(env_file)
            _ok(".env đã được tải")
        else:
            _warn(
                ".env chưa tồn tại. Sao chép .env.example → .env và điền thông tin. "
                "Tuyệt đối không commit .env."
            )
            if not required:
                print("          → Bỏ qua kiểm tra MySQL (dùng --mysql để bắt buộc).")
                return
    except ImportError:
        _fail("python-dotenv chưa cài. Chạy: pip install python-dotenv")
        return

    # Lấy thông tin kết nối từ biến môi trường
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "airbnb_sg_dw")

    if not user:
        msg = "MYSQL_USER chưa được thiết lập trong .env"
        _fail(msg) if required else _warn(msg)
        return
    if not password:
        msg = "MYSQL_PASSWORD chưa được thiết lập trong .env"
        _fail(msg) if required else _warn(msg)
        return

    # Thử kết nối bằng SQLAlchemy + PyMySQL
    try:
        from sqlalchemy import create_engine, text

        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(url, connect_args={"connect_timeout": 5})

        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.scalar()
            _ok(f"Kết nối MySQL thành công – Server version: {version}")

            # Thử tạo bảng tạm để xác nhận quyền ghi
            conn.execute(text(
                "CREATE TEMPORARY TABLE _smoke_test_tmp (id INT)"
            ))
            conn.execute(text("DROP TEMPORARY TABLE _smoke_test_tmp"))
            _ok("Tạo/xoá bảng tạm thành công – quyền ghi hợp lệ")

    except Exception as exc:
        msg = f"Kết nối MySQL thất bại: {exc}"
        _fail(msg) if required else _warn(msg + " (Phối hợp Minh – Task 1.5 để cài MySQL)")


# ---------------------------------------------------------------------------
# 5. Tổng kết
# ---------------------------------------------------------------------------
def summary() -> None:
    _header("KẾT QUẢ TỔNG HỢP")
    print(f"  PASS : {_pass_count}")
    print(f"  WARN : {_warn_count}")
    print(f"  FAIL : {_fail_count}")
    print()

    if _fail_count == 0:
        print("  ✅ Môi trường sẵn sàng! Có thể bắt đầu phát triển pipeline.")
    else:
        print("  ❌ Có lỗi cần khắc phục. Xem chi tiết [FAIL] ở trên.")
        print()
        print(textwrap.dedent("""\
        Hướng dẫn nhanh:
          1. python -m venv .venv
          2. .venv\\Scripts\\Activate.ps1       # Windows PowerShell
             source .venv/bin/activate         # macOS / Linux
          3. pip install -r requirements.txt
          4. cp .env.example .env              # điền thông tin MySQL
          5. python smoke_test.py
        """))

    sys.exit(1 if _fail_count > 0 else 0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke test – Kiểm tra môi trường Python và kết nối MySQL"
    )
    parser.add_argument(
        "--mysql",
        action="store_true",
        help="Bắt buộc kiểm tra kết nối MySQL (mặc định chỉ cảnh báo nếu chưa sẵn sàng)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  SMOKE TEST – Task 1.4")
    print("  Airbnb Singapore Data Warehouse")
    print("=" * 60)

    check_python()
    check_imports()
    check_raw_data()
    check_mysql(required=args.mysql)
    summary()


if __name__ == "__main__":
    main()
