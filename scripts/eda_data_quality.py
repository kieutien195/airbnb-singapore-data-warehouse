"""
eda_data_quality.py
Task 2.3 - EDA: Missing, Duplicates, Outliers và phân bố

Phạm vi:
- Khảo sát dữ liệu Singapore Airbnb.
- Đánh giá NULL, Duplicates và giá trị ngoài miền hợp lệ.
- Phân tích phân bố và Outliers bằng IQR.
- Kiểm tra tính toàn vẹn tham chiếu giữa các bảng.
- Tạo và thực thi notebook 01_eda.ipynb.
- Xuất data_quality_baseline.csv và cleaning recommendations.

Lưu ý:
- Không chỉnh sửa dữ liệu gốc.
- Không tự động xóa NULL, Duplicates hoặc Outliers.
"""

from pathlib import Path
import sys
import traceback

import nbformat
from nbclient import NotebookClient


# ============================================================
# 1. CẤU HÌNH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"
TEST_DIR = PROJECT_ROOT / "tests"
EDA_DOCS_DIR = PROJECT_ROOT / "docs" / "eda"

NOTEBOOK_PATH = NOTEBOOK_DIR / "01_eda.ipynb"

BASELINE_PATH = TEST_DIR / "data_quality_baseline.csv"

RECOMMENDATIONS_CSV_PATH = (
    EDA_DOCS_DIR / "cleaning_recommendations.csv"
)

RECOMMENDATIONS_MD_PATH = (
    EDA_DOCS_DIR / "cleaning_recommendations.md"
)

KERNEL_NAME = "python3"

EXPECTED_RAW_FILES = [
    "listings.csv.gz",
    "calendar.csv.gz",
    "reviews.csv.gz",
    "neighbourhoods.csv",
]

_pass_count = 0
_warn_count = 0
_fail_count = 0


# ============================================================
# 2. HÀM HIỂN THỊ
# ============================================================

def _set_console_encoding():
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")


def _ok(message):
    global _pass_count
    _pass_count += 1
    print(f"[PASS] {message}")


def _warn(message):
    global _warn_count
    _warn_count += 1
    print(f"[WARN] {message}")


def _fail(message):
    global _fail_count
    _fail_count += 1
    print(f"[FAIL] {message}")


def _header(title):
    print()
    print("=" * 75)
    print(title)
    print("=" * 75)


def _summary():
    _header("TỔNG KẾT TASK 2.3")

    print(f"Số bước thành công: {_pass_count}")
    print(f"Số cảnh báo: {_warn_count}")
    print(f"Số bước thất bại: {_fail_count}")

    if _fail_count == 0:
        print("\n[PASS] Chương trình đã kết thúc.")
    else:
        print("\n[FAIL] Chương trình còn bước chưa hoàn thành.")


# ============================================================
# 3. KIỂM TRA DỮ LIỆU ĐẦU VÀO
# ============================================================

def check_raw_data():
    _header("1. KIỂM TRA DỮ LIỆU ĐẦU VÀO")

    if not RAW_DATA_DIR.exists():
        _fail(f"Không tìm thấy thư mục: {RAW_DATA_DIR}")
        return False

    all_exist = True

    for filename in EXPECTED_RAW_FILES:
        file_path = RAW_DATA_DIR / filename

        if file_path.exists():
            _ok(f"Tìm thấy {filename}")
        else:
            _fail(f"Không tìm thấy {filename}")
            all_exist = False

    return all_exist


# ============================================================
# 4. TẠO NOTEBOOK
# ============================================================

