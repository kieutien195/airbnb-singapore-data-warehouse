# MySQL và Kiến trúc DWH

Minh phụ trách toàn bộ hệ thống SQL: khởi tạo database, tầng staging (Bronze), kho dữ liệu (Gold), tối ưu chỉ mục và các view phân tích phục vụ báo cáo Power BI.

---

## 1. Danh mục kịch bản SQL theo tiến trình triển khai

| Tệp SQL | Phân hệ / Tầng dữ liệu | Nhiệm vụ liên quan | Mô tả tóm tắt |
|---|---|---|---|
| [`00_init_database.sql`](00_init_database.sql) | Môi trường MySQL | Task 1.5 | Tạo database `airbnb_sg_2026` với `utf8mb4`, kiểm tra phiên bản và collation. |
| [`01_staging_schema.sql`](01_staging_schema.sql) | **Staging (Bronze / Raw Landing)** | **Task 3.1** | Tạo 4 bảng `stg_*` chứa dữ liệu thô từ 4 file nguồn (103 cột nguồn + 3 cột metadata + `raw_id`), đánh chỉ mục inline. |
| [`02_warehouse_schema.sql`](02_warehouse_schema.sql) | **Warehouse (Gold Fact Constellation)** | **Task 3.5** | DDL triển khai chính thức 3 Dimension và 3 Fact theo grain đã duyệt; UNIQUE theo grain, FK ghép bảo vệ listing/snapshot, index và CHECK. |
| [`02_warehouse_schema_draft.sql`](02_warehouse_schema_draft.sql) | Thiết kế lịch sử | Task 2.5 | Bản nháp thiết kế gốc; DDL triển khai hiện hành nằm ở `02_warehouse_schema.sql`. |
| [`03_load_warehouse.sql`](03_load_warehouse.sql) | **Load Warehouse (ETL/ELT to Gold)** | **Task 3.6** | Quy trình nạp Dimension trước Fact, ánh xạ khóa surrogate, kiểm soát trùng lặp và đối chiếu số dòng nạp. |
| [`03_validate_gold_against_raw.sql`](03_validate_gold_against_raw.sql) | Kiểm thử & QA | Task 3.5 & 4.x | Bộ truy vấn đối chiếu số lượng dòng, kiểm tra khóa mồ côi và tính toàn vẹn giữa các tầng. |

---

## 2. Chi tiết Tầng Staging (`01_staging_schema.sql` - Task 3.1)

Tầng Staging đóng vai trò vùng đệm nạp thô (Raw Landing Zone), tuân thủ nguyên tắc **Bảo toàn dữ liệu gốc (Bronze Immutability)**:

1. **`stg_neighbourhoods`**: Nạp từ `data/raw/neighbourhoods.csv` (55 khu vực, 2 cột nguồn + 3 metadata + `raw_id`).
2. **`stg_calendar`**: Nạp từ `data/raw/calendar.csv.gz` (1,170,950 dòng, 5 cột nguồn + 3 metadata + `raw_id`). Index: `(listing_id, date)`, `(date)`, `(snapshot_date)`.
3. **`stg_reviews`**: Nạp từ `data/raw/reviews.csv.gz` (46,000 dòng, 6 cột nguồn + 3 metadata + `raw_id`). Index: `(listing_id)`, `(id)`, `(date)`, `(snapshot_date)`.
4. **`stg_listings`**: Nạp từ `data/raw/listings.csv.gz` (3,208 dòng, 90 cột nguồn + 3 metadata + `raw_id`). Index: `(id)`, `(host_id)`, `(snapshot_date)`, `(neighbourhood_cleansed)`.

### 3 Cột Metadata kiểm toán chuẩn hóa:
- `source_file VARCHAR(100)`: Tên tệp dữ liệu nguồn phát sinh bản ghi.
- `snapshot_date DATE`: Ngày snapshot dữ liệu (`2026-09-23`).
- `ingested_at DATETIME`: Mốc thời gian bản ghi được nạp vào MySQL Staging (`CURRENT_TIMESTAMP`).

---

## 3. Warehouse Schema DDL (`02_warehouse_schema.sql` - Task 3.5)

Triển khai mô hình **Fact Constellation** (Kimball) gồm 3 bảng Dimension và 3 bảng Fact:

- **Dimension**: `dim_date` (6,209 dòng ngày), `dim_neighbourhood` (55 khu vực quy hoạch), `dim_listing` (3,208 tin đăng).
- **Fact**: `fact_listing_snapshot` (3,208 dòng đo lường), `fact_calendar` (1,170,950 dòng lịch phòng), `fact_review` (46,000 dòng đánh giá).
- **Khóa ngoại ghép (Composite FK)**: `(listing_sk, snapshot_date_sk, neighbourhood_sk)` liên kết 3 Fact với `dim_listing`, bảo vệ chống lệch snapshot hoặc địa lý.
- **Ràng buộc Grain**: Khóa `UNIQUE` theo grain nghiệp vụ trên cả 3 bảng Fact.

Kiểm tra đối chiếu schema tự động:
```bash
.venv\Scripts\python.exe scripts/verify_warehouse_schema.py --verify-only
```

---

## 4. Quy trình nạp kho dữ liệu Gold (`03_load_warehouse.sql` - Task 3.6)

### Thứ tự nạp theo phụ thuộc khóa ngoại (Foreign Key Dependency):
1. **`dim_date`**: Nạp dải ngày lịch 2011-01-01 .. 2027-12-31 (6,209 dòng).
2. **`dim_neighbourhood`**: Nạp danh mục 55 khu vực quy hoạch từ Staging/Silver.
3. **`dim_listing`**: Nạp 3,208 tin đăng, map surrogate key `neighbourhood_sk` và `snapshot_date_sk`.
4. **`fact_listing_snapshot`**: Nạp 3,208 dòng chỉ số định lượng cấp listing.
5. **`fact_calendar`**: Nạp 1,170,950 dòng lịch phòng 365 ngày.
6. **`fact_review`**: Nạp 46,000 dòng đánh giá lịch sử.

### Bảng kiểm toán nạp kho (`etl_load_log`):
Mỗi bước nạp đều ghi lại: `step_order`, `table_name`, `rows_source`, `rows_loaded`, `rows_failed`, `duration_seconds`, `status`, `started_at`, `completed_at`.

### Chạy nạp kho dữ liệu và kiểm chứng tự động:
```bash
.venv\Scripts\python.exe scripts/load_warehouse.py
```
Script sẽ tự động:
1. Nạp đầy đủ 6 bảng Gold theo chuẩn batching và UPSERT (`ON DUPLICATE KEY UPDATE`).
2. Kiểm tra tính toàn vẹn tham chiếu (Referential Integrity): Kiểm tra khóa mồ côi (Orphan Keys) bằng SQL, đạt 0 orphan.
3. Kiểm tra tính khả lặp (Idempotency - TQ-05): Chạy lại lần 2 cùng snapshot, đối chiếu số dòng trước và sau nạp để chứng minh số dòng không bị nhân đôi.
4. Truy vấn xác thực 5 KPI cốt lõi và xuất báo cáo `outputs/warehouse_load_summary.csv`.
