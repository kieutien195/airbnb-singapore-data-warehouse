"""
task_2_4_2_5_mapping_and_schema.py
Thực hiện và kiểm chứng tự động cho:
- Task 2.4: Quy tắc cleaning, source-to-target mapping và danh sách kiểm thử (ETL Test Checklist).
- Task 2.5: Xác định Grain, Dimension, Fact, Schema Draft và kiểm chứng độ tương thích nguồn -> đích trên dữ liệu thật.

Đầu ra:
1. docs/source_to_target_mapping.csv
2. docs/warehouse_schema_columns.csv
3. tests/etl_test_checklist.csv
4. tests/task_2_4_2_5_verification.csv
"""

from pathlib import Path
import json
import sys
import pandas as pd
import numpy as np
from warehouse_validation import validate_design


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DOCS_DIR = PROJECT_ROOT / "docs"
TESTS_DIR = PROJECT_ROOT / "tests"
DD_ALL_PATH = DOCS_DIR / "data_dictionary" / "data_dictionary_all_sources.csv"
INVENTORY_PATH = DOCS_DIR / "source_inventory.csv"

MAPPING_CSV_PATH = DOCS_DIR / "source_to_target_mapping.csv"
WAREHOUSE_COLS_CSV_PATH = DOCS_DIR / "warehouse_schema_columns.csv"
ETL_TEST_CHECKLIST_PATH = TESTS_DIR / "etl_test_checklist.csv"
VERIFICATION_CSV_PATH = TESTS_DIR / "task_2_4_2_5_verification.csv"


def _set_console_encoding():
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")


# ==============================================================================
# 1. ĐỊNH NGHĨA CHI TIẾT MAPPING CHO TẤT CẢ 103 CỘT NGUỒN
#    (Đã hiệu chỉnh 100% các góp ý trong docs/feedback.md)
# ==============================================================================

