# Chạy lại EDA — Task 2.3

Từ thư mục gốc repo, kích hoạt môi trường Python của dự án rồi chạy:

```bash
python -m pip install pandas numpy matplotlib nbformat nbclient ipykernel
python scripts/eda_data_quality.py
python -m unittest discover -s tests -p "test_eda_support.py" -v
```

Script tạo lại `notebooks/01_eda.ipynb`, thực thi và lưu output. Kernel mặc định
là `python3`. Nếu nhóm dùng kernelspec riêng:

```bash
python -m ipykernel install --user --name airbnb-venv --display-name "Airbnb (.venv)"
python scripts/eda_data_quality.py --kernel airbnb-venv
```

Có thể mở notebook trong VS Code/Jupyter, chọn đúng môi trường rồi **Run All**
và lưu. Notebook tìm repo từ thư mục gốc hoặc `notebooks/`, không cần Colab.
`--generate-only` chỉ tạo notebook chưa chạy, không xác nhận các kết quả cũ.
Script là nguồn sinh notebook; khi thay logic, sửa script/helper và tạo lại notebook.

## Đầu ra và quy tắc

| File | Nội dung |
|---|---|
| `notebooks/01_eda.ipynb` | EDA và biểu đồ đã chạy |
| `tests/data_quality_baseline.csv` | NULL, khóa, miền, outlier, liên kết, currency, checksum và review reconciliation |
| `tests/review_reconciliation.csv` | Một dòng/listing; số review Listings, số khóa Reviews và chênh lệch |
| `docs/eda/review_group_summary.csv` | Trung vị số review và mẫu số của tất cả khu vực/loại phòng |
| `docs/eda/cleaning_recommendations.csv` / `.md` | Khuyến nghị và bằng chứng sinh từ cùng lần chạy |

- Giá chính: parse `Listings.price`, lấy giá hữu hạn > 0, chỉ lấy SGD xác nhận
  qua `price_quote_raw.quote.currency`. Thiếu currency không suy từ ký hiệu `$`.
  Quote được đối chiếu trên cùng tập listing có đủ hai giá SGD hợp lệ.
- Rating: 1–5 là miền quan sát của snapshot, thống nhất KPI; chưa thay cho
  xác minh metadata chính thức. Giữ NULL và báo cáo coverage.
- Review: so sánh toàn bộ lịch sử ngày hợp lệ trong file với một snapshot Listings.
  Đếm khóa `(listing_id,id)` phân biệt, khóa số nguyên dương; không xóa raw.
  `observed_review_records = 0` nghĩa là không có review trong file; số review
  thiếu/sai ở Listings vẫn là NULL. Chênh lệch không đủ chứng minh nguồn nào sai.
- Trung vị theo nhóm gồm các listing có số review hợp lệ, kể cả 0; bảng có
  `listing_count` và `listings_with_valid_review_count` để đọc đúng mẫu số.

## LF/CRLF và raw

`.gitattributes` quy định LF cho file văn bản và `data/raw/** -text` để Git
không tự đổi xuống dòng của dữ liệu gốc. Quy tắc này không khôi phục file đã
bị đổi byte trước đó. Không chạy renormalize toàn repo để sửa raw.

Kiểm tra trước khi commit:

```bash
git check-attr text eol -- notebooks/01_eda.ipynb data/raw/neighbourhoods.csv
git diff --stat
git diff -- data/raw
```

Notebook đối chiếu SHA256 byte gốc với `docs/source_inventory.csv`. Chỉ CSV văn
bản có phép thử CRLF → LF trong bộ nhớ; không áp dụng cho gzip và không ghi
ngược ra raw. `MATCH_AFTER_CRLF_TO_LF` là cảnh báo lệch byte, không phải khớp
gốc. Nếu cần khôi phục, lấy đúng file tải gốc và xác nhận SHA256 trùng inventory;
không đổi checksum để che chênh lệch. Mismatch không giải thích được sẽ dừng EDA.

## Lần xác minh trong môi trường sửa PR

Tất cả code cell được thực thi tuần tự bằng IPython trong cùng tiến trình và
lưu bảng/biểu đồ vào notebook. Môi trường này không hỗ trợ socket của Jupyter
kernel; thông tin đó được ghi trong metadata notebook. Nhóm cần chạy lệnh trên
hoặc Run All một lần ở VS Code để xác nhận đường thực thi qua kernel thực tế.