def build_notebook():
    """Tạo notebook có thể chạy từ repo hoặc notebooks; output do các cell sinh."""
    for directory in (NOTEBOOK_DIR, TEST_DIR, EDA_DOCS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    notebook = nbformat.v4.new_notebook(metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": KERNEL_NAME},
        "language_info": {"name": "python"},
    })
    cells = []
    cells.append(nbformat.v4.new_markdown_cell(r'''
# Task 2.3 – EDA: Missing, Duplicates, Outliers và phân bố

## 1. Mục tiêu

Notebook thực hiện khảo sát dữ liệu Singapore Airbnb nhằm đánh giá
chất lượng dữ liệu trước khi chuyển sang các bước xử lý tiếp theo.

Các nội dung chính:

1. Khảo sát cấu trúc và kích thước dữ liệu.
2. Thống kê số lượng và tỷ lệ NULL.
3. Kiểm tra Duplicates theo đúng grain của từng bảng.
4. Kiểm tra giá trị ngoài miền hợp lệ.
5. Phân tích phân bố dữ liệu.
6. Nhận diện Outliers bằng phương pháp IQR.
7. Kiểm tra tính toàn vẹn tham chiếu giữa các bảng.
8. Đánh giá nguy cơ JOIN fan-out.

## 2. Phạm vi

Notebook chỉ thực hiện EDA và đánh giá chất lượng dữ liệu.

Không tự động xóa NULL, Duplicates hoặc Outliers.
Dữ liệu nguồn trong `data/raw` được giữ nguyên.

## 3. Các bảng dữ liệu

- Listings
- Calendar
- Reviews
- Neighbourhoods
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

%matplotlib inline

import importlib.util
from IPython.display import display

PROJECT_ROOT = next((p for p in [Path.cwd(), *Path.cwd().parents]
    if (p / "scripts" / "eda_support.py").is_file()
    and (p / "data" / "raw").is_dir()), None)
if PROJECT_ROOT is None:
    raise FileNotFoundError("Mở notebook từ repo hoặc thư mục notebooks có data/raw.")
spec = importlib.util.spec_from_file_location("eda_support", PROJECT_ROOT / "scripts" / "eda_support.py")
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

TEST_DIR = PROJECT_ROOT / "tests"
EDA_DOCS_DIR = PROJECT_ROOT / "docs" / "eda"

BASELINE_PATH = TEST_DIR / "data_quality_baseline.csv"
RECOMMENDATIONS_CSV_PATH = (
    EDA_DOCS_DIR / "cleaning_recommendations.csv"
)
RECOMMENDATIONS_MD_PATH = (
    EDA_DOCS_DIR / "cleaning_recommendations.md"
)

TEST_DIR.mkdir(parents=True, exist_ok=True)
EDA_DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Đọc dữ liệu nguồn
listings = pd.read_csv(
    RAW_DATA_DIR / "listings.csv.gz",
    compression="gzip",
    low_memory=False
)

calendar = pd.read_csv(
    RAW_DATA_DIR / "calendar.csv.gz",
    compression="gzip",
    low_memory=False
)

reviews = pd.read_csv(
    RAW_DATA_DIR / "reviews.csv.gz",
    compression="gzip",
    low_memory=False
)

neighbourhoods = pd.read_csv(
    RAW_DATA_DIR / "neighbourhoods.csv"
)

data_tables = {
    "Listings": listings,
    "Calendar": calendar,
    "Reviews": reviews,
    "Neighbourhoods": neighbourhoods
}

print("Đã đọc dữ liệu thành công.")
print("-" * 65)

for table_name, dataframe in data_tables.items():
    print(
        f"{table_name}: "
        f"{len(dataframe):,} dòng, "
        f"{len(dataframe.columns):,} cột"
    )
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## 4. Khảo sát tổng quan dữ liệu

Thống kê số dòng, số cột, tổng số ô NULL và số dòng trùng hoàn toàn
của từng bảng dữ liệu.
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
overview_rows = []

for table_name, dataframe in data_tables.items():
    overview_rows.append({
        "dataset": table_name,
        "row_count": len(dataframe),
        "column_count": len(dataframe.columns),
        "null_cells": int(dataframe.isna().sum().sum()),
        "full_duplicate_rows": int(dataframe.duplicated().sum())
    })

overview_df = pd.DataFrame(overview_rows)

display(overview_df)

for table_name, dataframe in data_tables.items():
    print(f"\n===== {table_name} =====")
    # Chỉ hiển thị khóa và trường phục vụ khảo sát, tránh văn bản cá nhân dài.
    sample_columns = [c for c in ["id", "listing_id", "date", "price", "room_type",
        "neighbourhood_group", "neighbourhood", "available"] if c in dataframe.columns]
    display(dataframe[sample_columns].head())

print("\nThông tin kiểu dữ liệu Listings:")
display(
    pd.DataFrame({
        "column": listings.columns,
        "dtype": listings.dtypes.astype(str).values
    })
)
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## 5. Đánh giá NULL và Duplicates

### 5.1. NULL

Thống kê số lượng và tỷ lệ NULL trên từng trường của mỗi bảng.

### 5.2. Duplicates

Grain được sử dụng để kiểm tra:

| Bảng | Grain |
|---|---|
| Listings | `id` |
| Calendar | `listing_id`, `date` |
| Reviews | `listing_id`, `id` |
| Neighbourhoods | `neighbourhood_group`, `neighbourhood` |

Đối với Reviews, không sử dụng riêng `id` làm khóa kiểm tra
vì dữ liệu đang khảo sát có cùng id xuất hiện ở nhiều listing.
Khóa ghép là khóa khảo sát trên nguồn hiện tại; tính duy nhất quan sát
được không tự chứng minh đây là khóa nghiệp vụ đúng cho mọi nguồn.
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
baseline_rows = []

def add_baseline(
    dimension,
    table_name,
    field_name,
    check_name,
    observed_value,
    total_records=None,
    percentage=None,
    status="INFO",
    note=""
):
    baseline_rows.append({
        "quality_dimension": dimension,
        "dataset": table_name,
        "field_or_key": field_name,
        "check_name": check_name,
        "observed_value": observed_value,
        "total_records": total_records,
        "percentage": percentage,
        "status": status,
        "note": note
    })


# 5.1. NULL theo từng trường
null_rows = []

for table_name, dataframe in data_tables.items():
    total_rows = len(dataframe)

    for column in dataframe.columns:
        null_count = int(dataframe[column].isna().sum())

        null_percentage = (
            null_count / total_rows * 100
            if total_rows else 0
        )

        null_rows.append({
            "dataset": table_name,
            "field": column,
            "null_count": null_count,
            "total_records": total_rows,
            "null_percentage": round(null_percentage, 4)
        })

        add_baseline(
            dimension="NULL",
            table_name=table_name,
            field_name=column,
            check_name="NULL count",
            observed_value=null_count,
            total_records=total_rows,
            percentage=round(null_percentage, 4),
            status="WARN" if null_count else "PASS",
            note="Số lượng giá trị NULL tại trường dữ liệu."
        )

null_df = pd.DataFrame(null_rows)

print("Kết quả NULL của toàn bộ trường (theo cách đọc NA mặc định của Pandas):")
with pd.option_context("display.max_rows", None, "display.max_columns", None):
    display(null_df)

print("Các trường có NULL:")
display(
    null_df[null_df["null_count"] > 0]
    .sort_values(
        ["dataset", "null_percentage"],
        ascending=[True, False]
    )
)


# 5.2. Duplicates theo đúng grain
grain_keys = {
    "Listings": ["id"],
    "Calendar": ["listing_id", "date"],
    "Reviews": ["listing_id", "id"],
    "Neighbourhoods": [
        "neighbourhood_group",
        "neighbourhood"
    ]
}

duplicate_rows = []

for table_name, keys in grain_keys.items():
    dataframe = data_tables[table_name]

    missing_keys = [
        column for column in keys
        if column not in dataframe.columns
    ]

    if missing_keys:
        print(
            f"[WARN] {table_name} thiếu các cột khóa: "
            f"{missing_keys}"
        )
        continue

    duplicate_count = int(
        dataframe.duplicated(subset=keys, keep="first").sum()
    )

    total_rows = len(dataframe)

    duplicate_percentage = (
        duplicate_count / total_rows * 100
        if total_rows else 0
    )

    duplicate_rows.append({
        "dataset": table_name,
        "grain": " + ".join(keys),
        "duplicate_count": duplicate_count,
        "total_records": total_rows,
        "duplicate_percentage": round(
            duplicate_percentage, 4
        )
    })

    add_baseline(
        dimension="Duplicates",
        table_name=table_name,
        field_name=" + ".join(keys),
        check_name="Duplicate by grain",
        observed_value=duplicate_count,
        total_records=total_rows,
        percentage=round(duplicate_percentage, 4),
        status="WARN" if duplicate_count else "PASS",
        note="Số bản ghi trùng theo grain của bảng."
    )

duplicate_df = pd.DataFrame(duplicate_rows)

print("Kết quả kiểm tra Duplicates:")
display(duplicate_df)
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## 6. Kiểm tra giá trị ngoài miền hợp lệ

Kiểm tra các trường số, ngày tháng và trường phân loại có miền
giá trị xác định.

Các giá trị không hợp lệ được ghi nhận trong baseline để xem xét,
không tự động chỉnh sửa dữ liệu.
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
def check_numeric_domain(
    dataframe,
    table_name,
    column,
    condition,
    description
):
    if column not in dataframe.columns:
        print(f"[WARN] Không tìm thấy {table_name}.{column}")
        return

    values = pd.to_numeric(
        dataframe[column],
        errors="coerce"
    )

    invalid_conversion = (
        dataframe[column].notna() & values.isna()
    )

    invalid_domain = (
        values.notna() & (~np.isfinite(values) | ~condition(values))
    )

    invalid_count = int(
        invalid_conversion.sum() + invalid_domain.sum()
    )

    total_non_null = int(dataframe[column].notna().sum())

    percentage = (
        invalid_count / total_non_null * 100
        if total_non_null else 0
    )

    add_baseline(
        dimension="Out of domain",
        table_name=table_name,
        field_name=column,
        check_name="Numeric domain validation",
        observed_value=invalid_count,
        total_records=total_non_null,
        percentage=round(percentage, 4),
        status=("N/A" if total_non_null == 0 else "WARN" if invalid_count else "PASS"),
        note=description
    )

    print(
        f"{table_name}.{column}: "
        f"{invalid_count:,} giá trị cần kiểm tra "
        f"/ {total_non_null:,} giá trị không NULL."
    )


def check_date_domain(dataframe, table_name, column):
    if column not in dataframe.columns:
        return

    parsed = pd.to_datetime(
        dataframe[column],
        errors="coerce"
    )

    invalid_mask = (
        dataframe[column].notna() & parsed.isna()
    )

    invalid_count = int(invalid_mask.sum())
    total_non_null = int(dataframe[column].notna().sum())

    percentage = (
        invalid_count / total_non_null * 100
        if total_non_null else 0
    )

    add_baseline(
        dimension="Out of domain",
        table_name=table_name,
        field_name=column,
        check_name="Date validation",
        observed_value=invalid_count,
        total_records=total_non_null,
        percentage=round(percentage, 4),
        status=(
            "N/A" if total_non_null == 0
            else "WARN" if invalid_count else "PASS"
        ),
        note="Số giá trị ngày tháng không thể chuyển đổi."
    )


# Listings: miền hợp lệ của các trường số
listing_numeric_rules = {
    "id": (
        lambda x: x > 0,
        "Listing ID phải lớn hơn 0."
    ),
    "host_id": (
        lambda x: x > 0,
        "Host ID phải lớn hơn 0."
    ),
    "accommodates": (
        lambda x: x > 0,
        "Sức chứa phải lớn hơn 0."
    ),
    "minimum_nights": (
        lambda x: x > 0,
        "Số đêm tối thiểu phải lớn hơn 0."
    ),
    "maximum_nights": (
        lambda x: x > 0,
        "Số đêm tối đa phải lớn hơn 0."
    ),
    "review_scores_rating": (
        lambda x: x.between(1, 5),
        "Miền quan sát 1–5, thống nhất KPI; chưa xác minh metadata chính thức. NULL không đổi thành 0."
    ),
    "latitude": (
        lambda x: x.between(-90, 90),
        "Latitude phải nằm trong khoảng -90 đến 90."
    ),
    "longitude": (
        lambda x: x.between(-180, 180),
        "Longitude phải nằm trong khoảng -180 đến 180."
    )
}

for column, (condition, description) in listing_numeric_rules.items():
    check_numeric_domain(
        listings,
        "Listings",
        column,
        condition,
        description
    )


# Giá chính theo KPI: Listings.price, hữu hạn, >0, currency SGD xác nhận từ JSON.
price_analysis = support.prepare_prices(listings)
price_column = "price"
price_unit = "SGD/đêm"
numeric_price = price_analysis["listed_price_numeric"]
invalid_price = listings["price"].notna() & (
    numeric_price.isna() | ~np.isfinite(numeric_price) | numeric_price.le(0))
excluded_currency = numeric_price.notna() & np.isfinite(numeric_price) & numeric_price.gt(0) & price_analysis["currency"].ne("SGD")
add_baseline("Out of domain", "Listings", "price", "Parsed finite positive price",
    int(invalid_price.sum()), int(listings["price"].notna().sum()),
    status="WARN" if invalid_price.any() else "PASS", note="Parse $ và dấu phẩy; giữ raw, không điền 0.")
add_baseline("Currency", "Listings", "price", "Numeric positive price without confirmed SGD",
    int(excluded_currency.sum()), int(numeric_price.notna().sum()),
    status="WARN" if excluded_currency.any() else "PASS", note="Loại khỏi mẫu giá SGD; không suy currency từ ký hiệu $.")

# Calendar
calendar_numeric_rules = {
    "listing_id": (
        lambda x: x > 0,
        "listing_id phải lớn hơn 0."
    ),
    "minimum_nights": (
        lambda x: x > 0,
        "minimum_nights phải lớn hơn 0."
    ),
    "maximum_nights": (
        lambda x: x > 0,
        "maximum_nights phải lớn hơn 0."
    )
}

for column, (condition, description) in calendar_numeric_rules.items():
    check_numeric_domain(
        calendar,
        "Calendar",
        column,
        condition,
        description
    )


# Reviews
review_numeric_rules = {
    "listing_id": (
        lambda x: x > 0,
        "listing_id phải lớn hơn 0."
    ),
    "id": (
        lambda x: x > 0,
        "Review ID phải lớn hơn 0."
    ),
    "reviewer_id": (
        lambda x: x > 0,
        "Reviewer ID phải lớn hơn 0."
    )
}

for column, (condition, description) in review_numeric_rules.items():
    check_numeric_domain(
        reviews,
        "Reviews",
        column,
        condition,
        description
    )


# Kiểm tra ngày tháng
date_rules = {
    "Listings": (
        listings,
        ["last_scraped", "host_since", "first_review", "last_review"]
    ),
    "Calendar": (
        calendar,
        ["date"]
    ),
    "Reviews": (
        reviews,
        ["date"]
    )
}

for table_name, (dataframe, columns) in date_rules.items():
    for column in columns:
        check_date_domain(dataframe, table_name, column)


# Kiểm tra available trong Calendar
if "available" in calendar.columns:
    available_values = (
        calendar["available"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
    )

    allowed_values = {"t", "f"}

    invalid_count = int(
        (~available_values.isin(allowed_values)).sum()
    )

    total_values = len(available_values)

    percentage = (
        invalid_count / total_values * 100
        if total_values else 0
    )

    add_baseline(
        dimension="Out of domain",
        table_name="Calendar",
        field_name="available",
        check_name="Allowed values",
        observed_value=invalid_count,
        total_records=total_values,
        percentage=round(percentage, 4),
        status="WARN" if invalid_count else "PASS",
        note="Giá trị hợp lệ được ghi nhận là t hoặc f."
    )

    print(
        f"Calendar.available: {invalid_count:,} giá trị "
        f"ngoài miền / {total_values:,} giá trị."
    )


# Neighbourhoods: kiểm tra chuỗi rỗng
for column in ["neighbourhood_group", "neighbourhood"]:
    if column in neighbourhoods.columns:
        empty_count = int(
            neighbourhoods[column]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
            .sum()
        )

        add_baseline(
            dimension="Out of domain",
            table_name="Neighbourhoods",
            field_name=column,
            check_name="Empty string validation",
            observed_value=empty_count,
            total_records=len(neighbourhoods),
            percentage=round(
                empty_count / len(neighbourhoods) * 100, 4
            ) if len(neighbourhoods) else 0,
            status="WARN" if empty_count else "PASS",
            note="Số giá trị chuỗi rỗng."
        )
# Listings.room_type: kiểm tra miền giá trị
allowed_room_types = {
    "Entire home/apt",
    "Private room",
    "Shared room",
    "Hotel room",
}

room_values = listings["room_type"]
non_null_mask = room_values.notna()
invalid_mask = (
    non_null_mask
    & ~room_values.isin(allowed_room_types)
)

invalid_count = int(invalid_mask.sum())
total_non_null = int(non_null_mask.sum())

add_baseline(
    dimension="Out of domain",
    table_name="Listings",
    field_name="room_type",
    check_name="Allowed values",
    observed_value=invalid_count,
    total_records=total_non_null,
    percentage=(
        round(invalid_count / total_non_null * 100, 4)
        if total_non_null else None
    ),
    status=(
        "N/A" if total_non_null == 0
        else "WARN" if invalid_count else "PASS"
    ),
    note="Kiểm tra bốn loại phòng; NULL được thống kê riêng."
)
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## Bằng chứng về thời gian, tiền tệ, xuất xứ và khóa Reviews

Đối chiếu snapshot với ngày thực tế, tiền tệ từ JSON và checksum.
Chuẩn hóa xuống dòng chỉ trong bộ nhớ; giữ nguyên file nguồn.
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
import json
import hashlib

# Khoang ngay thuc te, tach biet voi snapshot trong inventory
time_rows = []
for dataset, dataframe, column in [
    ("Listings", listings, "last_scraped"),
    ("Calendar", calendar, "date"),
    ("Reviews", reviews, "date"),
]:
    parsed = pd.to_datetime(dataframe[column], errors="coerce")
    time_rows.append({
        "dataset": dataset,
        "field": column,
        "min_date": str(parsed.min().date()) if parsed.notna().any() else "N/A",
        "max_date": str(parsed.max().date()) if parsed.notna().any() else "N/A",
        "unparseable_non_null": int(
            (dataframe[column].notna() & parsed.isna()).sum()
        ),
    })
time_evidence_df = pd.DataFrame(time_rows)
display(time_evidence_df)

inventory = pd.read_csv(
    PROJECT_ROOT / "docs" / "source_inventory.csv",
    dtype=str,
    keep_default_na=False,
)
display(inventory[["file_name", "snapshot_date"]])

quote_currency = price_analysis["currency"]
currency_evidence_df = pd.DataFrame({
    "all_listings": quote_currency.value_counts(),
    "listings_with_numeric_listed_price": quote_currency[price_analysis["listed_price_numeric"].notna()].value_counts(),
    "listings_with_valid_sgd_listed_price": quote_currency[price_analysis["listed_price_sgd"].notna()].value_counts(),
}).fillna(0).astype(int)
display(currency_evidence_df)

checksum_rows = []
for _, item in inventory.iterrows():
    filename = item["file_name"]
    source_path = (RAW_DATA_DIR / filename).resolve()
    if source_path.parent != RAW_DATA_DIR.resolve():
        raise ValueError("Inventory chứa đường dẫn ngoài data/raw")
    raw_bytes = source_path.read_bytes()
    observed = hashlib.sha256(raw_bytes).hexdigest()
    # Chỉ chẩn đoán CRLF trên CSV văn bản, tuyệt đối không chuẩn hóa byte gzip.
    lf_hash = (hashlib.sha256(raw_bytes.replace(b"\r\n", b"\n")).hexdigest()
               if source_path.suffix.lower() == ".csv" else None)
    expected = item["sha256"].strip().lower()
    if observed == expected:
        result = "EXACT_MATCH"
    elif lf_hash == expected:
        result = "MATCH_AFTER_CRLF_TO_LF"
    else:
        result = "UNEXPLAINED_MISMATCH"
    checksum_rows.append({
        "file_name": filename,
        "expected_sha256": expected,
        "observed_sha256": observed,
        "sha256_after_crlf_to_lf": lf_hash,
        "result": result,
    })
checksum_evidence_df = pd.DataFrame(checksum_rows)
with pd.option_context("display.max_columns", None, "display.max_colwidth", None):
    display(checksum_evidence_df)

review_id_duplicate_excess = int(reviews.duplicated(["id"], keep="first").sum())
review_pair_duplicate_excess = int(
    reviews.duplicated(["listing_id", "id"], keep="first").sum()
)
review_id_cross_listing_count = int(
    reviews.groupby("id")["listing_id"].nunique().gt(1).sum()
)
review_key_evidence_df = pd.DataFrame([{
    "duplicate_excess_by_id": review_id_duplicate_excess,
    "ids_in_multiple_listings": review_id_cross_listing_count,
    "duplicate_excess_by_listing_id_and_id": review_pair_duplicate_excess,
}])
display(review_key_evidence_df)
audit_summary = (
    f"Đơn vị giá: {price_unit}. Giá chính là Listings.price, hữu hạn, >0 và SGD xác nhận từ JSON; "
    "không phải giá giao dịch hoặc doanh thu thực thu. "
    f"Reviews có {review_id_duplicate_excess:,} dòng dư theo id, "
    f"{review_id_cross_listing_count:,} id xuất hiện ở nhiều listing và "
    f"{review_pair_duplicate_excess:,} dòng dư theo (listing_id, id). "
    "Khóa ghép là khóa khảo sát trên nguồn hiện tại, chưa tự chứng minh "
    "tính đúng đắn nghiệp vụ cho mọi nguồn. Ngày snapshot trong inventory "
    "và khoảng ngày scrape được báo cáo riêng. Checksum khớp sau chuẩn hóa "
    "xuống dòng không được gọi là khớp byte gốc."
)
print(audit_summary)

for item in checksum_rows:
    add_baseline("Provenance", "Raw", item["file_name"], "SHA256 exact bytes",
        int(item["result"] != "EXACT_MATCH"), 1,
        status="PASS" if item["result"] == "EXACT_MATCH" else ("WARN" if item["result"] == "MATCH_AFTER_CRLF_TO_LF" else "FAIL"),
        note=item["result"] + "; không sửa raw hoặc checksum inventory.")
if checksum_evidence_df["result"].eq("UNEXPLAINED_MISMATCH").any():
    raise ValueError("Checksum raw lệch không giải thích được; xác minh nguồn trước khi dùng kết quả.")
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## 7. Phân tích Outliers bằng IQR

Phương pháp IQR được sử dụng để nhận diện các giá trị nằm ngoài
khoảng phân bố thông thường.

- Q1: phân vị 25%.
- Median (Q2): phân vị 50%.
- Q3: phân vị 75%.
- IQR = Q3 - Q1.
- Ngưỡng dưới = Q1 - 1.5 × IQR.
- Ngưỡng trên = Q3 + 1.5 × IQR.

Outliers chỉ được đánh dấu để kiểm tra, không đồng nghĩa với dữ liệu sai.
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
outlier_columns = [
    "accommodates",
    "bedrooms",
    "beds",
    "minimum_nights",
    "maximum_nights",
    "number_of_reviews",
    "reviews_per_month"
]

if price_column:
    outlier_columns.insert(0, price_column)

outlier_rows = []

for column in outlier_columns:
    if column not in listings.columns:
        continue

    values = (price_analysis["listed_price_sgd"] if column == "price"
              else pd.to_numeric(listings[column], errors="coerce"))
    values = values[values.notna() & np.isfinite(values)].astype(float)

    if len(values) == 0:
        continue

    q1 = values.quantile(0.25)
    median = values.quantile(0.50)
    q3 = values.quantile(0.75)

    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outlier_mask = (
        (values < lower_bound) |
        (values > upper_bound)
    )

    outlier_count = int(outlier_mask.sum())

    outlier_percentage = (
        outlier_count / len(values) * 100
    )

    outlier_rows.append({
        "field": column,
        "valid_count": len(values),
        "Q1": q1,
        "Median": median,
        "Q3": q3,
        "IQR": iqr,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "outlier_count": outlier_count,
        "outlier_percentage": round(outlier_percentage, 4)
    })

    add_baseline(
        dimension="Outliers",
        table_name="Listings",
        field_name=column,
        check_name="IQR outlier detection",
        observed_value=outlier_count,
        total_records=len(values),
        percentage=round(outlier_percentage, 4),
        status="WARN" if outlier_count else "PASS",
        note=(
            f"Q1={q1:.4f}; Median={median:.4f}; Q3={q3:.4f}; "
            f"IQR={iqr:.4f}; lower={lower_bound:.4f}; "
            f"upper={upper_bound:.4f}. "
            "Outliers không tự động bị loại bỏ."
        )
    )

outlier_df = pd.DataFrame(outlier_rows)

print("Kết quả nhận diện Outliers:")
display(outlier_df)


# Thống kê riêng giá thuê
if price_column:
    price_values = price_analysis["listed_price_sgd"].dropna().astype(float)

    print(f"Thống kê giá niêm yết Listings.price ({price_unit}):")
    display(
        price_values.describe(
            percentiles=[0.25, 0.5, 0.75, 0.9, 0.95]
        ).to_frame("Price")
    )

# Giá quote chỉ đối chiếu trên cùng tập listing, không thay giá KPI.
price_comparison_df = support.compare_prices(price_analysis)
display(price_comparison_df)
display(price_analysis[["listed_price_sgd", "quote_price_sgd"]].describe())
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## 8. Phân tích phân bố dữ liệu

Các nội dung được khảo sát:

1. Phân bố giá thuê mỗi đêm.
2. Phân bố theo room_type.
3. Phân bố theo neighbourhood_group.
4. Top 15 neighbourhood có nhiều Listings.
5. Phân bố review_scores_rating.
6. Tình trạng available trong Calendar.

Đối với các trường địa lý của Listings, sử dụng:
- `neighbourhood_group_cleansed`
- `neighbourhood_cleansed`
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
# Biểu đồ 1: Phân bố giá thuê
if price_column:
    price_values = price_analysis["listed_price_sgd"].dropna().astype(float)

    plt.figure(figsize=(10, 5))
    plt.hist(price_values, bins=50)
    plt.title("Phân bố giá niêm yết Listings.price")
    plt.xlabel(f"Giá niêm yết Listings.price ({price_unit})")
    plt.ylabel("Số lượng Listings")
    plt.tight_layout()
    plt.show()


# Biểu đồ 2: room_type
if "room_type" in listings.columns:
    room_counts = (
        listings["room_type"]
        .fillna("NULL")
        .value_counts()
    )

    plt.figure(figsize=(9, 5))
    room_counts.plot(kind="bar")
    plt.title("Phân bố Listings theo room_type")
    plt.xlabel("room_type")
    plt.ylabel("Số lượng Listings")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.show()

    display(room_counts.to_frame("Số lượng"))


# Biểu đồ 3: neighbourhood_group_cleansed
group_column = "neighbourhood_group_cleansed"

if group_column in listings.columns:
    group_counts = (
        listings[group_column]
        .fillna("NULL")
        .value_counts()
    )

    plt.figure(figsize=(9, 5))
    group_counts.plot(kind="bar")
    plt.title("Phân bố Listings theo neighbourhood group")
    plt.xlabel("Neighbourhood group")
    plt.ylabel("Số lượng Listings")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.show()

    display(group_counts.to_frame("Số lượng"))


# Biểu đồ 4: Top 15 neighbourhood
neighbourhood_column = "neighbourhood_cleansed"

if neighbourhood_column in listings.columns:
    neighbourhood_counts = (
        listings[neighbourhood_column]
        .fillna("NULL")
        .value_counts()
        .head(15)
        .sort_values()
    )

    plt.figure(figsize=(10, 7))
    neighbourhood_counts.plot(kind="barh")
    plt.title("Top 15 neighbourhood có nhiều Listings nhất")
    plt.xlabel("Số lượng Listings")
    plt.ylabel("Neighbourhood")
    plt.tight_layout()
    plt.show()

    display(
        neighbourhood_counts.sort_values(
            ascending=False
        ).to_frame("Số lượng")
    )


# Biểu đồ 5: review_scores_rating
if "review_scores_rating" in listings.columns:
    review_scores = pd.to_numeric(
        listings["review_scores_rating"],
        errors="coerce"
    ).dropna()

    plt.figure(figsize=(10, 5))
    plt.hist(review_scores, bins=30)
    plt.title("Phân bố review_scores_rating")
    plt.xlabel("Review score")
    plt.ylabel("Số lượng Listings")
    plt.tight_layout()
    plt.show()

    display(review_scores.describe().to_frame("Review score"))


# Biểu đồ 6: available trong Calendar
if "available" in calendar.columns:
    available_counts = (
        calendar["available"]
        .fillna("NULL")
        .astype(str)
        .value_counts()
    )

    plt.figure(figsize=(8, 5))
    available_counts.plot(kind="bar")
    plt.title("Phân bố tình trạng available trong Calendar")
    plt.xlabel("Available")
    plt.ylabel("Số lượng bản ghi")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.show()

    display(available_counts.to_frame("Số lượng"))
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## 9. Kiểm tra tính toàn vẹn tham chiếu

Kiểm tra các quan hệ:

- Calendar.listing_id → Listings.id.
- Reviews.listing_id → Listings.id.
- Listings.neighbourhood_group_cleansed và
  Listings.neighbourhood_cleansed đối chiếu với
  Neighbourhoods.neighbourhood_group và Neighbourhoods.neighbourhood.

Ngoài ra, kiểm tra độ bao phủ của các bảng và nguy cơ JOIN fan-out.
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
listing_ids = set(listings["id"].dropna())


# 9.1. Calendar -> Listings
calendar_orphan_rows = int(
    (~calendar["listing_id"].isin(listing_ids)).sum()
)

add_baseline(
    dimension="Referential integrity",
    table_name="Calendar",
    field_name="listing_id -> Listings.id",
    check_name="Orphan listing_id",
    observed_value=calendar_orphan_rows,
    total_records=len(calendar),
    percentage=round(
        calendar_orphan_rows / len(calendar) * 100, 4
    ) if len(calendar) else 0,
    status="WARN" if calendar_orphan_rows else "PASS",
    note="Số dòng Calendar có listing_id không tồn tại trong Listings."
)

print(
    "Calendar orphan rows:",
    f"{calendar_orphan_rows:,}"
)


# 9.2. Reviews -> Listings
review_orphan_rows = int(
    (~reviews["listing_id"].isin(listing_ids)).sum()
)

add_baseline(
    dimension="Referential integrity",
    table_name="Reviews",
    field_name="listing_id -> Listings.id",
    check_name="Orphan listing_id",
    observed_value=review_orphan_rows,
    total_records=len(reviews),
    percentage=round(
        review_orphan_rows / len(reviews) * 100, 4
    ) if len(reviews) else 0,
    status="WARN" if review_orphan_rows else "PASS",
    note="Số dòng Reviews có listing_id không tồn tại trong Listings."
)

print(
    "Reviews orphan rows:",
    f"{review_orphan_rows:,}"
)


# 9.3. Listings -> Neighbourhoods
listing_group_column = "neighbourhood_group_cleansed"
listing_neighbourhood_column = "neighbourhood_cleansed"

dimension_group_column = "neighbourhood_group"
dimension_neighbourhood_column = "neighbourhood"

required_listing_columns = [
    listing_group_column,
    listing_neighbourhood_column
]

required_dimension_columns = [
    dimension_group_column,
    dimension_neighbourhood_column
]

if (
    all(c in listings.columns for c in required_listing_columns)
    and all(c in neighbourhoods.columns for c in required_dimension_columns)
):
    listing_neighbourhoods = (
        listings[
            required_listing_columns
        ]
        .dropna()
        .drop_duplicates()
        .rename(columns={
            listing_group_column: dimension_group_column,
            listing_neighbourhood_column: dimension_neighbourhood_column
        })
    )

    source_neighbourhoods = (
        neighbourhoods[
            required_dimension_columns
        ]
        .dropna()
        .drop_duplicates()
    )

    comparison = listing_neighbourhoods.merge(
        source_neighbourhoods,
        on=required_dimension_columns,
        how="left",
        indicator=True
    )

    unmatched_count = int(
        (comparison["_merge"] == "left_only").sum()
    )

    total_pairs = len(comparison)

    unmatched_percentage = (
        unmatched_count / total_pairs * 100
        if total_pairs else 0
    )

    add_baseline(
        dimension="Referential integrity",
        table_name="Listings",
        field_name=(
            "neighbourhood_group_cleansed + "
            "neighbourhood_cleansed"
        ),
        check_name="Neighbourhood matching",
        observed_value=unmatched_count,
        total_records=total_pairs,
        percentage=round(unmatched_percentage, 4),
        status="WARN" if unmatched_count else "PASS",
        note=(
            "Số cặp khu vực trong Listings không tìm thấy "
            "trong bảng Neighbourhoods."
        )
    )

    print(
        "Neighbourhood unmatched pairs:",
        f"{unmatched_count:,}/{total_pairs:,}"
    )

    if unmatched_count:
        display(
            comparison[
                comparison["_merge"] == "left_only"
            ]
        )

else:
    print(
        "[WARN] Không đủ cột để đối chiếu Neighbourhoods."
    )


# 9.4. Độ bao phủ của Listings trong Calendar và Reviews
calendar_listing_count = len(set(calendar["listing_id"].dropna()) & listing_ids)
review_listing_count = len(set(reviews["listing_id"].dropna()) & listing_ids)

listing_count = listings["id"].nunique()

calendar_coverage = (
    calendar_listing_count / listing_count * 100
    if listing_count else 0
)

review_coverage = (
    review_listing_count / listing_count * 100
    if listing_count else 0
)

coverage_df = pd.DataFrame([
    {
        "relationship": "Listings -> Calendar",
        "listing_count": listing_count,
        "child_listing_count": calendar_listing_count,
        "coverage_percentage": round(calendar_coverage, 4)
    },
    {
        "relationship": "Listings -> Reviews",
        "listing_count": listing_count,
        "child_listing_count": review_listing_count,
        "coverage_percentage": round(review_coverage, 4)
    }
])

display(coverage_df)

add_baseline(
    dimension="Data coverage",
    table_name="Calendar",
    field_name="listing_id",
    check_name="Listing coverage",
    observed_value=calendar_listing_count,
    total_records=listing_count,
    percentage=round(calendar_coverage, 4),
    status="INFO",
    note="Tỷ lệ listing xuất hiện trong Calendar."
)

add_baseline(
    dimension="Data coverage",
    table_name="Reviews",
    field_name="listing_id",
    check_name="Listing coverage",
    observed_value=review_listing_count,
    total_records=listing_count,
    percentage=round(review_coverage, 4),
    status="INFO",
    note="Tỷ lệ listing có ít nhất một review."
)


# 9.5. JOIN fan-out
calendar_counts = (
    calendar.groupby("listing_id")
    .size()
)

review_counts = (
    reviews.groupby("listing_id")
    .size()
)

fanout = pd.DataFrame({
    "calendar_rows": calendar_counts,
    "review_rows": review_counts
}).fillna(0)

fanout["potential_join_rows"] = (
    fanout["calendar_rows"] * fanout["review_rows"]
)

estimated_join_rows = int(
    fanout["potential_join_rows"].sum()
)

direct_join_estimate = int(
    listings["id"].map(calendar_counts).fillna(0)
    .mul(
        listings["id"].map(review_counts).fillna(0)
    )
    .sum()
)

print(
    "Số dòng Calendar:",
    f"{len(calendar):,}"
)

print(
    "Số dòng Reviews:",
    f"{len(reviews):,}"
)

print(
    "Ước lượng số dòng khi JOIN Calendar và Reviews "
    "trực tiếp theo listing_id:",
    f"{direct_join_estimate:,}"
)

add_baseline(
    dimension="JOIN fan-out",
    table_name="Listings - Calendar - Reviews",
    field_name="listing_id",
    check_name="Estimated join rows",
    observed_value=direct_join_estimate,
    total_records=len(listings),
    percentage=None,
    status="INFO",
    note=(
        "Ước lượng số dòng sau khi JOIN Calendar và Reviews "
        "theo listing_id. Nên tổng hợp bảng con trước khi JOIN."
    )
)
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## 10. Xuất Data Quality Baseline và Cleaning Recommendations

Tổng hợp kết quả kiểm tra vào `data_quality_baseline.csv`.

Các khuyến nghị được lưu riêng để làm cơ sở cho bước xử lý dữ liệu
tiếp theo. Notebook không thực hiện làm sạch dữ liệu.
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## 9.1. Số lượng review và đối chiếu hai nguồn

Trung vị `Listings.number_of_reviews` theo khu vực/loại phòng, kèm mẫu số.
Đối chiếu số khóa `(listing_id,id)` phân biệt, khóa số nguyên dương và ngày hợp lệ
trong toàn bộ file Reviews. Không đồng nhất số bản ghi file với số review Listings.
Xuất bảng đầy đủ 1 dòng/listing và bảng tất cả nhóm; không sửa raw.
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
review_comparison_df, review_summary_df, review_groups_df = support.reconcile_reviews(listings, reviews)
review_comparison_df.to_csv(TEST_DIR / "review_reconciliation.csv", index=False, encoding="utf-8-sig")
review_groups_df.to_csv(EDA_DOCS_DIR / "review_group_summary.csv", index=False, encoding="utf-8-sig")
display(review_summary_df)
display(review_groups_df)
differences = review_comparison_df.query("comparison_status == 'DIFFERENT'")
display(differences.sort_values("difference_listing_minus_file", key=lambda s: s.abs(), ascending=False).head(20))
review_summary = review_summary_df.iloc[0]
review_note = (
    f"{int(review_summary['matched_listings']):,}/{len(listings):,} listing khớp; "
    f"{int(review_summary['different_listings']):,} lệch; "
    f"{int(review_summary['missing_or_invalid_listings_count']):,} thiếu/sai số review ở Listings. "
    f"File có {int(review_summary['valid_review_rows']):,} dòng khóa/ngày hợp lệ và "
    f"{int(review_summary['unique_review_keys']):,} khóa (listing_id,id) phân biệt. "
    "Đối chiếu toàn bộ ngày review trong file với một snapshot Listings; không lọc theo năm. "
    "0 ở observed_review_records nghĩa là không tìm thấy trong file; NULL từ Listings giữ NULL. "
    "Chênh lệch chưa chứng minh nguồn nào sai; cần xác minh phạm vi/lịch sử cập nhật từ nguồn, không ép bằng nhau.")
print(review_note)
add_baseline("Reconciliation", "Listings - Reviews", "number_of_reviews", "Listings count minus file distinct review keys",
    len(differences), len(listings), status="WARN" if len(differences) else "PASS", note=review_note)
add_baseline("Reconciliation", "Listings", "number_of_reviews", "Missing or invalid review count",
    int(review_summary["missing_or_invalid_listings_count"]), len(listings),
    status="WARN" if review_summary["missing_or_invalid_listings_count"] else "PASS", note="Giữ NULL; không ép thành 0.")
for dimension in ["neighbourhood_cleansed", "room_type"]:
    grouped = review_groups_df.loc[review_groups_df["group_dimension"].eq(dimension)].sort_values("median_listing_review_count")
    # Tất cả nhóm đều có trong CSV; biểu đồ khu vực hiển thị top 15 theo trung vị.
    plotted = grouped.tail(15) if dimension == "neighbourhood_cleansed" else grouped
    plt.figure(figsize=(10, 7 if dimension == "neighbourhood_cleansed" else 4))
    plt.barh(plotted["group_value"].fillna("NULL").astype(str), plotted["median_listing_review_count"])
    plt.title("Trung vị Listings.number_of_reviews — " + ("top 15 khu vực" if dimension == "neighbourhood_cleansed" else "theo loại phòng"))
    plt.xlabel("Số review / listing (gồm listing có 0 review; NULL không điền 0)")
    plt.tight_layout(); plt.show()
'''))

    cells.append(nbformat.v4.new_code_cell(r'''
# 10.1. Xuất baseline
baseline_df = pd.DataFrame(baseline_rows)

baseline_df.to_csv(
    BASELINE_PATH,
    index=False,
    encoding="utf-8-sig"
)

print("Đã xuất data_quality_baseline.csv:")
print(BASELINE_PATH)

with pd.option_context(
    "display.max_rows", None,
    "display.max_columns", None,
    "display.max_colwidth", None,
):
    display(baseline_df)


# 10.2. Cleaning recommendations
recommendation_rows = [
    {
        "dataset": "Listings",
        "issue": "NULL",
        "recommendation": (
            "Đánh giá ý nghĩa từng trường trước khi quyết định "
            "giữ nguyên, loại bỏ hoặc thay thế NULL."
        ),
        "priority": "High",
        "note": (
            "Không thay thế NULL đồng loạt vì mỗi trường "
            "có ý nghĩa nghiệp vụ khác nhau."
        )
    },
    {
        "dataset": "Listings",
        "issue": "Outliers",
        "recommendation": (
            "Kiểm tra các giá trị ngoài ngưỡng IQR kết hợp "
            "với ngữ cảnh nghiệp vụ."
        ),
        "priority": "Medium",
        "note": (
            "Outliers không đồng nghĩa với dữ liệu sai; "
            "không tự động loại bỏ."
        )
    },
    {
        "dataset": "Calendar",
        "issue": "Data volume",
        "recommendation": (
            "Tổng hợp dữ liệu Calendar theo listing_id "
            "trước khi kết hợp với bảng có quan hệ một-nhiều khác."
        ),
        "priority": "High",
        "note": (
            "Calendar có nhiều bản ghi cho một listing."
        )
    },
    {
        "dataset": "Reviews",
        "issue": "Duplicates",
        "recommendation": (
            "Kiểm tra riêng id và cặp (listing_id, id); giải thích grain quan sát."
        ),
        "priority": "High",
        "note": (
            "Báo cáo id riêng lẻ và khóa ghép; không tự động xóa theo id."
        )
    },
    {
        "dataset": "Listings - Calendar - Reviews",
        "issue": "JOIN fan-out",
        "recommendation": (
            "Tổng hợp Calendar và Reviews theo listing_id "
            "trước khi JOIN nếu cần một dòng trên mỗi listing."
        ),
        "priority": "High",
        "note": (
            "JOIN trực tiếp các bảng một-nhiều có thể "
            "làm nhân bản số dòng."
        )
    },
    {
        "dataset": "Listings - Neighbourhoods",
        "issue": "Referential integrity",
        "recommendation": (
            "Đối chiếu theo cặp neighbourhood_group_cleansed "
            "và neighbourhood_cleansed."
        ),
        "priority": "Medium",
        "note": (
            "Bảng Neighbourhoods sử dụng neighbourhood_group "
            "và neighbourhood."
        )
    }
]


# Khuyen nghi lay truc tiep tu baseline, khong hard-code so lieu
for item in baseline_rows:
    dimension = item["quality_dimension"]
    field = item["field_or_key"]
    is_target = item["dataset"] == "Listings" and (
        (dimension == "NULL" and field in {
            "price", "review_scores_rating"
        })
        or (dimension == "Outliers" and field == "price")
    )
    if not is_target:
        continue
    count = int(item["observed_value"])
    total = int(item["total_records"])
    percentage = item["percentage"]
    recommendation_rows.append({
        "dataset": "Listings",
        "issue": f"{dimension}: {field}",
        "recommendation": (
            "Giữ nguyên để xem xét theo ngữ cảnh; không tự động xóa."
            if dimension == "Outliers" else
            "Không điền 0 thay cho dữ liệu thiếu; ghi rõ mẫu số có dữ liệu khi phân tích."
        ),
        "priority": "Medium" if dimension == "Outliers" else "High",
        "note": f"{count:,}/{total:,} bản ghi ({percentage:.4f}%). {item['note']}",
    })
recommendation_rows.append({
    "dataset": "Reviews",
    "issue": "ID riêng lẻ và khóa ghép",
    "recommendation": (
        "Báo cáo riêng duplicate theo id và (listing_id, id); không tự động "
        "xóa theo id riêng lẻ. Khóa ghép là khóa khảo sát trên nguồn hiện tại."
    ),
    "priority": "High",
    "note": (
        f"Dòng dư theo id: {review_id_duplicate_excess:,}; "
        f"id ở nhiều listing: {review_id_cross_listing_count:,}; "
        f"dòng dư theo khóa ghép: {review_pair_duplicate_excess:,}."
    ),
})
recommendation_rows.append({
    "dataset": "All sources",
    "issue": "Thời gian, tiền tệ và checksum",
    "recommendation": (
        "Giữ nguyên raw và inventory; báo cáo checksum byte gốc và kết quả "
        "chuẩn hóa CRLF thành LF riêng biệt. Nếu vẫn lệch, xác minh lại nguồn."
    ),
    "priority": "High",
    "note": audit_summary,
})

recommendation_rows.extend([
    {"dataset": "Listings - Reviews", "issue": "Review count reconciliation", "recommendation": "Giữ hai chỉ tiêu riêng; xác minh phạm vi nguồn nếu lệch, không ghi đè số đếm.", "priority": "High", "note": review_note},
    {"dataset": "Listings", "issue": "Rating domain", "recommendation": "Dùng 1–5 thống nhất với KPI; NULL không điền 0.", "priority": "Medium", "note": "Đây là miền quan sát snapshot, chưa có xác minh metadata chính thức."},
    {"dataset": "Listings", "issue": "Price sample", "recommendation": "KPI và EDA dùng price >0, hữu hạn, currency SGD từ JSON; quote là đối chiếu trên cùng tập listing.", "priority": "High", "note": str(price_comparison_df.iloc[0].to_dict())},
])
recommendations_df = pd.DataFrame(recommendation_rows)

recommendations_df.to_csv(
    RECOMMENDATIONS_CSV_PATH,
    index=False,
    encoding="utf-8-sig"
)

display(recommendations_df)


# 10.3. Xuất file Markdown
def dataframe_to_markdown(dataframe):
    columns = list(dataframe.columns)

    header = "| " + " | ".join(columns) + " |"

    separator = "| " + " | ".join(
        ["---"] * len(columns)
    ) + " |"

    rows = []

    for _, row in dataframe.iterrows():
        values = []

        for value in row:
            value = str(value)
            value = value.replace("|", "\\|")
            value = value.replace("\n", " ")
            values.append(value)

        rows.append("| " + " | ".join(values) + " |")

    return "\n".join([header, separator] + rows)


markdown_content = f"""
# Khuyến nghị xử lý dữ liệu – Task 2.3

## 1. Mục đích

Tài liệu tổng hợp các vấn đề chất lượng dữ liệu được ghi nhận
trong quá trình EDA của bộ dữ liệu Singapore Airbnb.

## 2. Nguyên tắc

- Không tự động xóa NULL.
- Không xóa Duplicates khi chưa xác định đúng grain.
- Không tự động xóa Outliers chỉ dựa trên IQR.
- Giữ nguyên dữ liệu nguồn trong quá trình EDA.

## 3. Các khuyến nghị

{dataframe_to_markdown(recommendations_df)}

## 4. Lưu ý

### NULL
Xem xét ý nghĩa của từng trường trước khi quyết định xử lý.

### Duplicates
Kiểm tra theo grain của từng bảng. Đối với Reviews,
sử dụng cặp listing_id và id.

### Outliers
Đối chiếu các giá trị ngoài ngưỡng IQR với ngữ cảnh nghiệp vụ.

### Referential integrity
Kiểm tra các khóa tham chiếu giữa Listings, Calendar,
Reviews và Neighbourhoods.

### JOIN fan-out
Tổng hợp dữ liệu Calendar và Reviews theo listing_id
trước khi JOIN nếu cần một dòng trên mỗi listing.

### Thời gian, tiền tệ và xuất xứ

{audit_summary}

#### Khoảng ngày thực tế

{dataframe_to_markdown(time_evidence_df)}

#### Snapshot theo inventory

{dataframe_to_markdown(inventory[["file_name", "snapshot_date"]])}

#### Bằng chứng tiền tệ từ JSON nguồn

{dataframe_to_markdown(currency_evidence_df.rename_axis("currency").reset_index())}

#### Đối chiếu checksum

{dataframe_to_markdown(checksum_evidence_df)}

NULL được thống kê theo cách đọc mặc định của Pandas, bao gồm các
chuỗi như NA, N/A và None được nhận diện là thiếu. Không tự động
coi đây là lý do xóa bản ghi.

## 5. Bằng chứng bổ sung

### Giá niêm yết và quote trên cùng mẫu

{dataframe_to_markdown(price_comparison_df)}

### Số lượng review

{review_note}

{dataframe_to_markdown(review_summary_df)}

Bảng đầy đủ: `tests/review_reconciliation.csv` và `docs/eda/review_group_summary.csv`.

{dataframe_to_markdown(review_groups_df)}

### Rating

Miền 1–5 là miền quan sát và quy tắc thống nhất với KPI, chưa xác minh metadata chính thức.

## 6. Kết luận

Các kết quả trong data_quality_baseline.csv là cơ sở
để xác định những trường và quan hệ dữ liệu cần được xem xét
trong bước xử lý tiếp theo.

Tài liệu này chỉ đưa ra khuyến nghị, không thực hiện làm sạch
dữ liệu nguồn.
"""

RECOMMENDATIONS_MD_PATH.write_text(
    markdown_content,
    encoding="utf-8"
)

print("Đã xuất cleaning_recommendations.md:")
print(RECOMMENDATIONS_MD_PATH)
'''))

    cells.append(nbformat.v4.new_markdown_cell(r'''
## 11. Kết luận

Notebook đã thực hiện khảo sát dữ liệu Singapore Airbnb theo phạm vi
Task 2.3.

Các nội dung đã được xem xét:

- Kích thước và cấu trúc dữ liệu.
- NULL và Duplicates.
- Giá trị ngoài miền hợp lệ.
- Outliers theo phương pháp IQR.
- Phân bố giá thuê, room_type, neighbourhood,
  review_scores_rating và available.
- Tính toàn vẹn tham chiếu.
- Độ bao phủ giữa các bảng.
- Nguy cơ JOIN fan-out.

Các kết quả được lưu trong:

- `tests/data_quality_baseline.csv`
- `docs/eda/cleaning_recommendations.csv`
- `docs/eda/cleaning_recommendations.md`

Đây là bước đánh giá chất lượng dữ liệu, không phải bước làm sạch.
'''))

    notebook.cells = cells
    nbformat.write(notebook, NOTEBOOK_PATH)
    _ok(f"Đã tạo notebook: {NOTEBOOK_PATH}")
    return NOTEBOOK_PATH


