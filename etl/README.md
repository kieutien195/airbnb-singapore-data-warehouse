# Pipeline Tích hợp Dữ liệu (ETL / Data Pipeline)

- **Phụ trách:** Thái (Data Engineer / ETL)
- **Phối hợp:** Minh (Data Warehouse / MySQL) & Hồng (QA / Data Quality)
- **Snapshot chuẩn:** `2026-09-23` (Inside Airbnb Singapore)

Tài liệu này hướng dẫn cách cấu hình, thực thi và kiểm chứng các module thuộc Phase 3:
- **Task 3.2**: Ingest dữ liệu thô vào Staging (`etl/ingest.py`)
- **Task 3.3**: Làm sạch và chuẩn hóa dữ liệu Silver (`etl/clean.py`)
- **Task 3.4**: Mapping sang Fact/Dimension Gold & kiểm tra quan hệ đa bảng (`etl/transform.py`)

---

## 1. Cấu trúc Thư mục Module ETL

```
etl/
├── config.yaml          # File cấu hình đường dẫn, chunk size, tham số snapshot
├── db.py                # Tiện ích kết nối MySQL an toàn, quản lý partition & idempotency
├── ingest.py            # Task 3.2: Module đọc CSV/GZ theo chunk nạp vào Staging
├── clean.py             # Task 3.3: Module làm sạch dữ liệu, chuẩn hóa price/date/boolean
├── transform.py         # Task 3.4: Module ánh xạ Star Schema & kiểm tra orphan key
├── run_pipeline.py      # Script điều phối chạy toàn trình end-to-end
└── README.md            # Tài liệu hướng dẫn sử dụng (tệp này)
```

---

## 2. Hướng dẫn Thực thi

### 2.1. Chạy Toàn trình Pipeline (Khuyến nghị)

```bash
# Kích hoạt virtual environment
.venv\Scripts\Activate.ps1

# Chạy toàn bộ 3 bước: Ingest -> Clean -> Transform
python etl/run_pipeline.py

# Chạy toàn bộ qua file, kể cả khi đã cấu hình MySQL
python etl/run_pipeline.py --file-only

# Hoặc chạy thử nghiệm nhanh ở chế độ mẫu (500 dòng đầu mỗi file):
python etl/run_pipeline.py --sample 500
```

### 2.2. Chạy Từng Module Độc lập

#### Bước 1 – Ingestion (Task 3.2):
```bash
# Chạy thử mẫu 500 dòng, chỉ xuất file:
python etl/ingest.py --sample 500

# Chạy toàn bộ dữ liệu nguồn:
python etl/ingest.py
```
- **Đầu ra**: 
  - MySQL Staging tables (khi có cấu hình MySQL và chạy toàn bộ): `stg_listings`, `stg_calendar`, `stg_reviews`, `stg_neighbourhoods`.
  - File Staging: `data/processed/staging/stg_*.csv`.
  - Log kiểm toán: `logs/ingest.log` và bảng `etl_ingest_log`.

#### Bước 2 – Làm sạch Dữ liệu Silver (Task 3.3):
```bash
python etl/clean.py
```
- **Đầu ra**:
  - Dữ liệu sạch tầng Silver: `data/processed/silver/silver_*.csv`.
  - Báo cáo kiểm toán trước-sau: `outputs/cleaning_audit_summary.csv`.
  - File bản ghi bị loại (nếu có vi phạm): `data/processed/rejected/etl_rejected_records.csv`.

#### Bước 3 – Mapping Fact/Dimension & Orphan Check (Task 3.4):
```bash
python etl/transform.py
```
- **Đầu ra**:
  - Dữ liệu chuẩn mô hình Star Schema: `data/processed/gold/` (`dim_date.csv`, `dim_neighbourhood.csv`, `dim_listing.csv`, `fact_listing_snapshot.csv`, `fact_calendar.csv`, `fact_review.csv`).
  - Báo cáo kiểm tra quan hệ và tỷ lệ orphan: `outputs/join_coverage.csv` và `tests/join_coverage.csv`.

---

## 3. Các Nguyên tắc Kỹ thuật Đã Được Hiện Thực

1. **Bảo mật**: Không bao giờ hardcode tài khoản/mật khẩu trong code. Toàn bộ kết nối được nạp an toàn từ `.env`.
2. **Tính khả lặp (TQ-05 / TC-20)**: Ingest dùng và kiểm tra DDL Task 3.1 trong `sql/01_staging_schema.sql` bằng verifier cùng task. Nếu schema cũ không khớp, nâng cấp theo hướng dẫn Task 3.1 trước khi nạp. Mỗi bảng dùng khóa MySQL theo snapshot và một transaction cho cả DELETE lẫn INSERT. Lỗi nạp hoặc sai số dòng cấu hình sẽ rollback bảng đang nạp và dừng pipeline. Khi đổi snapshot, cập nhật `expected_rows` trong cấu hình tương ứng.
   - Nếu đã cấu hình MySQL, lỗi kết nối làm lệnh thoát khác 0. Dùng `--file-only` khi muốn chạy toàn bộ qua file.
   - Chế độ mẫu chỉ ghi vào thư mục con `sample/` của từng tầng và báo cáo. Calendar/Reviews có thể thiếu listing cha do lấy mẫu từng file độc lập; các dòng này được ghi lại và loại khỏi Gold mẫu.
3. **Bảo toàn dữ liệu nghiệp vụ**:
   - `price` và `review_scores_*` có `NULL` hợp lệ được giữ nguyên `NULL`, tuyệt đối không thay bằng `0`.
   - Outliers (giá cao, sức chứa lớn) được giữ nguyên 100% trong Silver và Gold theo đúng phân phối tự nhiên của thị trường Singapore.
   - `accommodates` là số nguyên `1..16`, không bao giờ parse thành `DATE`.
   - Giữ nguyên phần thập phân của `minimum_nights_avg_ntm` và `maximum_nights_avg_ntm`.
   - `Reviews` được khử trùng theo đúng khóa ghép `(listing_id, review_id, snapshot_date)`, không xóa theo `id` đơn lẻ.
4. **Hiệu năng xử lý (High Performance)**:
   - File `calendar.csv.gz` (> 1.17 triệu dòng) được xử lý theo chunk và vector hóa 100% bằng NumPy/Pandas, hoàn tất toàn bộ pipeline trong chưa đầy 30 giây.
   - Nghiêm cấm mọi thao tác JOIN trực tiếp giữa Calendar và Reviews để triệt tiêu nguy cơ bùng nổ số dòng.

---

## 4. Nghiệm thu Bàn giao (Handoff)

- **Bàn giao Gold**: Khi thiếu listing cha hoặc khóa ngày, pipeline ghi coverage `FAIL` và thoát khác 0 trước khi xuất Gold mới. Dòng Calendar/Reviews thiếu listing cha nằm trong `outputs/etl_orphan_records.csv`. Khu vực mới được cảnh báo và ánh xạ vào `Unknown Neighbourhood` với SK 0. Chỉ dùng Gold cho bước 3.5 sau lần chạy toàn bộ thành công.
- **Nghiệm thu MySQL**: Chạy trên database thử nghiệm với quyền tạo bảng và ghi staging. Chạy hai lần cùng snapshot và đối chiếu số dòng theo bảng. Xác nhận log ingest thành công và bốn quan hệ trong `outputs/join_coverage.csv`.