LISTINGS_SPECS = {
    "id": (
        "listing_id", "BIGINT UNSIGNED", "KEEP_CLEANED",
        "dim_listing; fact_listing_snapshot", "listing_id", "BIGINT UNSIGNED",
        "Business Key", "NOT NULL",
        "Ép kiểu số nguyên dương BIGINT UNSIGNED; kết hợp với snapshot_date làm khóa tự nhiên (listing_id, snapshot_date).",
        "REJECT_ROW_IF_NULL", "id IS NOT NULL AND id > 0",
        "KPI-01; KPI-02; KPI-03; KPI-05; SUP-01; TQ-01; TQ-02; TQ-03; TQ-04"
    ),
    "listing_url": (
        "listing_url", "VARCHAR(255)", "KEEP_CLEANED",
        "dim_listing", "listing_url", "VARCHAR(255)",
        "Descriptive Attribute", "NOT NULL",
        "Cắt khoảng trắng đầu/cuối (TRIM); kiểm tra tiền tố URL hợp lệ.",
        "KEEP_NULL", "LENGTH(TRIM(listing_url)) <= 255",
        "Descriptive / Truy vết nguồn"
    ),
    "scrape_id": (
        "scrape_id", "BIGINT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "scrape_id", "BIGINT UNSIGNED",
        "Audit / Metadata", "NOT NULL",
        "Ép kiểu BIGINT UNSIGNED; dùng đối chiếu phiên bản thu thập của snapshot.",
        "REJECT_ROW_IF_NULL", "scrape_id IS NOT NULL AND scrape_id > 0",
        "KPI-01; TQ-01; TQ-04"
    ),
    "last_scraped": (
        "last_scraped_date", "DATE", "KEEP_CLEANED",
        "dim_listing", "last_scraped_date", "DATE",
        "Audit / Metadata", "NOT NULL",
        "Parse chuỗi YYYY-MM-DD sang kiểu DATE; báo lỗi nếu không parse được.",
        "REJECT_ROW_IF_NULL", "VALID_DATE(last_scraped) BETWEEN '2026-09-25' AND '2026-09-26'",
        "KPI-01; TQ-04"
    ),
    "source": (
        "source_type", "VARCHAR(50)", "KEEP_CLEANED",
        "dim_listing", "source_type", "VARCHAR(50)",
        "Descriptive Attribute", "NULL",
        "TRIM chuỗi; chuyển chuỗi rỗng thành NULL; giữ nguyên giá trị hợp lệ (ví dụ 'previous scrape').",
        "KEEP_NULL", "source_type IS NULL OR LENGTH(source_type) <= 50",
        "Descriptive / EDA"
    ),
    "name": (
        "listing_name", "VARCHAR(300)", "KEEP_CLEANED",
        "dim_listing", "listing_name", "VARCHAR(300)",
        "Descriptive Attribute", "NOT NULL",
        "TRIM khoảng trắng thừa và chuẩn hóa ký tự xuống dòng trong tên tin đăng.",
        "KEEP_NULL_OR_UNKNOWN", "LENGTH(listing_name) <= 300",
        "Descriptive / Power BI Tooltip"
    ),
    "description": (
        "description_text", "TEXT", "KEEP_AUDIT_ONLY",
        "N/A (Silver only)", "", "",
        "Excluded in Gold (Long Text)", "NULL",
        "Giữ dạng TEXT UTF-8 ở Staging/Silver; không nạp vào Gold để tối ưu bộ nhớ MySQL & Power BI; không dùng suy diễn điểm review.",
        "KEEP_NULL", "UTF8MB4_VALID",
        "Descriptive / Silver Audit"
    ),
    "neighborhood_overview": (
        "neighborhood_overview", "TEXT", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100% (3,208/3,208 NULL); giữ kiểu TEXT ở Staging (không suy từ float64 sang DECIMAL), lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "picture_url": (
        "picture_url", "VARCHAR(500)", "KEEP_CLEANED",
        "dim_listing", "picture_url", "VARCHAR(500)",
        "Descriptive Attribute", "NULL",
        "TRIM chuỗi URL ảnh đại diện; chuyển chuỗi rỗng thành NULL.",
        "KEEP_NULL", "picture_url IS NULL OR LENGTH(picture_url) <= 500",
        "Descriptive / Power BI"
    ),
    "host_id": (
        "host_id", "BIGINT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "host_id", "BIGINT UNSIGNED",
        "Descriptive Attribute", "NOT NULL",
        "Ép kiểu BIGINT UNSIGNED; lưu thuộc tính chủ nhà denormalized trong dim_listing theo chuẩn Star Schema.",
        "REJECT_ROW_IF_NULL", "host_id IS NOT NULL AND host_id > 0",
        "Descriptive / Host Analytics"
    ),
    "host_url": (
        "host_url", "VARCHAR(255)", "KEEP_AUDIT_ONLY",
        "N/A (Silver only)", "", "",
        "Excluded in Gold (Redundant URL)", "NULL",
        "TRIM chuỗi URL; giữ ở Staging/Silver vì có thể tái tạo từ host_id.",
        "KEEP_NULL", "LENGTH(host_url) <= 255",
        "Descriptive / Silver Audit"
    ),
    "host_profile_id": (
        "host_profile_id", "BIGINT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "host_profile_id", "BIGINT UNSIGNED",
        "Descriptive Attribute", "NULL",
        "Ép kiểu BIGINT UNSIGNED vì giá trị lên tới ~1.46e18 (vượt miền INT 32-bit).",
        "KEEP_NULL", "host_profile_id IS NULL OR host_profile_id > 0",
        "Descriptive"
    ),
    "host_profile_url": (
        "host_profile_url", "VARCHAR(255)", "KEEP_AUDIT_ONLY",
        "N/A (Silver only)", "", "",
        "Excluded in Gold (Redundant URL)", "NULL",
        "TRIM chuỗi URL; giữ ở Staging/Silver.",
        "KEEP_NULL", "LENGTH(host_profile_url) <= 255",
        "Descriptive / Silver Audit"
    ),
    "host_name": (
        "host_name", "VARCHAR(150)", "KEEP_CLEANED",
        "dim_listing", "host_name", "VARCHAR(150)",
        "Descriptive Attribute", "NOT NULL",
        "TRIM khoảng trắng thừa của tên chủ nhà.",
        "KEEP_NULL", "LENGTH(host_name) <= 150",
        "Descriptive / Host Analytics"
    ),
    "host_since": (
        "host_since_date", "DATE", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100% (3,208/3,208 NULL); định nghĩa kiểu chuẩn là DATE (không suy float64 sang DECIMAL); lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "hosts_time_as_user_years": (
        "hosts_time_as_user_years", "SMALLINT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "hosts_time_as_user_years", "SMALLINT UNSIGNED",
        "Descriptive Attribute", "NULL",
        "Ép kiểu số nguyên không âm SMALLINT UNSIGNED.",
        "KEEP_NULL", "hosts_time_as_user_years >= 0",
        "Descriptive"
    ),
    "hosts_time_as_user_months": (
        "hosts_time_as_user_months", "TINYINT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "hosts_time_as_user_months", "TINYINT UNSIGNED",
        "Descriptive Attribute", "NULL",
        "Ép kiểu số nguyên không âm TINYINT UNSIGNED (0–11).",
        "KEEP_NULL", "hosts_time_as_user_months BETWEEN 0 AND 11",
        "Descriptive"
    ),
    "hosts_time_as_host_years": (
        "hosts_time_as_host_years", "SMALLINT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "hosts_time_as_host_years", "SMALLINT UNSIGNED",
        "Descriptive Attribute", "NULL",
        "Ép kiểu số nguyên không âm SMALLINT UNSIGNED.",
        "KEEP_NULL", "hosts_time_as_host_years >= 0",
        "Descriptive"
    ),
    "hosts_time_as_host_months": (
        "hosts_time_as_host_months", "TINYINT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "hosts_time_as_host_months", "TINYINT UNSIGNED",
        "Descriptive Attribute", "NULL",
        "Ép kiểu số nguyên không âm TINYINT UNSIGNED (0–11).",
        "KEEP_NULL", "hosts_time_as_host_months BETWEEN 0 AND 11",
        "Descriptive"
    ),
    "host_location": (
        "host_location", "VARCHAR(150)", "KEEP_CLEANED",
        "dim_listing", "host_location", "VARCHAR(150)",
        "Descriptive Attribute", "NULL",
        "TRIM chuỗi; chuyển chuỗi rỗng thành NULL; giữ nguyên NULL (1,322 dòng thiếu).",
        "KEEP_NULL", "host_location IS NULL OR LENGTH(host_location) <= 150",
        "Descriptive"
    ),
    "host_about": (
        "host_about_text", "TEXT", "KEEP_AUDIT_ONLY",
        "N/A (Silver only)", "", "",
        "Excluded in Gold (Long Text)", "NULL",
        "Giữ dạng TEXT ở Staging/Silver; không đưa vào Gold.",
        "KEEP_NULL", "UTF8MB4_VALID",
        "Descriptive / Silver Audit"
    ),
    "host_response_time": (
        "host_response_time", "VARCHAR(50)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100%; kiểu nghiệp vụ đúng là chuỗi phân loại VARCHAR(50), tuyệt đối không suy từ float64 sang DECIMAL.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "host_response_rate": (
        "host_response_rate", "DECIMAL(5,2)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100%; giữ NULL ở Staging, lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "host_acceptance_rate": (
        "host_acceptance_rate", "DECIMAL(5,2)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100%; giữ NULL ở Staging, lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "host_is_superhost": (
        "host_is_superhost", "TINYINT(1)", "KEEP_CLEANED",
        "dim_listing", "host_is_superhost", "TINYINT(1)",
        "Descriptive Attribute", "NULL",
        "Ánh xạ cờ boolean: 't'/'true'/'1' -> 1 (TRUE), 'f'/'false'/'0' -> 0 (FALSE), giữ NULL nếu thiếu.",
        "KEEP_NULL", "host_is_superhost IN (0, 1) OR host_is_superhost IS NULL",
        "Descriptive / Host Analytics"
    ),
    "host_thumbnail_url": (
        "host_thumbnail_url", "VARCHAR(500)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100%; kiểu nghiệp vụ đúng là VARCHAR(500) (không suy từ float64 sang DECIMAL); lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "host_picture_url": (
        "host_picture_url", "VARCHAR(500)", "KEEP_AUDIT_ONLY",
        "N/A (Silver only)", "", "",
        "Excluded in Gold (Redundant URL)", "NULL",
        "TRIM chuỗi URL ảnh chủ nhà; giữ ở Staging/Silver.",
        "KEEP_NULL", "host_picture_url IS NULL OR LENGTH(host_picture_url) <= 500",
        "Descriptive / Silver Audit"
    ),
    "host_neighbourhood": (
        "host_neighbourhood", "VARCHAR(100)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100%; kiểu nghiệp vụ đúng là VARCHAR(100) (không suy từ float64 sang DECIMAL); lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "host_listings_count": (
        "host_listings_count", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "host_listings_count", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra >= 0.",
        "KEEP_NULL", "host_listings_count >= 0",
        "Host Scale Analysis"
    ),
    "host_total_listings_count": (
        "host_total_listings_count", "INT UNSIGNED", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100%; kiểu nghiệp vụ đúng là INT UNSIGNED (không phải DECIMAL); lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "host_verifications": (
        "host_verifications", "VARCHAR(255)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100%; kiểu nghiệp vụ đúng là chuỗi danh sách VARCHAR/TEXT (không phải DECIMAL); lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "host_has_profile_pic": (
        "host_has_profile_pic", "TINYINT(1)", "KEEP_CLEANED",
        "dim_listing", "host_has_profile_pic", "TINYINT(1)",
        "Descriptive Attribute", "NULL",
        "Ánh xạ cờ boolean: 't'/'true'/'1' -> 1, 'f'/'false'/'0' -> 0, giữ NULL nếu thiếu.",
        "KEEP_NULL", "host_has_profile_pic IN (0, 1) OR host_has_profile_pic IS NULL",
        "Descriptive"
    ),
    "host_identity_verified": (
        "host_identity_verified", "TINYINT(1)", "KEEP_CLEANED",
        "dim_listing", "host_identity_verified", "TINYINT(1)",
        "Descriptive Attribute", "NULL",
        "Ánh xạ cờ boolean: 't'/'true'/'1' -> 1, 'f'/'false'/'0' -> 0, giữ NULL nếu thiếu.",
        "KEEP_NULL", "host_identity_verified IN (0, 1) OR host_identity_verified IS NULL",
        "Descriptive"
    ),
    "neighbourhood": (
        "neighbourhood_raw", "VARCHAR(100)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100% (3,208/3,208 NULL); kiểu nghiệp vụ là VARCHAR(100) (không phải DECIMAL); dùng neighbourhood_cleansed thay thế.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (Use neighbourhood_cleansed)"
    ),
    "neighbourhood_cleansed": (
        "neighbourhood_name", "VARCHAR(100)", "KEEP_CLEANED",
        "dim_listing; fact_listing_snapshot", "neighbourhood_sk (lookup via dim_neighbourhood)", "INT UNSIGNED",
        "Foreign Key", "NOT NULL",
        "TRIM chuỗi; kết hợp với neighbourhood_group_cleansed để tra cứu surrogate key neighbourhood_sk trong dim_neighbourhood.",
        "REJECT_ROW_IF_NULL", "EXISTS IN dim_neighbourhood(neighbourhood_group, neighbourhood_name)",
        "KPI-03; RQ1; RQ2; RQ3; RQ4; TQ-03"
    ),
    "neighbourhood_group_cleansed": (
        "neighbourhood_group", "VARCHAR(50)", "KEEP_CLEANED",
        "dim_listing; fact_listing_snapshot", "neighbourhood_sk (lookup via dim_neighbourhood)", "INT UNSIGNED",
        "Foreign Key", "NOT NULL",
        "TRIM chuỗi; kết hợp với neighbourhood_cleansed để tra cứu surrogate key neighbourhood_sk trong dim_neighbourhood.",
        "REJECT_ROW_IF_NULL", "EXISTS IN dim_neighbourhood(neighbourhood_group, neighbourhood_name)",
        "RQ1; RQ2; RQ3; RQ4; TQ-03"
    ),
    "latitude": (
        "latitude", "DECIMAL(10,7)", "KEEP_CLEANED",
        "dim_listing", "latitude", "DECIMAL(10,7)",
        "Descriptive Attribute", "NOT NULL",
        "Ép kiểu DECIMAL(10,7); kiểm tra tọa độ vĩ độ trong phạm vi Singapore (1.15 đến 1.50).",
        "REJECT_ROW_IF_NULL", "latitude BETWEEN -90 AND 90 (Singapore: 1.15 TO 1.50)",
        "Map Visualization / RQ1"
    ),
    "longitude": (
        "longitude", "DECIMAL(10,7)", "KEEP_CLEANED",
        "dim_listing", "longitude", "DECIMAL(10,7)",
        "Descriptive Attribute", "NOT NULL",
        "Ép kiểu DECIMAL(10,7); kiểm tra tọa độ kinh độ trong phạm vi Singapore (103.60 đến 104.10).",
        "REJECT_ROW_IF_NULL", "longitude BETWEEN -180 AND 180 (Singapore: 103.60 TO 104.10)",
        "Map Visualization / RQ1"
    ),
    "property_type": (
        "property_type", "VARCHAR(100)", "KEEP_CLEANED",
        "dim_listing", "property_type", "VARCHAR(100)",
        "Descriptive Attribute", "NOT NULL",
        "TRIM khoảng trắng thừa; chuẩn hóa chuỗi mô tả loại bất động sản.",
        "KEEP_NULL", "LENGTH(property_type) <= 100",
        "Descriptive / RQ1"
    ),
    "room_type": (
        "room_type", "VARCHAR(50)", "KEEP_CLEANED",
        "dim_listing", "room_type", "VARCHAR(50)",
        "Descriptive Attribute", "NOT NULL",
        "TRIM chuỗi; kiểm tra thuộc 4 danh mục chuẩn: 'Private room', 'Entire home/apt', 'Hotel room', 'Shared room'.",
        "REJECT_ROW_IF_NULL", "room_type IN ('Private room', 'Entire home/apt', 'Hotel room', 'Shared room')",
        "KPI-03; RQ1; RQ2; RQ3; RQ4; TQ-04"
    ),
    "accommodates": (
        "accommodates", "INT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "accommodates", "INT UNSIGNED",
        "Descriptive Attribute", "NOT NULL",
        "Giữ kiểu số nguyên dương INT UNSIGNED (sức chứa khách tối đa, miền quan sát 1–16); tuyệt đối KHÔNG parse thành DATE.",
        "REJECT_ROW_IF_NULL", "accommodates BETWEEN 1 AND 50",
        "Descriptive / TQ-04 (Fixed feedback bug)"
    ),
    "bathrooms": (
        "bathrooms", "DECIMAL(4,1)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100%; thông tin phòng tắm thực tế nằm ở bathrooms_text; lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (Use bathrooms_text)"
    ),
    "bathrooms_text": (
        "bathrooms_text", "VARCHAR(100)", "KEEP_CLEANED",
        "dim_listing", "bathrooms_text", "VARCHAR(100)",
        "Descriptive Attribute", "NULL",
        "TRIM chuỗi; chuyển chuỗi rỗng thành NULL; giữ NULL ở 10 dòng thiếu.",
        "KEEP_NULL", "bathrooms_text IS NULL OR LENGTH(bathrooms_text) <= 100",
        "Descriptive"
    ),
    "bedrooms": (
        "bedrooms", "INT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "bedrooms", "INT UNSIGNED",
        "Descriptive Attribute", "NULL",
        "Chuyển từ float64 (do có 2 NULL) sang số nguyên nullable INT UNSIGNED (0 dòng có phần thập phân); giữ NULL.",
        "KEEP_NULL", "bedrooms IS NULL OR bedrooms >= 0",
        "Descriptive"
    ),
    "beds": (
        "beds", "INT UNSIGNED", "KEEP_CLEANED",
        "dim_listing", "beds", "INT UNSIGNED",
        "Descriptive Attribute", "NULL",
        "Chuyển từ float64 (do có 154 NULL) sang số nguyên nullable INT UNSIGNED (0 dòng có phần thập phân); giữ NULL.",
        "KEEP_NULL", "beds IS NULL OR beds >= 0",
        "Descriptive"
    ),
    "amenities": (
        "amenities_json", "TEXT", "KEEP_AUDIT_ONLY",
        "N/A (Silver only)", "", "",
        "Excluded in Gold (JSON Array Text)", "NULL",
        "Giữ chuỗi JSON danh sách tiện nghi ở Staging/Silver; không nạp vào Gold.",
        "KEEP_NULL", "VALID_JSON_ARRAY",
        "Descriptive / Silver Audit"
    ),
    "price": (
        "listed_price_raw_amount; listed_price_sgd", "DECIMAL(12,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "listed_price_raw_amount; listed_price_sgd", "DECIMAL(12,2)",
        "Fact Measure", "NULL",
        "Loại bỏ '$' và ',' rồi ép kiểu DECIMAL(12,2) vào listed_price_raw_amount (2,728 dòng). Đối chiếu quote.currency='SGD' từ price_quote_raw để gán listed_price_sgd (2,725 dòng, 3 dòng thiếu currency trong JSON gán NULL cho listed_price_sgd). Không thay NULL bằng 0; không tự xóa outlier.",
        "KEEP_NULL", "listed_price_sgd IS NULL OR listed_price_sgd > 0",
        "KPI-02; RQ2"
    ),
    "price_quote_checkin_date": (
        "price_quote_checkin_date", "DATE", "KEEP_CLEANED",
        "fact_listing_snapshot", "price_quote_checkin_date", "DATE",
        "Audit / Metadata", "NULL",
        "Parse chuỗi YYYY-MM-DD sang kiểu DATE (không phải tiền tệ/DECIMAL); giữ NULL ở 318 dòng thiếu.",
        "KEEP_NULL", "price_quote_checkin_date IS NULL OR VALID_DATE",
        "Price Quote Context (Fixed feedback bug)"
    ),
    "price_quote_checkout_date": (
        "price_quote_checkout_date", "DATE", "KEEP_CLEANED",
        "fact_listing_snapshot", "price_quote_checkout_date", "DATE",
        "Audit / Metadata", "NULL",
        "Parse chuỗi YYYY-MM-DD sang kiểu DATE (không phải tiền tệ/DECIMAL); kiểm tra >= price_quote_checkin_date; giữ NULL ở 318 dòng.",
        "KEEP_NULL", "price_quote_checkout_date IS NULL OR price_quote_checkout_date >= price_quote_checkin_date",
        "Price Quote Context (Fixed feedback bug)"
    ),
    "price_quote_total_price": (
        "price_quote_total_price", "DECIMAL(14,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "price_quote_total_price", "DECIMAL(14,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(14,2); giữ NULL ở 483 dòng thiếu.",
        "KEEP_NULL", "price_quote_total_price IS NULL OR price_quote_total_price > 0",
        "Price Verification"
    ),
    "price_quote_price_per_night": (
        "price_quote_price_per_night", "DECIMAL(12,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "price_quote_price_per_night", "DECIMAL(12,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(12,2); đối chiếu khớp 100% với listed_price_sgd trên 2,725 dòng có currency='SGD'; giữ NULL ở 483 dòng.",
        "KEEP_NULL", "price_quote_price_per_night IS NULL OR price_quote_price_per_night > 0",
        "KPI-02; RQ2"
    ),
    "price_quote_raw": (
        "quote_currency; is_price_sgd_verified", "CHAR(3); TINYINT(1)", "KEEP_CLEANED",
        "fact_listing_snapshot", "quote_currency; is_price_sgd_verified", "CHAR(3); TINYINT(1)",
        "Audit / Metadata", "NULL",
        "Giữ nguyên chuỗi JSON ở Staging/Silver; parse JSON trích quote.currency -> quote_currency ('SGD' ở 2,855 dòng; NULL ở 353 dòng) và bật cờ is_price_sgd_verified=1 khi có giá hợp lệ kèm quote.currency='SGD' (2,725 dòng).",
        "KEEP_NULL", "VALID_JSON_OR_NULL",
        "KPI-02 Currency Verification (Fixed feedback bug)"
    ),
    "minimum_nights": (
        "minimum_nights", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "minimum_nights", "INT UNSIGNED",
        "Fact Measure", "NULL",
        "Chuyển từ float64 sang số nguyên nullable INT UNSIGNED (0 dòng có phần thập phân); giữ NULL ở 197 dòng.",
        "KEEP_NULL", "minimum_nights IS NULL OR minimum_nights > 0",
        "Stay Length Analysis / TQ-04"
    ),
    "maximum_nights": (
        "maximum_nights", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "maximum_nights", "INT UNSIGNED",
        "Fact Measure", "NULL",
        "Chuyển từ float64 sang số nguyên nullable INT UNSIGNED (0 dòng có phần thập phân); giữ NULL ở 197 dòng.",
        "KEEP_NULL", "maximum_nights IS NULL OR maximum_nights > 0",
        "Stay Length Analysis / TQ-04"
    ),
    "minimum_minimum_nights": (
        "minimum_minimum_nights", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "minimum_minimum_nights", "INT UNSIGNED",
        "Fact Measure", "NULL",
        "Chuyển từ float64 sang số nguyên nullable INT UNSIGNED; giữ NULL ở 197 dòng.",
        "KEEP_NULL", "minimum_minimum_nights IS NULL OR minimum_minimum_nights > 0",
        "Stay Length Analysis"
    ),
    "maximum_minimum_nights": (
        "maximum_minimum_nights", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "maximum_minimum_nights", "INT UNSIGNED",
        "Fact Measure", "NULL",
        "Chuyển từ float64 sang số nguyên nullable INT UNSIGNED; giữ NULL ở 197 dòng.",
        "KEEP_NULL", "maximum_minimum_nights IS NULL OR maximum_minimum_nights > 0",
        "Stay Length Analysis"
    ),
    "minimum_maximum_nights": (
        "minimum_maximum_nights", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "minimum_maximum_nights", "INT UNSIGNED",
        "Fact Measure", "NULL",
        "Chuyển từ float64 sang số nguyên nullable INT UNSIGNED; giữ NULL ở 197 dòng.",
        "KEEP_NULL", "minimum_maximum_nights IS NULL OR minimum_maximum_nights > 0",
        "Stay Length Analysis"
    ),
    "maximum_maximum_nights": (
        "maximum_maximum_nights", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "maximum_maximum_nights", "INT UNSIGNED",
        "Fact Measure", "NULL",
        "Chuyển từ float64 sang số nguyên nullable INT UNSIGNED; giữ NULL ở 197 dòng.",
        "KEEP_NULL", "maximum_maximum_nights IS NULL OR maximum_maximum_nights > 0",
        "Stay Length Analysis"
    ),
    "minimum_nights_avg_ntm": (
        "minimum_nights_avg_ntm", "DECIMAL(10,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "minimum_nights_avg_ntm", "DECIMAL(10,2)",
        "Fact Measure", "NOT NULL",
        "Giữ kiểu số thập phân DECIMAL(10,2) vì có 320/3,208 dòng mang phần thập phân; không ép sang INT.",
        "REJECT_ROW_IF_NULL", "minimum_nights_avg_ntm > 0",
        "Stay Length Analysis (Fixed feedback bug)"
    ),
    "maximum_nights_avg_ntm": (
        "maximum_nights_avg_ntm", "DECIMAL(10,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "maximum_nights_avg_ntm", "DECIMAL(10,2)",
        "Fact Measure", "NOT NULL",
        "Giữ kiểu số thập phân DECIMAL(10,2) vì có 426/3,208 dòng mang phần thập phân; không ép sang INT.",
        "REJECT_ROW_IF_NULL", "maximum_nights_avg_ntm > 0",
        "Stay Length Analysis (Fixed feedback bug)"
    ),
    "calendar_updated": (
        "calendar_updated", "VARCHAR(50)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100% (3,208/3,208 NULL); giữ NULL ở Staging, lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "has_availability": (
        "has_availability", "TINYINT(1)", "KEEP_CLEANED",
        "dim_listing", "has_availability", "TINYINT(1)",
        "Descriptive Attribute", "NULL",
        "Ánh xạ cờ boolean: 't'/'true'/'1' -> 1, 'f'/'false'/'0' -> 0; giữ nguyên NULL ở 42 dòng thiếu.",
        "KEEP_NULL", "has_availability IN (0, 1) OR has_availability IS NULL",
        "Descriptive (Fixed feedback bug)"
    ),
    "availability_30": (
        "availability_30", "SMALLINT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "availability_30", "SMALLINT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu SMALLINT UNSIGNED; kiểm tra miền hợp lệ 0–30.",
        "REJECT_ROW_IF_NULL", "availability_30 BETWEEN 0 AND 30",
        "Availability Snapshot Metrics"
    ),
    "availability_60": (
        "availability_60", "SMALLINT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "availability_60", "SMALLINT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu SMALLINT UNSIGNED; kiểm tra miền hợp lệ 0–60.",
        "REJECT_ROW_IF_NULL", "availability_60 BETWEEN 0 AND 60",
        "Availability Snapshot Metrics"
    ),
    "availability_90": (
        "availability_90", "SMALLINT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "availability_90", "SMALLINT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu SMALLINT UNSIGNED; kiểm tra miền hợp lệ 0–90.",
        "REJECT_ROW_IF_NULL", "availability_90 BETWEEN 0 AND 90",
        "Availability Snapshot Metrics"
    ),
    "availability_365": (
        "availability_365", "SMALLINT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "availability_365", "SMALLINT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu SMALLINT UNSIGNED; kiểm tra miền hợp lệ 0–365.",
        "REJECT_ROW_IF_NULL", "availability_365 BETWEEN 0 AND 365",
        "Availability Snapshot Metrics"
    ),
    "calendar_last_scraped": (
        "calendar_last_scraped_date", "DATE", "KEEP_CLEANED",
        "dim_listing", "calendar_last_scraped_date", "DATE",
        "Audit / Metadata", "NOT NULL",
        "Parse chuỗi YYYY-MM-DD sang DATE.",
        "REJECT_ROW_IF_NULL", "VALID_DATE(calendar_last_scraped)",
        "Audit / Metadata"
    ),
    "number_of_reviews": (
        "number_of_reviews", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "number_of_reviews", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; giữ giá trị 0 hợp lệ (1,369 dòng bằng 0); không thay NULL bằng 0 nếu phát sinh.",
        "REJECT_ROW_IF_NULL", "number_of_reviews >= 0",
        "SUP-01; RQ4"
    ),
    "number_of_reviews_ltm": (
        "number_of_reviews_ltm", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "number_of_reviews_ltm", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra >= 0.",
        "REJECT_ROW_IF_NULL", "number_of_reviews_ltm >= 0",
        "RQ4 Supporting Metric"
    ),
    "number_of_reviews_l30d": (
        "number_of_reviews_l30d", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "number_of_reviews_l30d", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra >= 0.",
        "REJECT_ROW_IF_NULL", "number_of_reviews_l30d >= 0",
        "RQ4 Supporting Metric"
    ),
    "availability_eoy": (
        "availability_eoy", "SMALLINT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "availability_eoy", "SMALLINT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu SMALLINT UNSIGNED; kiểm tra miền hợp lệ 0–366.",
        "REJECT_ROW_IF_NULL", "availability_eoy BETWEEN 0 AND 366",
        "Availability Snapshot Metrics"
    ),
    "number_of_reviews_ly": (
        "number_of_reviews_ly", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "number_of_reviews_ly", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra >= 0.",
        "REJECT_ROW_IF_NULL", "number_of_reviews_ly >= 0",
        "RQ4 Supporting Metric"
    ),
    "estimated_occupancy_l365d": (
        "estimated_occupancy_l365d", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "estimated_occupancy_l365d", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; lưu kèm cảnh báo đây chỉ là ước tính mô hình của Inside Airbnb, không phải số đêm đặt phòng thực tế.",
        "KEEP_NULL", "estimated_occupancy_l365d BETWEEN 0 AND 365",
        "Source Estimate Only (Caveat in feedback.md)"
    ),
    "estimated_revenue_l365d": (
        "estimated_revenue_l365d", "DECIMAL(14,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "estimated_revenue_l365d", "DECIMAL(14,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(14,2); giữ NULL ở 480 dòng thiếu; lưu kèm cảnh báo đây chỉ là ước tính của nguồn, không phải doanh thu thực.",
        "KEEP_NULL", "estimated_revenue_l365d IS NULL OR estimated_revenue_l365d >= 0",
        "Source Estimate Only (Caveat in feedback.md)"
    ),
    "first_review": (
        "first_review_date", "DATE", "KEEP_CLEANED",
        "dim_listing", "first_review_date", "DATE",
        "Descriptive Attribute", "NULL",
        "Parse chuỗi YYYY-MM-DD sang kiểu DATE (không để VARCHAR/TEXT); giữ NULL ở 1,369 listing chưa có review.",
        "KEEP_NULL", "first_review_date IS NULL OR VALID_DATE",
        "Descriptive / RQ4 (Fixed feedback bug)"
    ),
    "last_review": (
        "last_review_date", "DATE", "KEEP_CLEANED",
        "dim_listing", "last_review_date", "DATE",
        "Descriptive Attribute", "NULL",
        "Parse chuỗi YYYY-MM-DD sang kiểu DATE (không để VARCHAR/TEXT); kiểm tra >= first_review_date; giữ NULL ở 1,369 listing chưa có review.",
        "KEEP_NULL", "last_review_date IS NULL OR last_review_date >= first_review_date",
        "Descriptive / RQ4 (Fixed feedback bug)"
    ),
    "review_scores_rating": (
        "review_scores_rating", "DECIMAL(4,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "review_scores_rating", "DECIMAL(4,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(4,2); kiểm tra miền hợp lệ 1.00–5.00; giữ nguyên NULL ở 1,369 dòng (tuyệt đối không thay NULL bằng 0).",
        "KEEP_NULL", "review_scores_rating IS NULL OR review_scores_rating BETWEEN 1.00 AND 5.00",
        "KPI-05; RQ4; TQ-04"
    ),
    "review_scores_accuracy": (
        "review_scores_accuracy", "DECIMAL(4,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "review_scores_accuracy", "DECIMAL(4,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(4,2); kiểm tra miền hợp lệ 1.00–5.00; giữ nguyên NULL ở 1,369 dòng.",
        "KEEP_NULL", "review_scores_accuracy IS NULL OR review_scores_accuracy BETWEEN 1.00 AND 5.00",
        "RQ4 Sub-score"
    ),
    "review_scores_cleanliness": (
        "review_scores_cleanliness", "DECIMAL(4,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "review_scores_cleanliness", "DECIMAL(4,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(4,2); kiểm tra miền hợp lệ 1.00–5.00; giữ nguyên NULL ở 1,369 dòng.",
        "KEEP_NULL", "review_scores_cleanliness IS NULL OR review_scores_cleanliness BETWEEN 1.00 AND 5.00",
        "RQ4 Sub-score"
    ),
    "review_scores_checkin": (
        "review_scores_checkin", "DECIMAL(4,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "review_scores_checkin", "DECIMAL(4,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(4,2); kiểm tra miền hợp lệ 1.00–5.00; giữ nguyên NULL ở 1,369 dòng.",
        "KEEP_NULL", "review_scores_checkin IS NULL OR review_scores_checkin BETWEEN 1.00 AND 5.00",
        "RQ4 Sub-score"
    ),
    "review_scores_communication": (
        "review_scores_communication", "DECIMAL(4,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "review_scores_communication", "DECIMAL(4,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(4,2); kiểm tra miền hợp lệ 1.00–5.00; giữ nguyên NULL ở 1,369 dòng.",
        "KEEP_NULL", "review_scores_communication IS NULL OR review_scores_communication BETWEEN 1.00 AND 5.00",
        "RQ4 Sub-score"
    ),
    "review_scores_location": (
        "review_scores_location", "DECIMAL(4,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "review_scores_location", "DECIMAL(4,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(4,2); kiểm tra miền hợp lệ 1.00–5.00; giữ nguyên NULL ở 1,370 dòng.",
        "KEEP_NULL", "review_scores_location IS NULL OR review_scores_location BETWEEN 1.00 AND 5.00",
        "RQ4 Sub-score"
    ),
    "review_scores_value": (
        "review_scores_value", "DECIMAL(4,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "review_scores_value", "DECIMAL(4,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(4,2); kiểm tra miền hợp lệ 1.00–5.00; giữ nguyên NULL ở 1,370 dòng.",
        "KEEP_NULL", "review_scores_value IS NULL OR review_scores_value BETWEEN 1.00 AND 5.00",
        "RQ4 Sub-score"
    ),
    "license": (
        "license", "VARCHAR(150)", "KEEP_CLEANED",
        "dim_listing", "license", "VARCHAR(150)",
        "Descriptive Attribute", "NULL",
        "TRIM khoảng trắng và ký tự xuống dòng; giữ NULL ở 1,471 dòng thiếu.",
        "KEEP_NULL", "license IS NULL OR LENGTH(license) <= 150",
        "Descriptive"
    ),
    "instant_bookable": (
        "instant_bookable", "TINYINT(1)", "KEEP_RAW_ONLY_ALL_NULL",
        "N/A (100% NULL in snapshot)", "", "",
        "Excluded in Gold (100% NULL)", "NULL",
        "Cột trống 100% (3,208/3,208 NULL); kiểu nghiệp vụ là boolean TINYINT(1) (không phải DECIMAL); lược bỏ ở Gold.",
        "KEEP_NULL", "ALL_NULL_OBSERVED",
        "Excluded (100% NULL)"
    ),
    "calculated_host_listings_count": (
        "calculated_host_listings_count", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "calculated_host_listings_count", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra >= 0.",
        "REJECT_ROW_IF_NULL", "calculated_host_listings_count >= 0",
        "Host Scale Analysis"
    ),
    "calculated_host_listings_count_entire_homes": (
        "calculated_host_listings_count_entire_homes", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "calculated_host_listings_count_entire_homes", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra >= 0.",
        "REJECT_ROW_IF_NULL", "calculated_host_listings_count_entire_homes >= 0",
        "Host Scale Analysis"
    ),
    "calculated_host_listings_count_private_rooms": (
        "calculated_host_listings_count_private_rooms", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "calculated_host_listings_count_private_rooms", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra >= 0.",
        "REJECT_ROW_IF_NULL", "calculated_host_listings_count_private_rooms >= 0",
        "Host Scale Analysis"
    ),
    "calculated_host_listings_count_shared_rooms": (
        "calculated_host_listings_count_shared_rooms", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_listing_snapshot", "calculated_host_listings_count_shared_rooms", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra >= 0.",
        "REJECT_ROW_IF_NULL", "calculated_host_listings_count_shared_rooms >= 0",
        "Host Scale Analysis"
    ),
    "reviews_per_month": (
        "reviews_per_month", "DECIMAL(8,2)", "KEEP_CLEANED",
        "fact_listing_snapshot", "reviews_per_month", "DECIMAL(8,2)",
        "Fact Measure", "NULL",
        "Ép kiểu DECIMAL(8,2); giữ nguyên NULL ở 1,369 dòng chưa có review.",
        "KEEP_NULL", "reviews_per_month IS NULL OR reviews_per_month >= 0",
        "RQ4 Supporting Metric"
    ),
}

CALENDAR_SPECS = {
    "listing_id": (
        "listing_id", "BIGINT UNSIGNED", "KEEP_CLEANED",
        "fact_calendar", "listing_id; listing_sk (lookup via dim_listing)", "BIGINT UNSIGNED",
        "Business Key / Foreign Key", "NOT NULL",
        "Ép kiểu BIGINT UNSIGNED; kiểm tra tồn tại trong dim_listing cùng snapshot_date; ánh xạ sang listing_sk và neighbourhood_sk.",
        "REJECT_ROW_IF_NULL_OR_ORPHAN", "listing_id > 0 AND EXISTS IN Listings.id",
        "KPI-04; RQ3; TQ-01; TQ-02; TQ-03; TQ-04"
    ),
    "date": (
        "calendar_date", "DATE", "KEEP_CLEANED",
        "fact_calendar", "calendar_date; calendar_date_sk (YYYYMMDD)", "DATE; INT",
        "Business Key / Foreign Key", "NOT NULL",
        "Parse chuỗi YYYY-MM-DD sang DATE; tạo khóa ngoại calendar_date_sk = YYYYMMDD tham chiếu dim_date.date_sk.",
        "REJECT_ROW_IF_NULL", "VALID_DATE(date) BETWEEN '2026-09-25' AND '2027-09-25'",
        "KPI-04; RQ3; TQ-01; TQ-02; TQ-04"
    ),
    "available": (
        "is_available", "TINYINT(1)", "KEEP_CLEANED",
        "fact_calendar", "is_available", "TINYINT(1)",
        "Fact Measure", "NOT NULL",
        "Chuẩn hóa 't'/'true'/'1' -> 1 (TRUE), 'f'/'false'/'0' -> 0 (FALSE); loại/báo lỗi nếu ngoài miền. Cho phép tính tử số KPI-04 bằng SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END).",
        "REJECT_ROW_IF_NULL", "LOWER(TRIM(available)) IN ('t','f','true','false','1','0')",
        "KPI-04; RQ3; TQ-01; TQ-04"
    ),
    "minimum_nights": (
        "minimum_nights", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_calendar", "minimum_nights", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra > 0.",
        "REJECT_ROW_IF_NULL", "minimum_nights > 0",
        "RQ3 / TQ-04"
    ),
    "maximum_nights": (
        "maximum_nights", "INT UNSIGNED", "KEEP_CLEANED",
        "fact_calendar", "maximum_nights", "INT UNSIGNED",
        "Fact Measure", "NOT NULL",
        "Ép kiểu INT UNSIGNED; kiểm tra > 0 và >= minimum_nights.",
        "REJECT_ROW_IF_NULL", "maximum_nights > 0 AND maximum_nights >= minimum_nights",
        "RQ3 / TQ-04"
    ),
}

REVIEWS_SPECS = {
    "listing_id": (
        "listing_id", "BIGINT UNSIGNED", "KEEP_CLEANED",
        "fact_review", "listing_id; listing_sk (lookup via dim_listing)", "BIGINT UNSIGNED",
        "Business Key / Foreign Key", "NOT NULL",
        "Ép kiểu BIGINT UNSIGNED; thành phần thứ nhất của khóa ghép (listing_id, review_id, snapshot_date); kiểm tra tồn tại trong Listings.id.",
        "REJECT_ROW_IF_NULL_OR_ORPHAN", "listing_id > 0 AND EXISTS IN Listings.id",
        "SUP-02; RQ4; TQ-01; TQ-02; TQ-03; TQ-04"
    ),
    "id": (
        "review_id", "BIGINT UNSIGNED", "KEEP_CLEANED",
        "fact_review", "review_id", "BIGINT UNSIGNED",
        "Business Key (Composite)", "NOT NULL",
        "Đổi tên id -> review_id; ép kiểu BIGINT UNSIGNED; thành phần thứ hai của khóa ghép (listing_id, review_id, snapshot_date). Không kiểm tra unique đơn lẻ vì có 4,809 dòng dư theo id riêng lẻ; không suy cơ chế nghiệp vụ từ việc trùng id.",
        "REJECT_ROW_IF_NULL", "review_id > 0 AND UNIQUE(listing_id, review_id, snapshot_date)",
        "SUP-02; RQ4; TQ-01; TQ-02; TQ-04"
    ),
    "date": (
        "review_date", "DATE", "KEEP_CLEANED",
        "fact_review", "review_date; review_date_sk (YYYYMMDD)", "DATE; INT",
        "Foreign Key", "NOT NULL",
        "Đổi tên date -> review_date; parse YYYY-MM-DD sang DATE; tạo review_date_sk = YYYYMMDD tham chiếu dim_date.date_sk.",
        "REJECT_ROW_IF_NULL", "VALID_DATE(date) BETWEEN '2011-05-04' AND '2026-09-25'",
        "SUP-02; RQ4; TQ-01; TQ-04"
    ),
    "reviewer_id": (
        "reviewer_id", "BIGINT UNSIGNED", "KEEP_CLEANED",
        "fact_review", "reviewer_id", "BIGINT UNSIGNED",
        "Degenerate Attribute", "NOT NULL",
        "Ép kiểu BIGINT UNSIGNED; kiểm tra > 0.",
        "REJECT_ROW_IF_NULL", "reviewer_id > 0",
        "RQ4 / TQ-04"
    ),
    "reviewer_name": (
        "reviewer_name", "VARCHAR(150)", "KEEP_CLEANED",
        "fact_review", "reviewer_name", "VARCHAR(150)",
        "Degenerate Attribute", "NOT NULL",
        "TRIM khoảng trắng thừa của tên người đánh giá.",
        "KEEP_NULL_OR_UNKNOWN", "LENGTH(reviewer_name) <= 150",
        "Descriptive"
    ),
    "comments": (
        "comments_text; has_comment; comment_length", "TEXT; TINYINT(1); INT UNSIGNED", "KEEP_CLEANED",
        "fact_review", "has_comment; comment_length", "TINYINT(1); INT UNSIGNED",
        "Fact Measure / Flag", "NULL (raw); NOT NULL (flags)",
        "Giữ văn bản gốc ở Staging/Silver (chuẩn hóa CRLF/HTML <br/>); trong fact_review trích cờ has_comment (1 nếu không NULL/rỗng, 0 nếu thiếu - có 17 dòng NULL) và comment_length. Không dùng comments để suy diễn điểm review.",
        "KEEP_NULL", "has_comment IN (0, 1) AND comment_length >= 0",
        "RQ4 Descriptive"
    ),
}

NEIGHBOURHOODS_SPECS = {
    "neighbourhood_group": (
        "neighbourhood_group", "VARCHAR(50)", "KEEP_CLEANED",
        "dim_neighbourhood", "neighbourhood_group", "VARCHAR(50)",
        "Business Key (Composite)", "NOT NULL",
        "TRIM khoảng trắng đầu/cuối; thành phần thứ nhất của khóa ghép (neighbourhood_group, neighbourhood_name).",
        "REJECT_ROW_IF_NULL_OR_BLANK", "LENGTH(TRIM(neighbourhood_group)) > 0",
        "RQ1; RQ2; RQ3; RQ4; TQ-01; TQ-02; TQ-03; TQ-04"
    ),
    "neighbourhood": (
        "neighbourhood_name", "VARCHAR(100)", "KEEP_CLEANED",
        "dim_neighbourhood", "neighbourhood_name", "VARCHAR(100)",
        "Business Key (Composite)", "NOT NULL",
        "Đổi tên neighbourhood -> neighbourhood_name; TRIM khoảng trắng đầu/cuối; thành phần thứ hai của khóa ghép (neighbourhood_group, neighbourhood_name).",
        "REJECT_ROW_IF_NULL_OR_BLANK", "LENGTH(TRIM(neighbourhood_name)) > 0",
        "KPI-03; RQ1; RQ2; RQ3; RQ4; TQ-01; TQ-02; TQ-03; TQ-04"
    ),
}


def build_source_to_target_mapping(dd_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    spec_map = {
        "Listings": ("stg_listings", LISTINGS_SPECS),
        "Calendar": ("stg_calendar", CALENDAR_SPECS),
        "Reviews": ("stg_reviews", REVIEWS_SPECS),
        "Neighbourhoods": ("stg_neighbourhoods", NEIGHBOURHOODS_SPECS),
    }

    seq = 1
    for _, r in dd_df.iterrows():
        src_name = r["source_name"]
        src_file = r["source_file"]
        col = r["column_name"]
        init_dtype = r["initial_pandas_dtype"]
        null_cnt = int(r["null_count"])
        null_pct = float(r["null_rate_percent"])

        stg_table, specs = spec_map[src_name]
        if col not in specs:
            raise KeyError(f"Thiếu cấu hình mapping cho {src_name}.{col}")

        (
            silver_col, silver_dtype, silver_status,
            gold_table, gold_col, gold_dtype,
            field_cat, gold_nullable,
            transform_rule, null_rule, val_rule, kpi_usage
        ) = specs[col]

        rows.append({
            "mapping_id": f"MAP-{seq:03d}",
            "source_dataset": src_name,
            "source_file": src_file,
            "source_column": col,
            "source_pandas_dtype": init_dtype,
            "source_null_count": null_cnt,
            "source_null_pct": null_pct,
            "staging_table": stg_table,
            "staging_column": col,
            "silver_status": silver_status,
            "silver_column": silver_col,
            "silver_target_dtype": silver_dtype,
            "gold_target_table": gold_table,
            "gold_target_column": gold_col,
            "gold_mysql_dtype": gold_dtype,
            "gold_nullable": gold_nullable,
            "field_category": field_cat,
            "transformation_rule": transform_rule,
            "null_handling_rule": null_rule,
            "validation_rule": val_rule,
            "kpi_and_rq_relevance": kpi_usage,
        })
        seq += 1

    # Bổ sung 4 dòng metadata cột hệ thống (snapshot_date, source_file, ingested_at) cho 4 nguồn
    for src_name, src_file, stg_table, gold_targets in [
        ("Listings", "listings.csv.gz", "stg_listings", "dim_listing; fact_listing_snapshot"),
        ("Calendar", "calendar.csv.gz", "stg_calendar", "fact_calendar"),
        ("Reviews", "reviews.csv.gz", "stg_reviews", "fact_review"),
        ("Neighbourhoods", "neighbourhoods.csv", "stg_neighbourhoods", "dim_neighbourhood"),
    ]:
        rows.append({
            "mapping_id": f"MAP-{seq:03d}",
            "source_dataset": src_name,
            "source_file": src_file,
            "source_column": "[METADATA] snapshot_date",
            "source_pandas_dtype": "metadata (DATE)",
            "source_null_count": 0,
            "source_null_pct": 0.0,
            "staging_table": stg_table,
            "staging_column": "snapshot_date",
            "silver_status": "GENERATED_METADATA",
            "silver_column": "snapshot_date",
            "silver_target_dtype": "DATE",
            "gold_target_table": gold_targets,
            "gold_target_column": "snapshot_date" if src_name == "Neighbourhoods" else "snapshot_date; snapshot_date_sk",
            "gold_mysql_dtype": "DATE" if src_name == "Neighbourhoods" else "DATE; INT",
            "gold_nullable": "NOT NULL",
            "field_category": "Business Key / Snapshot Partition",
            "transformation_rule": "Gán snapshot_date từ source_inventory theo file_name; chỉ sinh snapshot_date_sk cho dim_listing và các fact, không sinh cho dim_neighbourhood.",
            "null_handling_rule": "REJECT_IF_MISSING_IN_INVENTORY",
            "validation_rule": "snapshot_date = '2026-09-23'" if src_name == "Neighbourhoods" else "snapshot_date = '2026-09-23' AND EXISTS IN dim_date",
            "kpi_and_rq_relevance": "All KPIs (Snapshot Grain Control); TQ-02; TQ-05",
        })
        seq += 1

    return pd.DataFrame(rows)


# ==============================================================================
# 2. ĐỊNH NGHĨA SCHEMA CÁC BẢNG GOLD WAREHOUSE (TASK 2.5)
# ==============================================================================

def build_warehouse_schema_columns() -> pd.DataFrame:
    cols = [
        # ---------------- dim_date ----------------
        ("dim_date", "Dimension", 1, "date_sk", "INT", "NOT NULL", "PK", "", "Derived from Calendar/Reviews/Snapshot dates", "Surrogate Key", "Khóa đại diện ngày định dạng số nguyên YYYYMMDD (ví dụ 20260923)."),
        ("dim_date", "Dimension", 2, "full_date", "DATE", "NOT NULL", "UNIQUE (BK)", "", "Derived date range 2011-01-01..2027-12-31", "Natural Key", "Ngày dương lịch chuẩn YYYY-MM-DD."),
        ("dim_date", "Dimension", 3, "day_of_month", "TINYINT UNSIGNED", "NOT NULL", "", "", "DAY(full_date)", "Descriptive Attribute", "Ngày trong tháng (1–31)."),
        ("dim_date", "Dimension", 4, "day_of_week_iso", "TINYINT UNSIGNED", "NOT NULL", "", "", "WEEKDAY(full_date)+1", "Descriptive Attribute", "Thứ trong tuần theo chuẩn ISO (1=Thứ Hai .. 7=Chủ Nhật)."),
        ("dim_date", "Dimension", 5, "day_name", "VARCHAR(15)", "NOT NULL", "", "", "DAYNAME(full_date)", "Descriptive Attribute", "Tên thứ trong tuần (Monday..Sunday)."),
        ("dim_date", "Dimension", 6, "is_weekend", "TINYINT(1)", "NOT NULL", "", "", "day_of_week_iso IN (6,7)", "Descriptive Attribute", "Cờ cuối tuần: 1 nếu Thứ Bảy/Chủ Nhật, 0 nếu ngày thường."),
        ("dim_date", "Dimension", 7, "week_of_year", "TINYINT UNSIGNED", "NOT NULL", "", "", "WEEK(full_date, 3)", "Descriptive Attribute", "Tuần ISO trong năm (1–53)."),
        ("dim_date", "Dimension", 8, "month_num", "TINYINT UNSIGNED", "NOT NULL", "", "", "MONTH(full_date)", "Descriptive Attribute", "Tháng trong năm (1–12)."),
        ("dim_date", "Dimension", 9, "month_name", "VARCHAR(15)", "NOT NULL", "", "", "MONTHNAME(full_date)", "Descriptive Attribute", "Tên tháng (January..December)."),
        ("dim_date", "Dimension", 10, "year_month", "CHAR(7)", "NOT NULL", "", "", "DATE_FORMAT(full_date, '%Y-%m')", "Descriptive Attribute", "Chuỗi Năm-Tháng định dạng YYYY-MM phục vụ trục thời gian BI."),
        ("dim_date", "Dimension", 11, "quarter_num", "TINYINT UNSIGNED", "NOT NULL", "", "", "QUARTER(full_date)", "Descriptive Attribute", "Quý trong năm (1–4)."),
        ("dim_date", "Dimension", 12, "year_quarter", "CHAR(7)", "NOT NULL", "", "", "CONCAT(YEAR, '-Q', QUARTER)", "Descriptive Attribute", "Chuỗi Năm-Quý định dạng YYYY-Q#."),
        ("dim_date", "Dimension", 13, "year_num", "SMALLINT UNSIGNED", "NOT NULL", "", "", "YEAR(full_date)", "Descriptive Attribute", "Năm dương lịch (2011–2027)."),

        # ---------------- dim_neighbourhood ----------------
        ("dim_neighbourhood", "Dimension", 1, "neighbourhood_sk", "INT UNSIGNED", "NOT NULL", "PK (AUTO_INCREMENT)", "", "System generated", "Surrogate Key", "Khóa đại diện khu vực địa lý."),
        ("dim_neighbourhood", "Dimension", 2, "neighbourhood_group", "VARCHAR(50)", "NOT NULL", "UNIQUE (BK part 1)", "", "Neighbourhoods.neighbourhood_group", "Natural Key / Hierarchy", "Nhóm vùng địa lý lớn (5 vùng: Central, East, North, North-East, West Region)."),
        ("dim_neighbourhood", "Dimension", 3, "neighbourhood_name", "VARCHAR(100)", "NOT NULL", "UNIQUE (BK part 2)", "", "Neighbourhoods.neighbourhood", "Natural Key", "Tên khu vực quy hoạch chuẩn hóa (55 khu vực)."),
        ("dim_neighbourhood", "Dimension", 4, "snapshot_date", "DATE", "NOT NULL", "", "", "source_inventory.snapshot_date", "Audit / Metadata", "Ngày snapshot danh mục nguồn (2026-09-23)."),
        ("dim_neighbourhood", "Dimension", 5, "created_at", "DATETIME", "NOT NULL", "", "", "CURRENT_TIMESTAMP", "Audit / Metadata", "Thời điểm nạp bản ghi vào kho."),

        # ---------------- dim_listing ----------------
        ("dim_listing", "Dimension", 1, "listing_sk", "BIGINT UNSIGNED", "NOT NULL", "PK (AUTO_INCREMENT)", "", "System generated", "Surrogate Key", "Khóa đại diện của phiên bản tin đăng tại snapshot."),
        ("dim_listing", "Dimension", 2, "listing_id", "BIGINT UNSIGNED", "NOT NULL", "UNIQUE (BK part 1)", "", "Listings.id", "Natural Key", "Mã định danh tin đăng Airbnb gốc."),
        ("dim_listing", "Dimension", 3, "snapshot_date", "DATE", "NOT NULL", "UNIQUE (BK part 2)", "", "source_inventory.snapshot_date", "Natural Key", "Ngày snapshot của bản ghi tin đăng (hỗ trợ đa snapshot)."),
        ("dim_listing", "Dimension", 4, "snapshot_date_sk", "INT", "NOT NULL", "FK", "dim_date.date_sk", "Derived from snapshot_date", "Foreign Key", "Khóa ngoại tham chiếu dim_date."),
        ("dim_listing", "Dimension", 5, "neighbourhood_sk", "INT UNSIGNED", "NOT NULL", "FK", "dim_neighbourhood.neighbourhood_sk", "Listings.(neighbourhood_group_cleansed, neighbourhood_cleansed)", "Foreign Key", "Khóa ngoại tham chiếu khu vực của tin đăng."),
        ("dim_listing", "Dimension", 6, "scrape_id", "BIGINT UNSIGNED", "NOT NULL", "", "", "Listings.scrape_id", "Audit / Metadata", "Mã phiên thu thập dữ liệu của Inside Airbnb."),
        ("dim_listing", "Dimension", 7, "last_scraped_date", "DATE", "NOT NULL", "", "", "Listings.last_scraped", "Audit / Metadata", "Ngày thu thập thực tế của tin đăng."),
        ("dim_listing", "Dimension", 8, "calendar_last_scraped_date", "DATE", "NOT NULL", "", "", "Listings.calendar_last_scraped", "Audit / Metadata", "Ngày thu thập lịch lần cuối."),
        ("dim_listing", "Dimension", 9, "source_type", "VARCHAR(50)", "NULL", "", "", "Listings.source", "Descriptive Attribute", "Nguồn bản ghi trong scrape (ví dụ 'previous scrape')."),
        ("dim_listing", "Dimension", 10, "listing_name", "VARCHAR(300)", "NOT NULL", "", "", "Listings.name", "Descriptive Attribute", "Tên tiêu đề tin đăng."),
        ("dim_listing", "Dimension", 11, "listing_url", "VARCHAR(255)", "NOT NULL", "", "", "Listings.listing_url", "Descriptive Attribute", "URL trang tin đăng trên Airbnb."),
        ("dim_listing", "Dimension", 12, "picture_url", "VARCHAR(500)", "NULL", "", "", "Listings.picture_url", "Descriptive Attribute", "URL ảnh đại diện tin đăng."),
        ("dim_listing", "Dimension", 13, "property_type", "VARCHAR(100)", "NOT NULL", "", "", "Listings.property_type", "Descriptive Attribute", "Loại hình bất động sản chi tiết."),
        ("dim_listing", "Dimension", 14, "room_type", "VARCHAR(50)", "NOT NULL", "", "", "Listings.room_type", "Descriptive Attribute", "Loại phòng (Entire home/apt, Private room, Hotel room, Shared room) — chiều phân tích chính cho RQ1–RQ4 & KPI-03."),
        ("dim_listing", "Dimension", 15, "accommodates", "INT UNSIGNED", "NOT NULL", "", "", "Listings.accommodates", "Descriptive Attribute", "Sức chứa khách tối đa (số nguyên 1–16)."),
        ("dim_listing", "Dimension", 16, "bedrooms", "INT UNSIGNED", "NULL", "", "", "Listings.bedrooms", "Descriptive Attribute", "Số phòng ngủ (nullable INT)."),
        ("dim_listing", "Dimension", 17, "beds", "INT UNSIGNED", "NULL", "", "", "Listings.beds", "Descriptive Attribute", "Số giường (nullable INT)."),
        ("dim_listing", "Dimension", 18, "bathrooms_text", "VARCHAR(100)", "NULL", "", "", "Listings.bathrooms_text", "Descriptive Attribute", "Mô tả số lượng và loại phòng tắm."),
        ("dim_listing", "Dimension", 19, "latitude", "DECIMAL(10,7)", "NOT NULL", "", "", "Listings.latitude", "Descriptive Attribute", "Vĩ độ địa lý của tin đăng."),
        ("dim_listing", "Dimension", 20, "longitude", "DECIMAL(10,7)", "NOT NULL", "", "", "Listings.longitude", "Descriptive Attribute", "Kinh độ địa lý của tin đăng."),
        ("dim_listing", "Dimension", 21, "has_availability", "TINYINT(1)", "NULL", "", "", "Listings.has_availability", "Descriptive Attribute", "Cờ có thông tin mở lịch (1=True, 0=False, NULL)."),
        ("dim_listing", "Dimension", 22, "license", "VARCHAR(150)", "NULL", "", "", "Listings.license", "Descriptive Attribute", "Mã giấy phép đăng ký lưu trú."),
        ("dim_listing", "Dimension", 23, "host_id", "BIGINT UNSIGNED", "NOT NULL", "", "", "Listings.host_id", "Descriptive Attribute", "Mã định danh chủ nhà (denormalized trong dim_listing)."),
        ("dim_listing", "Dimension", 24, "host_profile_id", "BIGINT UNSIGNED", "NULL", "", "", "Listings.host_profile_id", "Descriptive Attribute", "Mã hồ sơ chủ nhà."),
        ("dim_listing", "Dimension", 25, "host_name", "VARCHAR(150)", "NOT NULL", "", "", "Listings.host_name", "Descriptive Attribute", "Tên hiển thị của chủ nhà."),
        ("dim_listing", "Dimension", 26, "host_location", "VARCHAR(150)", "NULL", "", "", "Listings.host_location", "Descriptive Attribute", "Địa điểm khai báo của chủ nhà."),
        ("dim_listing", "Dimension", 27, "host_is_superhost", "TINYINT(1)", "NULL", "", "", "Listings.host_is_superhost", "Descriptive Attribute", "Cờ chủ nhà Superhost (1=True, 0=False)."),
        ("dim_listing", "Dimension", 28, "host_has_profile_pic", "TINYINT(1)", "NULL", "", "", "Listings.host_has_profile_pic", "Descriptive Attribute", "Cờ chủ nhà có ảnh đại diện (1=True, 0=False)."),
        ("dim_listing", "Dimension", 29, "host_identity_verified", "TINYINT(1)", "NULL", "", "", "Listings.host_identity_verified", "Descriptive Attribute", "Cờ chủ nhà đã xác minh danh tính (1=True, 0=False)."),
        ("dim_listing", "Dimension", 30, "hosts_time_as_user_years", "SMALLINT UNSIGNED", "NULL", "", "", "Listings.hosts_time_as_user_years", "Descriptive Attribute", "Số năm tham gia Airbnb của chủ nhà."),
        ("dim_listing", "Dimension", 31, "hosts_time_as_user_months", "TINYINT UNSIGNED", "NULL", "", "", "Listings.hosts_time_as_user_months", "Descriptive Attribute", "Số tháng lẻ tham gia Airbnb của chủ nhà."),
        ("dim_listing", "Dimension", 32, "hosts_time_as_host_years", "SMALLINT UNSIGNED", "NULL", "", "", "Listings.hosts_time_as_host_years", "Descriptive Attribute", "Số năm làm host."),
        ("dim_listing", "Dimension", 33, "hosts_time_as_host_months", "TINYINT UNSIGNED", "NULL", "", "", "Listings.hosts_time_as_host_months", "Descriptive Attribute", "Số tháng lẻ làm host."),
        ("dim_listing", "Dimension", 34, "first_review_date", "DATE", "NULL", "", "", "Listings.first_review", "Descriptive Attribute", "Ngày đánh giá đầu tiên của tin đăng."),
        ("dim_listing", "Dimension", 35, "last_review_date", "DATE", "NULL", "", "", "Listings.last_review", "Descriptive Attribute", "Ngày đánh giá gần nhất của tin đăng."),
        ("dim_listing", "Dimension", 36, "created_at", "DATETIME", "NOT NULL", "", "", "CURRENT_TIMESTAMP", "Audit / Metadata", "Thời điểm nạp bản ghi vào kho."),

        # ---------------- fact_listing_snapshot ----------------
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 1, "listing_snapshot_sk", "BIGINT UNSIGNED", "NOT NULL", "PK (AUTO_INCREMENT)", "", "System generated", "Surrogate Key", "Khóa đại diện bảng fact_listing_snapshot."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 2, "listing_sk", "BIGINT UNSIGNED", "NOT NULL", "FK; UNIQUE (part 1)", "dim_listing.listing_sk", "Lookup from dim_listing(listing_id, snapshot_date)", "Foreign Key", "Khóa ngoại tham chiếu dim_listing."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 3, "neighbourhood_sk", "INT UNSIGNED", "NOT NULL", "FK", "dim_neighbourhood.neighbourhood_sk", "Lookup from dim_neighbourhood", "Foreign Key", "Khóa ngoại tham chiếu dim_neighbourhood."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 4, "snapshot_date_sk", "INT", "NOT NULL", "FK; UNIQUE (part 2)", "dim_date.date_sk", "Derived from snapshot_date", "Foreign Key", "Khóa ngoại tham chiếu dim_date."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 5, "listing_id", "BIGINT UNSIGNED", "NOT NULL", "UNIQUE (BK part 1)", "", "Listings.id", "Degenerate / Natural Key", "Mã listing gốc phục vụ kiểm tra/đối chiếu nhanh KPI-01."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 6, "snapshot_date", "DATE", "NOT NULL", "UNIQUE (BK part 2)", "", "source_inventory.snapshot_date", "Natural Key", "Ngày snapshot (2026-09-23)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 7, "listed_price_raw_amount", "DECIMAL(12,2)", "NULL", "", "", "Listings.price (stripped $,)", "Non-Additive Fact", "Giá niêm yết dạng số sau khi bỏ ký hiệu tiền tệ (có giá trị ở 2,728 dòng)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 8, "quote_currency", "CHAR(3)", "NULL", "", "", "Listings.price_quote_raw -> quote.currency", "Audit / Metadata", "Mã tiền tệ trích từ JSON báo giá ('SGD' ở 2,855 dòng)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 9, "is_price_sgd_verified", "TINYINT(1)", "NOT NULL", "", "", "1 if listed_price_raw_amount>0 and quote_currency='SGD' else 0", "Audit / Flag", "Cờ xác nhận giá hợp lệ bằng SGD (1 ở 2,725 dòng, 0 ở 483 dòng)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 10, "listed_price_sgd", "DECIMAL(12,2)", "NULL", "", "", "listed_price_raw_amount when is_price_sgd_verified=1", "Non-Additive Fact", "Giá niêm yết mỗi đêm đã xác minh đơn vị SGD (2,725 dòng) — dùng tính trực tiếp KPI-02 (Median = 202.83 SGD)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 11, "price_quote_price_per_night", "DECIMAL(12,2)", "NULL", "", "", "Listings.price_quote_price_per_night", "Non-Additive Fact", "Giá mỗi đêm từ trường báo giá tham chiếu (2,725 dòng)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 12, "price_quote_total_price", "DECIMAL(14,2)", "NULL", "", "", "Listings.price_quote_total_price", "Semi-Additive Fact", "Tổng giá báo tham chiếu cho kỳ lưu trú."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 13, "price_quote_checkin_date", "DATE", "NULL", "", "", "Listings.price_quote_checkin_date", "Audit / Metadata", "Ngày check-in của báo giá tham chiếu."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 14, "price_quote_checkout_date", "DATE", "NULL", "", "", "Listings.price_quote_checkout_date", "Audit / Metadata", "Ngày check-out của báo giá tham chiếu."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 15, "minimum_nights", "INT UNSIGNED", "NULL", "", "", "Listings.minimum_nights", "Non-Additive Fact", "Số đêm lưu trú tối thiểu cấu hình ở cấp listing."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 16, "maximum_nights", "INT UNSIGNED", "NULL", "", "", "Listings.maximum_nights", "Non-Additive Fact", "Số đêm lưu trú tối đa cấu hình ở cấp listing."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 17, "minimum_minimum_nights", "INT UNSIGNED", "NULL", "", "", "Listings.minimum_minimum_nights", "Non-Additive Fact", "Cực tiểu của số đêm lưu trú tối thiểu."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 18, "maximum_minimum_nights", "INT UNSIGNED", "NULL", "", "", "Listings.maximum_minimum_nights", "Non-Additive Fact", "Cực đại của số đêm lưu trú tối thiểu."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 19, "minimum_maximum_nights", "INT UNSIGNED", "NULL", "", "", "Listings.minimum_maximum_nights", "Non-Additive Fact", "Cực tiểu của số đêm lưu trú tối đa."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 20, "maximum_maximum_nights", "INT UNSIGNED", "NULL", "", "", "Listings.maximum_maximum_nights", "Non-Additive Fact", "Cực đại của số đêm lưu trú tối đa."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 21, "minimum_nights_avg_ntm", "DECIMAL(10,2)", "NOT NULL", "", "", "Listings.minimum_nights_avg_ntm", "Non-Additive Fact", "Trung bình số đêm tối thiểu 12 tháng tới (giữ phần thập phân)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 22, "maximum_nights_avg_ntm", "DECIMAL(10,2)", "NOT NULL", "", "", "Listings.maximum_nights_avg_ntm", "Non-Additive Fact", "Trung bình số đêm tối đa 12 tháng tới (giữ phần thập phân)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 23, "availability_30", "SMALLINT UNSIGNED", "NOT NULL", "", "", "Listings.availability_30", "Semi-Additive Fact", "Số đêm mở lịch trong 30 ngày tới."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 24, "availability_60", "SMALLINT UNSIGNED", "NOT NULL", "", "", "Listings.availability_60", "Semi-Additive Fact", "Số đêm mở lịch trong 60 ngày tới."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 25, "availability_90", "SMALLINT UNSIGNED", "NOT NULL", "", "", "Listings.availability_90", "Semi-Additive Fact", "Số đêm mở lịch trong 90 ngày tới."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 26, "availability_365", "SMALLINT UNSIGNED", "NOT NULL", "", "", "Listings.availability_365", "Semi-Additive Fact", "Số đêm mở lịch trong 365 ngày tới."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 27, "availability_eoy", "SMALLINT UNSIGNED", "NOT NULL", "", "", "Listings.availability_eoy", "Semi-Additive Fact", "Số đêm mở lịch đến cuối năm."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 28, "number_of_reviews", "INT UNSIGNED", "NOT NULL", "", "", "Listings.number_of_reviews", "Semi-Additive Fact", "Tổng số đánh giá tích lũy của listing tại snapshot — dùng tính SUP-01."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 29, "number_of_reviews_ltm", "INT UNSIGNED", "NOT NULL", "", "", "Listings.number_of_reviews_ltm", "Semi-Additive Fact", "Số đánh giá trong 12 tháng gần nhất."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 30, "number_of_reviews_l30d", "INT UNSIGNED", "NOT NULL", "", "", "Listings.number_of_reviews_l30d", "Semi-Additive Fact", "Số đánh giá trong 30 ngày gần nhất."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 31, "number_of_reviews_ly", "INT UNSIGNED", "NOT NULL", "", "", "Listings.number_of_reviews_ly", "Semi-Additive Fact", "Số đánh giá trong năm lịch trước."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 32, "reviews_per_month", "DECIMAL(8,2)", "NULL", "", "", "Listings.reviews_per_month", "Non-Additive Fact", "Số đánh giá trung bình mỗi tháng."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 33, "review_scores_rating", "DECIMAL(4,2)", "NULL", "", "", "Listings.review_scores_rating", "Non-Additive Fact", "Điểm đánh giá tổng thể (miền 1.00–5.00) — dùng tính KPI-05."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 34, "review_scores_accuracy", "DECIMAL(4,2)", "NULL", "", "", "Listings.review_scores_accuracy", "Non-Additive Fact", "Điểm độ chính xác của mô tả."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 35, "review_scores_cleanliness", "DECIMAL(4,2)", "NULL", "", "", "Listings.review_scores_cleanliness", "Non-Additive Fact", "Điểm mức độ sạch sẽ."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 36, "review_scores_checkin", "DECIMAL(4,2)", "NULL", "", "", "Listings.review_scores_checkin", "Non-Additive Fact", "Điểm quy trình nhận phòng."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 37, "review_scores_communication", "DECIMAL(4,2)", "NULL", "", "", "Listings.review_scores_communication", "Non-Additive Fact", "Điểm giao tiếp chủ nhà."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 38, "review_scores_location", "DECIMAL(4,2)", "NULL", "", "", "Listings.review_scores_location", "Non-Additive Fact", "Điểm vị trí."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 39, "review_scores_value", "DECIMAL(4,2)", "NULL", "", "", "Listings.review_scores_value", "Non-Additive Fact", "Điểm giá trị tương xứng chi phí."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 40, "host_listings_count", "INT UNSIGNED", "NOT NULL", "", "", "Listings.host_listings_count", "Semi-Additive Fact", "Số tin đăng của chủ nhà theo hồ sơ."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 41, "calculated_host_listings_count", "INT UNSIGNED", "NOT NULL", "", "", "Listings.calculated_host_listings_count", "Semi-Additive Fact", "Tổng số tin đăng của chủ nhà trong snapshot."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 42, "calculated_host_listings_count_entire_homes", "INT UNSIGNED", "NOT NULL", "", "", "Listings.calculated_host_listings_count_entire_homes", "Semi-Additive Fact", "Số tin đăng nguyên căn của chủ nhà."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 43, "calculated_host_listings_count_private_rooms", "INT UNSIGNED", "NOT NULL", "", "", "Listings.calculated_host_listings_count_private_rooms", "Semi-Additive Fact", "Số tin đăng phòng riêng của chủ nhà."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 44, "calculated_host_listings_count_shared_rooms", "INT UNSIGNED", "NOT NULL", "", "", "Listings.calculated_host_listings_count_shared_rooms", "Semi-Additive Fact", "Số tin đăng phòng chung của chủ nhà."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 45, "estimated_occupancy_l365d", "INT UNSIGNED", "NOT NULL", "", "", "Listings.estimated_occupancy_l365d", "Semi-Additive Fact (Estimate)", "Số ngày lấp đầy ước tính của nguồn (không phải giao dịch thực)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 46, "estimated_revenue_l365d", "DECIMAL(14,2)", "NULL", "", "", "Listings.estimated_revenue_l365d", "Semi-Additive Fact (Estimate)", "Doanh thu ước tính của nguồn (không phải doanh thu thực)."),
        ("fact_listing_snapshot", "Fact (Periodic Snapshot)", 47, "created_at", "DATETIME", "NOT NULL", "", "", "CURRENT_TIMESTAMP", "Audit / Metadata", "Thời điểm nạp bản ghi vào kho."),

        # ---------------- fact_calendar ----------------
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 1, "calendar_sk", "BIGINT UNSIGNED", "NOT NULL", "PK (AUTO_INCREMENT)", "", "System generated", "Surrogate Key", "Khóa đại diện dòng lịch theo ngày."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 2, "listing_sk", "BIGINT UNSIGNED", "NOT NULL", "FK", "dim_listing.listing_sk", "Lookup from dim_listing(listing_id, snapshot_date)", "Foreign Key", "Khóa ngoại tham chiếu dim_listing."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 3, "neighbourhood_sk", "INT UNSIGNED", "NOT NULL", "FK", "dim_neighbourhood.neighbourhood_sk", "Inherited from dim_listing.neighbourhood_sk", "Foreign Key (Conformed)", "Khóa ngoại tham chiếu dim_neighbourhood để tăng tốc lọc KPI-04 theo khu vực."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 4, "calendar_date_sk", "INT", "NOT NULL", "FK", "dim_date.date_sk", "Derived from Calendar.date", "Foreign Key", "Khóa ngoại tham chiếu ngày lịch trong dim_date."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 5, "snapshot_date_sk", "INT", "NOT NULL", "FK", "dim_date.date_sk", "Derived from snapshot_date", "Foreign Key", "Khóa ngoại tham chiếu ngày snapshot trong dim_date."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 6, "listing_id", "BIGINT UNSIGNED", "NOT NULL", "UNIQUE (BK part 1)", "", "Calendar.listing_id", "Natural Key", "Mã tin đăng gốc."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 7, "calendar_date", "DATE", "NOT NULL", "UNIQUE (BK part 2)", "", "Calendar.date", "Natural Key", "Ngày lịch được quan sát (2026-09-25..2027-09-25)."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 8, "snapshot_date", "DATE", "NOT NULL", "UNIQUE (BK part 3)", "", "source_inventory.snapshot_date", "Natural Key", "Ngày snapshot (2026-09-23)."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 9, "is_available", "TINYINT(1)", "NOT NULL", "", "", "Calendar.available ('t'->1, 'f'->0)", "Additive / Binary Fact", "Trạng thái mở lịch (1=Available, 0=Unavailable) — dùng tính KPI-04."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 10, "minimum_nights", "INT UNSIGNED", "NOT NULL", "", "", "Calendar.minimum_nights", "Non-Additive Fact", "Số đêm lưu trú tối thiểu áp dụng cho ngày lịch."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 11, "maximum_nights", "INT UNSIGNED", "NOT NULL", "", "", "Calendar.maximum_nights", "Non-Additive Fact", "Số đêm lưu trú tối đa áp dụng cho ngày lịch."),
        ("fact_calendar", "Fact (Daily Grain Snapshot)", 12, "created_at", "DATETIME", "NOT NULL", "", "", "CURRENT_TIMESTAMP", "Audit / Metadata", "Thời điểm nạp bản ghi vào kho."),

        # ---------------- fact_review ----------------
        ("fact_review", "Fact (Transaction / Event)", 1, "review_sk", "BIGINT UNSIGNED", "NOT NULL", "PK (AUTO_INCREMENT)", "", "System generated", "Surrogate Key", "Khóa đại diện sự kiện đánh giá."),
        ("fact_review", "Fact (Transaction / Event)", 2, "listing_sk", "BIGINT UNSIGNED", "NOT NULL", "FK", "dim_listing.listing_sk", "Lookup from dim_listing(listing_id, snapshot_date)", "Foreign Key", "Khóa ngoại tham chiếu dim_listing."),
        ("fact_review", "Fact (Transaction / Event)", 3, "neighbourhood_sk", "INT UNSIGNED", "NOT NULL", "FK", "dim_neighbourhood.neighbourhood_sk", "Inherited from dim_listing.neighbourhood_sk", "Foreign Key (Conformed)", "Khóa ngoại tham chiếu dim_neighbourhood."),
        ("fact_review", "Fact (Transaction / Event)", 4, "review_date_sk", "INT", "NOT NULL", "FK", "dim_date.date_sk", "Derived from Reviews.date", "Foreign Key", "Khóa ngoại tham chiếu ngày đánh giá trong dim_date."),
        ("fact_review", "Fact (Transaction / Event)", 5, "snapshot_date_sk", "INT", "NOT NULL", "FK", "dim_date.date_sk", "Derived from snapshot_date", "Foreign Key", "Khóa ngoại tham chiếu ngày snapshot trong dim_date."),
        ("fact_review", "Fact (Transaction / Event)", 6, "listing_id", "BIGINT UNSIGNED", "NOT NULL", "UNIQUE (BK part 1)", "", "Reviews.listing_id", "Natural Key", "Mã tin đăng được đánh giá."),
        ("fact_review", "Fact (Transaction / Event)", 7, "review_id", "BIGINT UNSIGNED", "NOT NULL", "UNIQUE (BK part 2)", "", "Reviews.id", "Degenerate Dimension / Natural Key", "Mã đánh giá từ hệ thống nguồn (duy nhất khi kết hợp với listing_id)."),
        ("fact_review", "Fact (Transaction / Event)", 8, "review_date", "DATE", "NOT NULL", "", "", "Reviews.date", "Natural Attribute", "Ngày đăng đánh giá (2011-05-04..2026-09-25)."),
        ("fact_review", "Fact (Transaction / Event)", 9, "snapshot_date", "DATE", "NOT NULL", "UNIQUE (BK part 3)", "", "source_inventory.snapshot_date", "Natural Key", "Ngày snapshot (2026-09-23)."),
        ("fact_review", "Fact (Transaction / Event)", 10, "reviewer_id", "BIGINT UNSIGNED", "NOT NULL", "", "", "Reviews.reviewer_id", "Degenerate Attribute", "Mã người dùng viết đánh giá."),
        ("fact_review", "Fact (Transaction / Event)", 11, "reviewer_name", "VARCHAR(150)", "NOT NULL", "", "", "Reviews.reviewer_name", "Degenerate Attribute", "Tên hiển thị của người đánh giá."),
        ("fact_review", "Fact (Transaction / Event)", 12, "has_comment", "TINYINT(1)", "NOT NULL", "", "", "1 if Reviews.comments not null/blank else 0", "Binary Flag", "Cờ có nội dung bình luận văn bản (45,983 dòng = 1; 17 dòng = 0)."),
        ("fact_review", "Fact (Transaction / Event)", 13, "comment_length", "INT UNSIGNED", "NOT NULL", "", "", "CHAR_LENGTH(TRIM(Reviews.comments))", "Additive / Descriptive Fact", "Độ dài ký tự của nội dung bình luận."),
        ("fact_review", "Fact (Transaction / Event)", 14, "review_count", "TINYINT UNSIGNED", "NOT NULL", "", "", "Constant 1", "Additive Fact", "Biến đếm sự kiện đánh giá (= 1) phục vụ tính SUP-02."),
        ("fact_review", "Fact (Transaction / Event)", 15, "created_at", "DATETIME", "NOT NULL", "", "", "CURRENT_TIMESTAMP", "Audit / Metadata", "Thời điểm nạp bản ghi vào kho."),
    ]
    return pd.DataFrame(cols, columns=[
        "table_name", "table_type", "ordinal_position", "column_name",
        "mysql_dtype", "nullable", "key_constraint", "references_table_column",
        "source_mapping", "kimball_role", "description"
    ])


# ==============================================================================
# 3. DANH SÁCH TEST CASES BÀN GIAO CHO HỒNG / MINH / THÁI (TASK 2.4)
# ==============================================================================

def build_etl_test_checklist() -> pd.DataFrame:
    tests = [
        ("TC-01", "TQ-01", "Staging -> Silver -> Gold", "Listings", "id, scrape_id, last_scraped, room_type, neighbourhood_cleansed, neighbourhood_group_cleansed", "Completeness (Not NULL)", "COUNT(*) WHERE required_col IS NULL = 0", "0 dòng thiếu ở các cột bắt buộc (3,208/3,208 hợp lệ)", "Thái (ETL) / Hồng (QA)"),
        ("TC-02", "TQ-01", "Staging -> Silver -> Gold", "Calendar", "listing_id, calendar_date, is_available, minimum_nights, maximum_nights", "Completeness (Not NULL)", "COUNT(*) WHERE required_col IS NULL = 0", "0 dòng thiếu trên 1,170,950 dòng", "Thái (ETL) / Hồng (QA)"),
        ("TC-03", "TQ-01", "Staging -> Silver -> Gold", "Reviews", "listing_id, review_id, review_date, reviewer_id", "Completeness (Not NULL)", "COUNT(*) WHERE required_col IS NULL = 0", "0 dòng thiếu trên 46,000 dòng", "Thái (ETL) / Hồng (QA)"),
        ("TC-04", "TQ-01", "Staging -> Silver -> Gold", "Neighbourhoods", "neighbourhood_group, neighbourhood_name", "Completeness (Not NULL & Not Blank)", "COUNT(*) WHERE col IS NULL OR TRIM(col)='' = 0", "0 dòng thiếu/rỗng trên 55 dòng", "Thái (ETL) / Hồng (QA)"),
        ("TC-05", "TQ-01", "Silver -> Gold", "fact_listing_snapshot", "listed_price_sgd, review_scores_rating", "Preserving Valid NULLs", "Không tự động thay NULL bằng 0: NULL count(listed_price_sgd)=483, NULL count(review_scores_rating)=1369", "Khớp chính xác số lượng NULL trước và sau ETL", "Hồng (QA) / Minh (DW)"),
        ("TC-06", "TQ-02", "Silver -> Gold", "dim_listing & fact_listing_snapshot", "(listing_id, snapshot_date)", "Grain Uniqueness", "COUNT(*) - COUNT(DISTINCT listing_id, snapshot_date) = 0", "0 dòng trùng khóa trên 3,208 dòng", "Minh (DW) / Hồng (QA)"),
        ("TC-07", "TQ-02", "Silver -> Gold", "fact_calendar", "(listing_id, calendar_date, snapshot_date)", "Grain Uniqueness", "COUNT(*) - COUNT(DISTINCT listing_id, calendar_date, snapshot_date) = 0", "0 dòng trùng khóa trên 1,170,950 dòng", "Minh (DW) / Hồng (QA)"),
        ("TC-08", "TQ-02", "Silver -> Gold", "fact_review", "(listing_id, review_id, snapshot_date)", "Composite Grain Uniqueness", "COUNT(*) - COUNT(DISTINCT listing_id, review_id, snapshot_date) = 0; ghi nhận riêng 4,809 dòng dư theo review_id riêng lẻ; đối chiếu thêm host, không khẳng định nguyên nhân", "0 dòng trùng theo khóa ghép (46,000 dòng)", "Thái (ETL) / Minh (DW) / Hồng (QA)"),
        ("TC-09", "TQ-02", "Silver -> Gold", "dim_neighbourhood", "(neighbourhood_group, neighbourhood_name)", "Grain Uniqueness", "COUNT(*) - COUNT(DISTINCT neighbourhood_group, neighbourhood_name) = 0", "0 dòng trùng khóa trên 55 dòng", "Minh (DW) / Hồng (QA)"),
        ("TC-10", "TQ-03", "Silver -> Gold", "fact_calendar -> dim_listing", "listing_sk / (listing_id, snapshot_date)", "Referential Integrity", "LEFT JOIN dim_listing WHERE dim_listing.listing_sk IS NULL = 0", "100% (1,170,950/1,170,950 dòng khớp khóa cha, 0 orphan)", "Minh (DW) / Hồng (QA)"),
        ("TC-11", "TQ-03", "Silver -> Gold", "fact_review -> dim_listing", "listing_sk / (listing_id, snapshot_date)", "Referential Integrity", "LEFT JOIN dim_listing WHERE dim_listing.listing_sk IS NULL = 0", "100% (46,000/46,000 dòng khớp khóa cha, 0 orphan)", "Minh (DW) / Hồng (QA)"),
        ("TC-12", "TQ-03", "Silver -> Gold", "dim_listing -> dim_neighbourhood", "neighbourhood_sk / (neighbourhood_group, neighbourhood_name)", "Referential Integrity", "LEFT JOIN dim_neighbourhood WHERE dim_neighbourhood.neighbourhood_sk IS NULL = 0", "100% (3,208/3,208 dòng khớp vào 42/55 khu vực chuẩn, 0 orphan)", "Minh (DW) / Hồng (QA)"),
        ("TC-13", "TQ-03", "Silver -> Gold", "All Facts -> dim_date", "snapshot_date_sk, calendar_date_sk, review_date_sk", "Date Dimension Coverage", "LEFT JOIN dim_date WHERE dim_date.date_sk IS NULL = 0", "100% các ngày trong khoảng 2011-05-04..2027-09-26 đều tồn tại trong dim_date", "Minh (DW)"),
        ("TC-14", "TQ-04; KPI-02", "Silver -> Gold", "fact_listing_snapshot", "listed_price_raw_amount, quote_currency, is_price_sgd_verified, listed_price_sgd", "Price & Currency Rule", "listed_price_raw_amount có 2,728 dòng > 0; quote_currency='SGD' có 2,855 dòng; giao nhau tạo 2,725 dòng có listed_price_sgd > 0 (3 dòng thiếu currency trong JSON phải có listed_price_sgd IS NULL)", "Đúng 2,725 dòng hợp lệ SGD, Median = 202.83 SGD", "Thái (ETL) / Minh (DW) / Hồng (QA)"),
        ("TC-15", "TQ-04", "Silver -> Gold", "dim_listing & fact_listing_snapshot", "accommodates, minimum_nights_avg_ntm, maximum_nights_avg_ntm", "Data Type Fidelity (Feedback Fix)", "accommodates là INT (1..16); minimum_nights_avg_ntm (320 dòng lẻ) và maximum_nights_avg_ntm (426 dòng lẻ) giữ kiểu DECIMAL(10,2)", "Không mất phần thập phân của *_avg_ntm; accommodates không bị parse thành ngày 1970", "Thái (ETL) / Hồng (QA)"),
        ("TC-16", "TQ-04", "Silver -> Gold", "dim_listing & fact_calendar", "is_available, host_is_superhost, host_has_profile_pic, host_identity_verified, has_availability", "Boolean Standardization", "Ánh xạ 't'->1, 'f'->0, giữ NULL ở has_availability (42 dòng); không có giá trị ngoài {0, 1, NULL}", "100% dòng boolean thuộc miền {0, 1, NULL}", "Thái (ETL) / Hồng (QA)"),
        ("TC-17", "TQ-04; KPI-05", "Silver -> Gold", "fact_listing_snapshot", "review_scores_rating & 6 sub-scores", "Rating Range Validation", "Tất cả giá trị không NULL nằm trong [1.00, 5.00]", "1,839/1,839 dòng rating tổng thể nằm trong [1.00, 5.00], 0 vi phạm", "Thái (ETL) / Hồng (QA)"),
        ("TC-18", "TQ-04", "Raw -> Silver -> Gold", "All 4 datasets", "Row counts per source and snapshot", "Row Count Reconciliation", "Đối chiếu số dòng theo snapshot; giải thích mọi reject/orphan; không rơi dòng âm thầm", "Listings=3,208; Calendar=1,170,950; Reviews=46,000; Neighbourhoods=55 (snapshot chuẩn)", "Thái (ETL) / Minh (DW) / Hồng (QA)"),
        ("TC-19", "KPI-01..05; SUP-01..02", "Silver vs Gold SQL", "Warehouse Views vs Pandas Silver", "7 chỉ tiêu KPI/SUP", "KPI Reconciliation & Anti-Fanout", "So sánh kết quả SQL trên Gold (không JOIN trực tiếp fact_calendar với fact_review) với Pandas trên Silver", "Chênh lệch = 0 ở độ chính xác gốc (KPI-01=3208, KPI-02=202.83, KPI-04=76.94%, KPI-05=4.54, SUP-01=1.0, SUP-02=46000)", "Minh (SQL) / Hồng (Pandas QA)"),
        ("TC-20", "TQ-05", "End-to-End Pipeline", "All Staging, Silver, Gold tables", "Row counts & KPI outputs after Run #1 vs Run #2", "Pipeline Re-run Idempotency", "Chạy lại pipeline lần 2 trên cùng snapshot 2026-09-23 (UPSERT / TRUNCATE-insert theo partition snapshot_date)", "Số dòng và 7 chỉ tiêu KPI/SUP sau lần chạy 2 bằng đúng lần chạy 1 (0 dòng nhân đôi)", "Thái (ETL) / Minh (DW) / Tiên (Sign-off)"),
    ]
    return pd.DataFrame(tests, columns=[
        "test_id", "related_kpi_or_tq", "target_layer", "dataset_or_table",
        "fields_under_test", "check_category", "test_logic_or_assertion",
        "expected_pass_criteria", "owner"
    ])


# ==============================================================================
# 4. KIỂM CHỨNG THỰC NGHIỆM TRÊN DỮ LIỆU THẬT (DATA/RAW)
# ==============================================================================

def verify_against_raw_data(mapping_df: pd.DataFrame, wh_df: pd.DataFrame) -> pd.DataFrame:
    listings = pd.read_csv(RAW_DIR / "listings.csv.gz", low_memory=False)
    calendar = pd.read_csv(RAW_DIR / "calendar.csv.gz", low_memory=False)
    reviews = pd.read_csv(RAW_DIR / "reviews.csv.gz", low_memory=False)
    neigh = pd.read_csv(RAW_DIR / "neighbourhoods.csv", low_memory=False)

    raw_map = {
        "Listings": listings,
        "Calendar": calendar,
        "Reviews": reviews,
        "Neighbourhoods": neigh,
    }

    results = []

    # 1. Kiểm tra độ phủ 103 cột nguồn
    mapped_raw = mapping_df[~mapping_df["source_column"].str.startswith("[METADATA]")]
    total_raw_cols = sum(len(df.columns) for df in raw_map.values())
    results.append((
        "V-01", "Source Column Coverage", "All 4 Raw Files",
        total_raw_cols, len(mapped_raw),
        "PASS" if total_raw_cols == len(mapped_raw) == 103 else "FAIL",
        "100% (103/103) cột từ 4 file nguồn đã có quy tắc mapping trong source_to_target_mapping.csv."
    ))

    # 2. Kiểm tra từng nguồn khớp chính xác tên cột
    for src_name, df in raw_map.items():
        m_cols = set(mapped_raw.loc[mapped_raw["source_dataset"] == src_name, "source_column"])
        r_cols = set(df.columns)
        diff = m_cols ^ r_cols
        results.append((
            f"V-02-{src_name}", "Exact Column Name Match", src_name,
            len(r_cols), len(m_cols),
            "PASS" if len(diff) == 0 else "FAIL",
            f"Khớp {len(r_cols)}/{len(r_cols)} cột nguồn {src_name}." if not diff else f"Lệch cột: {diff}"
        ))

    # 3. Kiểm tra khóa dự kiến (Grain Uniqueness)
    l_dup = int(listings.duplicated(subset=["id"]).sum())
    c_dup = int(calendar.duplicated(subset=["listing_id", "date"]).sum())
    r_dup_comp = int(reviews.duplicated(subset=["listing_id", "id"]).sum())
    r_dup_single = int(reviews.duplicated(subset=["id"]).sum())
    n_dup = int(neigh.duplicated(subset=["neighbourhood_group", "neighbourhood"]).sum())

    results.append(("V-03", "Grain Uniqueness: Listings(id, snapshot_date)", "Listings", 0, l_dup, "PASS" if l_dup == 0 else "FAIL", "3,208/3,208 dòng duy nhất."))
    results.append(("V-04", "Grain Uniqueness: Calendar(listing_id, date, snapshot_date)", "Calendar", 0, c_dup, "PASS" if c_dup == 0 else "FAIL", "1,170,950/1,170,950 dòng duy nhất."))
    results.append(("V-05", "Grain Uniqueness: Reviews(listing_id, id, snapshot_date)", "Reviews", 0, r_dup_comp, "PASS" if r_dup_comp == 0 else "FAIL", f"0 dòng trùng theo khóa ghép (listing_id, id); có {r_dup_single} dòng dư theo id riêng lẻ; chưa xác minh ngữ nghĩa khóa nghiệp vụ từ nguồn."))
    results.append(("V-06", "Grain Uniqueness: Neighbourhoods(neighbourhood_group, neighbourhood)", "Neighbourhoods", 0, n_dup, "PASS" if n_dup == 0 else "FAIL", "55/55 dòng duy nhất."))

    # 4. Kiểm tra toàn vẹn tham chiếu (Referential Integrity)
    listing_ids = set(listings["id"])
    c_orphan = int((~calendar["listing_id"].isin(listing_ids)).sum())
    r_orphan = int((~reviews["listing_id"].isin(listing_ids)).sum())
    neigh_pairs = set(zip(neigh["neighbourhood_group"].str.strip(), neigh["neighbourhood"].str.strip()))
    l_neigh_pairs = set(zip(listings["neighbourhood_group_cleansed"].str.strip(), listings["neighbourhood_cleansed"].str.strip()))
    n_orphan = len(l_neigh_pairs - neigh_pairs)

    results.append(("V-07", "FK Integrity: fact_calendar -> dim_listing", "Calendar -> Listings", 0, c_orphan, "PASS" if c_orphan == 0 else "FAIL", "100% listing_id trong Calendar tồn tại trong Listings."))
    results.append(("V-08", "FK Integrity: fact_review -> dim_listing", "Reviews -> Listings", 0, r_orphan, "PASS" if r_orphan == 0 else "FAIL", "100% listing_id trong Reviews tồn tại trong Listings."))
    results.append(("V-09", "FK Integrity: dim_listing -> dim_neighbourhood", "Listings -> Neighbourhoods", 0, n_orphan, "PASS" if n_orphan == 0 else "FAIL", f"42/42 cặp khu vực trong Listings đều nằm trong 55 khu vực của Neighbourhoods."))

    # 5. Kiểm tra quy tắc giá & tiền tệ SGD cho KPI-02
    price_num = pd.to_numeric(listings["price"].astype(str).str.replace(r"[\$,]", "", regex=True), errors="coerce")
    def extract_currency(val):
        if pd.isna(val):
            return None
        try:
            return json.loads(val).get("quote", {}).get("currency")
        except Exception:
            return None

    currencies = listings["price_quote_raw"].apply(extract_currency)
    sgd_verified_mask = price_num.notna() & np.isfinite(price_num) & (price_num > 0) & (currencies == "SGD")
    sgd_count = int(sgd_verified_mask.sum())
    median_sgd = round(float(price_num[sgd_verified_mask].median()), 2)
    unverified_price_rows = int((price_num.notna() & (currencies != "SGD")).sum())

    results.append((
        "V-10", "KPI-02 Price & SGD Currency Rule", "fact_listing_snapshot",
        2725, sgd_count,
        "PASS" if sgd_count == 2725 and median_sgd == 202.83 else "FAIL",
        f"2,728 dòng có price dạng số; 2,725 dòng xác minh quote.currency='SGD' (Median = {median_sgd} SGD); {unverified_price_rows} dòng có price nhưng thiếu currency trong JSON được tách riêng."
    ))

    # 6. Baseline raw: đây không phải kết quả truy vấn bảng Gold/MySQL.
    available = calendar["available"].astype("string").str.strip().str.lower().map(
        {"t": 1, "true": 1, "1": 1, "f": 0, "false": 0, "0": 0})
    rating = pd.to_numeric(listings["review_scores_rating"], errors="coerce")
    rating = rating[rating.notna() & np.isfinite(rating) & rating.between(1, 5)]
    expected = {"KPI-01": 3208, "KPI-02": 202.83, "KPI-04": 76.9427,
                "KPI-05": 4.5394, "SUP-01": 1.0, "SUP-02": 46000}
    observed = {"KPI-01": int(listings["id"].nunique()), "KPI-02": median_sgd,
                "KPI-04": round(float(available.mean() * 100), 4),
                "KPI-05": round(float(rating.mean()), 4),
                "SUP-01": float(listings["number_of_reviews"].median()),
                "SUP-02": len(reviews.drop_duplicates(["listing_id", "id"]))}
    expected_rooms = {"Private room": 1827, "Entire home/apt": 1232, "Hotel room": 83, "Shared room": 66}
    observed_rooms = listings["room_type"].value_counts(dropna=False).to_dict()
    expected["KPI-03_COUNTS"] = expected_rooms
    observed["KPI-03_COUNTS"] = observed_rooms
    baseline_ok = all(np.isclose(observed[k], expected[k], rtol=0, atol=0.00005)
                      for k in expected if k != "KPI-03_COUNTS") and observed_rooms == expected_rooms
    results.append(("V-11", "Raw KPI baseline vs pinned snapshot", "Raw only; NOT Gold/MySQL",
        json.dumps(expected, sort_keys=True), json.dumps(observed, sort_keys=True),
        "PASS" if baseline_ok else "FAIL",
        "So sánh giá trị tính lại từ raw với baseline snapshot 2026-09-23; KPI-04 và share theo %, rating 1–5. Chưa chạy SQL Gold."))

    # 7. Kiểm tra thiết kế đích thật sự: rỗng, mapping sai cột/kiểu hoặc CSV lệch DDL phải FAIL.
    ddl_path = PROJECT_ROOT / "sql" / "02_warehouse_schema_draft.sql"
    errors = validate_design(mapping_df.fillna(""), wh_df.fillna(""), ddl_path.read_text(encoding="utf-8"))
    results.append(("V-12", "Mapping targets and schema CSV vs DDL", "Static design only; NOT executed DDL",
        0, len(errors), "FAIL" if errors else "PASS", "; ".join(errors) if errors else "Mọi cột/kiểu mapping đích tồn tại; CSV và DDL khớp tên/kiểu/NULL. Không thay thế chạy DDL trên MySQL."))

    return pd.DataFrame(results, columns=[
        "check_id", "check_name", "scope", "expected", "observed", "status", "detail"
    ])


def main():
    _set_console_encoding()
    print("=" * 75)
    print("KHỞI TẠO & KIỂM CHỨNG TÀI LIỆU TASK 2.4 VÀ TASK 2.5")
    print("=" * 75)

    dd_df = pd.read_csv(DD_ALL_PATH, encoding="utf-8-sig")
    mapping_df = build_source_to_target_mapping(dd_df)
    mapping_df.to_csv(MAPPING_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"[PASS] Đã xuất {MAPPING_CSV_PATH.relative_to(PROJECT_ROOT)} ({len(mapping_df)} dòng mapping).")

    wh_df = build_warehouse_schema_columns()
    wh_df.to_csv(WAREHOUSE_COLS_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"[PASS] Đã xuất {WAREHOUSE_COLS_CSV_PATH.relative_to(PROJECT_ROOT)} ({len(wh_df)} cột trên 6 bảng Warehouse).")

    test_df = build_etl_test_checklist()
    test_df.to_csv(ETL_TEST_CHECKLIST_PATH, index=False, encoding="utf-8-sig")
    print(f"[PASS] Đã xuất {ETL_TEST_CHECKLIST_PATH.relative_to(PROJECT_ROOT)} ({len(test_df)} kịch bản kiểm thử).")

    ver_df = verify_against_raw_data(mapping_df, wh_df)
    ver_df.to_csv(VERIFICATION_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"[PASS] Đã xuất {VERIFICATION_CSV_PATH.relative_to(PROJECT_ROOT)} ({len(ver_df)} bước kiểm chứng thực nghiệm).")

    failed = ver_df[ver_df["status"] != "PASS"]
    for _, row in ver_df.iterrows():
        print(f"  [{row['status']}] {row['check_id']} - {row['check_name']}: {row['detail']}")

    if len(failed) > 0:
        sys.exit(1)
    print("\n[PASS] Kiểm tra raw và thiết kế tĩnh không phát hiện lỗi. Gold/MySQL: NOT_RUN; xem docs/gold_reconciliation.md.")


if __name__ == "__main__":
    main()
