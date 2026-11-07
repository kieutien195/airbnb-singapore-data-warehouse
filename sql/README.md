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
| [`03_load_warehouse.sql`](03_load_warehouse.sql) | **Audit nạp Warehouse** | **Task 3.6** | DDL bảng kiểm toán được loader Python thực thi trước transaction. |
| [`03_validate_gold_against_raw.sql`](03_validate_gold_against_raw.sql) | Kiểm thử & QA | Task 3.5 & 4.x | Bộ truy vấn đối chiếu số lượng dòng, kiểm tra khóa mồ côi và tính toàn vẹn giữa các tầng. |
| [`04_warehouse_kpi_audit.sql`](04_warehouse_kpi_audit.sql) | KPI và kiểm tra kỹ thuật Gold | Task 3.6 | Các truy vấn chỉ đọc sau khi nạp Gold. |

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

## 4. Nạp kho dữ liệu Gold (Task 3.6)

Đầu vào chính là sáu CSV Gold đã qua cleaning và mapping ở 3.3–3.4. Cần giữ bốn file raw trong `data/raw/` để tính độc lập các chỉ tiêu đối chiếu. Phiên bản này nghiệm thu snapshot `2026-09-23`.

Trên database thử chưa có sáu bảng Gold, chạy `python scripts/verify_warehouse_schema.py` để tạo và kiểm tra DDL. Nếu đã có sáu bảng, dùng `--verify-only`.

```bash
python scripts/load_warehouse.py
```

Loader kiểm tra schema, nạp Dimension trước Fact, tra khóa MySQL theo business key, rồi đối chiếu số dòng và các chỉ tiêu Raw–Gold trước khi commit. KPI-02 được tính theo trung vị giá SGD và đối chiếu cả mẫu số. Nếu lỗi, lệnh thoát khác 0 và rollback các thay đổi dữ liệu của lượt nạp. DDL tạo bảng audit chạy riêng trước transaction.

Mặc định loader thử nạp lại cùng bộ CSV trong transaction để đối chiếu số dòng và KPI; dùng `--skip-idempotency-test` nếu chỉ cần nạp một lượt. Để nghiệm thu việc chạy lại qua hai phiên kết nối độc lập, chạy lệnh hai lần và kiểm tra hai kết quả đều đạt.

Lượt thành công ghi log vào `etl_load_log` và xuất `outputs/warehouse_load_summary.csv`, `outputs/warehouse_raw_vs_gold.csv`. Xem `logs/load_warehouse.log` để kiểm tra kết quả của lần chạy gần nhất. Có thể đối chiếu độc lập bằng [quy trình Raw–Gold](../docs/gold_reconciliation.md).

Chạy `04_warehouse_kpi_audit.sql` sau khi loader thành công để xem KPI và kiểm tra kỹ thuật ở tầng Gold. TQ-01 đến TQ-04 báo `NOT_RUN` nếu thiếu bảng có dữ liệu trong phạm vi kiểm tra và chưa phát hiện lỗi. Với TQ-05, dùng log replay của loader hoặc đối chiếu hai lần chạy độc lập cùng snapshot, vì SQL chỉ đọc một trạng thái của kho.