def execute_notebook(notebook_path):
    _header("3. THỰC THI NOTEBOOK")

    try:
        notebook = nbformat.read(
            notebook_path,
            as_version=4
        )

        client = NotebookClient(
            notebook,
            timeout=600,
            kernel_name=KERNEL_NAME,
            resources={
                "metadata": {
                    "path": str(PROJECT_ROOT)
                }
            },
            allow_errors=False
        )

        executed_notebook = client.execute()

        # Ghi lại notebook sau khi thực thi.
        nbformat.write(
            executed_notebook,
            notebook_path
        )

        _ok("Notebook đã chạy hoàn tất.")
        _ok("Output đã được lưu trực tiếp vào notebook.")
        _ok("Các biểu đồ đã được lưu trong notebook.")

        return True

    except Exception as error:
        _fail(f"Không thể thực thi notebook: {error}")
        traceback.print_exc()
        return False


# ============================================================
# 6. KIỂM TRA ĐẦU RA
# ============================================================

def check_outputs():
    _header("4. KIỂM TRA SẢN PHẨM ĐẦU RA")

    expected_outputs = [
        NOTEBOOK_PATH,
        BASELINE_PATH,
        RECOMMENDATIONS_CSV_PATH,
        RECOMMENDATIONS_MD_PATH,
        TEST_DIR / "review_reconciliation.csv",
        EDA_DOCS_DIR / "review_group_summary.csv"
    ]

    all_exist = True

    for output_path in expected_outputs:
        if output_path.exists() and output_path.stat().st_size > 0:
            _ok(
                f"{output_path.relative_to(PROJECT_ROOT)} "
                f"({output_path.stat().st_size:,} bytes)"
            )
        else:
            _fail(f"Chưa tạo được: {output_path}")
            all_exist = False

    return all_exist


