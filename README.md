# Airbnb Singapore Data Warehouse

Đồ án môn **Nhà kho dữ liệu và tích hợp** — 29/10/2026–16/11/2026.

Xây dựng quy trình tích hợp dữ liệu Inside Airbnb Singapore bằng Python, kho dữ liệu đa chiều trên MySQL và dashboard Power BI.

## Thành viên

| Thành viên | Vai trò |
|---|---|
| Tiên | Leader, Data Architect, tích hợp và kiểm thử |
| Thái | Data Engineer, ETL |
| Hồng | Thu thập dữ liệu, EDA, Data Quality |
| Minh | Data Warehouse, MySQL, SQL KPI |
| Hưng | Power BI, phân tích và insight |

## Cấu trúc

| Đường dẫn | Nội dung |
|---|---|
| `data/raw/` | Dữ liệu gốc; không commit dataset |
| `data/processed/` | Dữ liệu đã xử lý; không commit dataset |
| `notebooks/` | EDA Notebook |
| `etl/` | Ingestion, cleaning, transformation |
| `sql/` | Staging, warehouse, nạp dữ liệu, KPI views |
| `tests/` | Kiểm tra chất lượng, khóa, grain và đối chiếu KPI |
| `docs/` | Scope, Data Dictionary, kiến trúc và nguồn dữ liệu |
| `dashboard/` | Power BI và hướng dẫn dashboard |

Đây là khung dự án ban đầu; pipeline, schema, notebook và dashboard sẽ được bổ sung trong các task tiếp theo.

## Thiết lập môi trường

Yêu cầu: Python 3.11+, MySQL 8.0+; Power BI Desktop trên máy người làm BI.

```bash
git clone https://github.com/kieutien195/airbnb-singapore-data-warehouse.git
cd airbnb-singapore-data-warehouse
python -m venv .venv
```

Kích hoạt môi trường:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
```

Sao chép `.env.example` thành `.env` và điền kết nối MySQL cục bộ. Không commit `.env`, mật khẩu hoặc thông tin đăng nhập.

### Kiểm tra môi trường (Smoke Test)

Sau khi cài đặt thư viện và cấu hình `.env`, chạy script kiểm thử:

```bash
python smoke_test.py            # Kiểm tra Python, thư viện và đọc dữ liệu thô
python smoke_test.py --mysql    # Bắt buộc kiểm tra thêm kết nối MySQL (Task 1.5)
```

## Dữ liệu và phạm vi

Nguồn: https://insideairbnb.com/get-the-data/ — Singapore; Listings, Calendar, Reviews và Neighbourhoods. Task 1.2 phải xác nhận URL, snapshot, thời gian tải, tên file và số dòng thực tế trước khi chốt dữ liệu. Không đưa dataset lớn vào Git; chia sẻ qua nơi lưu trữ chung của nhóm và ghi hướng dẫn tải trong `docs/`.

Dùng một snapshot chính. Listings phản ánh snapshot; Calendar theo ngày có trong file; Reviews có thể chứa lịch sử trước snapshot. Trạng thái unavailable không đồng nghĩa đã đặt phòng; không suy ra occupancy hoặc doanh thu thực tế.

Kho dự kiến gồm các fact listing snapshot, calendar và review với grain riêng, dùng chung dimension phù hợp. Thiết kế cần được kiểm chứng sau EDA. Không JOIN các fact ở mức chi tiết để tính KPI gây nhân bản.

## Quy tắc cộng tác

1. Clone repo và tạo nhánh theo công việc, ví dụ `feat/etl-ingest`, `docs/data-dictionary`.
2. Commit rõ nội dung: `feat: ...`, `fix: ...`, `docs: ...`.
3. Push nhánh và tạo Pull Request vào `main`; Tiên review trước khi merge.
4. Pull thay đổi mới trước khi bắt đầu công việc tiếp theo.
5. Không commit dữ liệu cá nhân không cần thiết, secrets, môi trường ảo hoặc dataset lớn.

Task 1.3 chỉ hoàn tất sau khi các thành viên được cấp quyền và kiểm tra clone, push nhánh, Pull Request thành công.
