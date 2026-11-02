# Kiểm thử dữ liệu và hệ thống

Hồng, Thái và Minh phụ trách kiểm tra missing, duplicate key, valid record, referential integrity và tính nhất quán khi chạy lại pipeline. Ghi kết quả trước và sau xử lý trên cùng phạm vi.

---

## 1. Kiểm tra môi trường (Smoke Test – Task 1.4)

Script `smoke_test.py` đặt tại thư mục gốc của repository, dùng để kiểm tra tính sẵn sàng của môi trường trước khi bắt đầu công việc:

- **Phiên bản Python**: Xác nhận Python >= 3.11 và đang kích hoạt virtual environment (`.venv`).
- **Thư viện phụ thuộc**: Import và kiểm tra phiên bản của tất cả các gói trong `requirements.txt` (`pandas`, `numpy`, `SQLAlchemy`, `PyMySQL`, `python-dotenv`, `jupyterlab`, `matplotlib`, `seaborn`).
- **Đọc dữ liệu thô (`data/raw/`)**: Kiểm tra sự tồn tại và đọc thử mẫu từ 4 nguồn:
  - `listings.csv.gz` (gzip, 90 cột, 3,208 dòng)
  - `calendar.csv.gz` (gzip, 5 cột, 1,170,950 dòng)
  - `reviews.csv.gz` (gzip, 6 cột, 46,000 dòng)
  - `neighbourhoods.csv` (CSV thuần, 2 cột, 55 dòng)
  - Toàn bộ đường dẫn sử dụng đường dẫn tương đối trong dự án (`data/raw/...`).
- **Kết nối MySQL**: Nạp biến môi trường từ `.env` (tạo từ `.env.example`), kiểm tra kết nối tới database thông qua SQLAlchemy + PyMySQL. Phối hợp cùng Minh (Task 1.5).

### Cách chạy:

```bash
# Kiểm tra Python, thư viện và đọc dữ liệu thô (bỏ qua MySQL nếu chưa cấu hình)
python smoke_test.py

# Bắt buộc kiểm tra kết nối MySQL (yêu cầu file .env đã cấu hình đầy đủ)
python smoke_test.py --mysql
```

---

## 2. Kế hoạch kiểm thử chất lượng dữ liệu (Data Quality – Tasks 3.x, 5.x)

- Kiểm tra khóa chính (PK uniqueness) và khóa ngoại (FK referential integrity).
- Kiểm tra tính đầy đủ (Completeness / Missing values).
- Kiểm tra miền giá trị hợp lệ (Validity / Range check).
- Kiểm tra tính nhất quán và khả năng chạy lại (Idempotency).
- Đối chiếu số liệu KPI trước và sau chuyển đổi (Reconciliation).