# ============================================================
# 7. MAIN
# ============================================================

def main():
    import argparse
    global KERNEL_NAME
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", default="python3", help="Tên kernelspec đang có trên máy")
    parser.add_argument("--generate-only", action="store_true", help="Chỉ tạo notebook, chưa thực thi hay xác nhận output")
    args = parser.parse_args()
    KERNEL_NAME = args.kernel
    _set_console_encoding()

    _header(
        "TASK 2.3 – EDA: MISSING, DUPLICATES, OUTLIERS VÀ PHÂN BỐ"
    )

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Raw data: {RAW_DATA_DIR}")
    print(f"Notebook: {NOTEBOOK_PATH}")
    print(f"Kernel: {KERNEL_NAME}")

    # Bước 1: Kiểm tra dữ liệu nguồn
    if not check_raw_data():
        _summary()
        return 1

    # Bước 2: Tạo notebook
    try:
        notebook_path = build_notebook()
    except Exception as error:
        _fail(f"Không thể tạo notebook: {error}")
        traceback.print_exc()
        _summary()
        return 1

    if args.generate_only:
        print("Đã tạo notebook chưa chạy; cần Run All hoặc chạy lại không có --generate-only.")
        return 0

    # Bước 3: Thực thi notebook
    if not execute_notebook(notebook_path):
        _summary()
        return 1

    # Bước 4: Kiểm tra đầu ra
    outputs_ok = check_outputs()

    _summary()

    if outputs_ok and _fail_count == 0:
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
