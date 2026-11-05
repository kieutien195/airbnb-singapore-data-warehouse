# MySQL và Kiến trúc DWH

Minh phụ trách toàn bộ hệ thống SQL: khởi tạo database, tầng staging (Bronze), kho dữ liệu (Gold), tối ưu chỉ mục và các view phân tích phục vụ báo cáo Power BI.

---

## 1. Danh mục kịch bản SQL theo tiến trình triển khai

| Tệp SQL | Phân hệ / Tầng dữ liệu | Nhiệm vụ liên quan | Mô tả tóm tắt |
|---|---|---|---|
| [`00_init_database.sql`](00_init_database.sql) | Môi trường MySQL | Task 1.5 | Tạo database `airbnb_sg_2026` với `utf8mb4`, kiểm tra phiên bản và collation. |
| [`01_staging_schema.sql`](01_staging_schema.sql) | **Staging (Bronze / Raw Landing)** | **Task 3.1** | Tạo 4 bảng `stg_*` chứa dữ liệu thô từ 4 file nguồn (103 cột nguồn + 3 cột metadata + `raw_id`), đánh chỉ mục inline. |
| [`02_warehouse_schema_draft.sql`](02_warehouse_schema_draft.sql) | **Warehouse (Gold Star Schema)** | **Task 2.5 & 3.5** | Tạo 3 bảng Dimension (`dim_date`, `dim_neighbourhood`, `dim_listing`) và 3 bảng Fact (`fact_calendar`, `fact_listing_snapshot`, `fact_review`). |
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

`latitude` và `longitude` được lưu nguyên chuỗi nguồn ở Staging để không làm tròn tọa độ. Chuyển sang kiểu số và kiểm tra miền giá trị thuộc bước Silver. DDL không chọn database cố định: hãy chọn đúng schema trước khi chạy trong Workbench hoặc kết nối bằng `MYSQL_DATABASE` từ `.env` khi chạy script.

Nếu database đã có các bảng Staging theo DDL cũ, kiểm tra row count trước. Chạy [`01_staging_schema_migration.sql`](01_staging_schema_migration.sql) một lần để đổi `ingestion_time` thành `ingested_at` và đổi kiểu tọa độ. Các tọa độ đã lưu dưới `DECIMAL(11,8)` không thể khôi phục phần thập phân đã mất; nếu bảng có dữ liệu, phải nạp lại từ CSV raw sau migration.

### Tiêu chí bàn giao cho Thái (Task 3.2 Ingestion):
- Bảng chấp nhận dữ liệu thô: Chuỗi giá có ký hiệu `$` (`price: $86.63`), văn bản tự do, JSON array (`amenities`), JSON object (`price_quote_raw`).
- Chưa áp ràng buộc khóa ngoại (Foreign Key) để cho phép nạp song song hoặc độc lập từng tệp nguồn.
- Tài khoản ứng dụng ETL `airbnb_app_minh_fc487b` đã được cấp đầy đủ quyền `CREATE`, `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `DROP`, `INDEX`, `ALTER`.

---

## 3. Cách chạy và kiểm tra

### Chạy qua MySQL Workbench:
1. Mở MySQL Workbench, kết nối tới local MySQL instance.
2. Mở file `sql/01_staging_schema.sql`.
3. Chọn schema đúng theo `MYSQL_DATABASE` trong `.env` làm default schema trước khi chạy. DDL không chứa `USE` cố định.
4. Nhấn biểu tượng tia sét **Execute** (Ctrl + Shift + Enter).
5. Quan sát Action Output và xử lý mọi lỗi trước khi chạy verifier.

### Chạy kiểm tra tự động qua Python:
```bash
.venv\Scripts\python.exe scripts/verify_staging_schema.py
.venv\Scripts\python.exe scripts/test_staging_types.py
```
Verifier so sánh đầy đủ thứ tự cột, kiểu/precision/scale, NULL, default, auto-increment, comment, index và table options với DDL. Bài thử INSERT/SELECT/UPDATE/DELETE chỉ thao tác trên `raw_id` vừa tạo trong transaction rồi ROLLBACK. MySQL tự commit DDL; nếu schema hiện tại khác, script báo FAIL và không tự xóa/sửa bảng cũ.
