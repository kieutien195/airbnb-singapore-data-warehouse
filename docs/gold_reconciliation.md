# Đối chiếu raw – Gold/MySQL

Raw, Silver và Gold có thể lệch do ép kiểu, điền NULL thành 0, chọn sai currency,
lọc khác ngày/snapshot, JOIN nhân dòng hoặc chạy nạp lại sinh bản ghi trùng.
MySQL cũng có thể đúng trong khi baseline kỳ vọng bị ghi sai. Không chọn một
phía là đúng chỉ vì đó là raw hay MySQL: phải dùng cùng định nghĩa, đầu vào,
snapshot, cửa sổ ngày và mẫu số. Với dữ liệu hiện tại, rating hợp lệ có trung bình
4.5394 (1.839 listing), không phải 4.5974.

## 1. Kiểm tra raw và thiết kế (chưa cần MySQL)

Từ repo, kích hoạt môi trường Python và cài requirements của dự án:

```bash
python scripts/task_2_4_2_5_mapping_and_schema.py
python -m unittest discover -s tests -p "test_warehouse_validation.py" -v
python scripts/warehouse_validation.py
```

Lệnh đầu tạo lại mapping, schema CSV, checklist và verification. V-01..V-11
khảo sát raw; V-12 kiểm tra thiết kế tĩnh (mapping đích, schema CSV, DDL).
V-11 so sánh thật với baseline snapshot đã kiểm tra; mọi FAIL làm script trả mã 1.
Đây chưa phải chạy DDL, nạp Gold hoặc đối chiếu SQL.

Lệnh cuối tạo `tests/gold_reconciliation/raw_expected_metrics.csv` và
`comparison_context.json`, đồng thời in `Gold/MySQL: NOT_RUN`.
Không dùng CSV raw này làm bằng chứng đã truy vấn Gold.

## 2. Sau khi đã nạp Gold vào MySQL

1. Trong MySQL Workbench, chọn đúng database đã có 6 bảng Gold. Không cần chạy
   lại CREATE TABLE hoặc nạp lại dữ liệu để làm phép đối chiếu này.
2. Mở `sql/03_validate_gold_against_raw.sql`. Sửa 5 biến đầu file theo
   `comparison_context.json` vừa sinh: snapshot, hai ngày Calendar, hai ngày Reviews.
   Mặc định dùng toàn bộ lịch sử review trong file, không tự lọc riêng năm 2026.
3. Chạy cả file. File chỉ dùng biến phiên và SELECT, không sửa dữ liệu.
4. Export **result grid cuối** thành CSV UTF-8 có header và dấu phẩy phân cột,
   đặt tên `tests/gold_reconciliation/gold_metrics.csv`. Cột phải là:
   `snapshot_date,metric,group_value,value`. SQL NULL xuất ô rỗng hoặc `NULL`;
   không thay bằng 0. Không tự sửa số để cho khớp.
5. Chạy:

```bash
python scripts/warehouse_validation.py --gold-csv tests/gold_reconciliation/gold_metrics.csv
```

Kết quả nằm ở `tests/gold_reconciliation/raw_vs_gold.csv`:

- `value_raw`: tính trực tiếp từ raw bằng Pandas.
- `value_gold`: kết quả SELECT MySQL đã xuất.
- `difference_gold_minus_raw`: Gold trừ raw.
- `status`: FAIL khi thiếu/thừa chỉ tiêu, lệch snapshot/nhóm hoặc lệch số.
  Trùng khóa đối chiếu hoặc giá trị không phải số hữu hạn làm lệnh dừng lỗi.

PASS chỉ khi tất cả dòng khớp ở độ chính xác 4 chữ số lẻ (sai số <= 0.00005).
Số đếm nguyên vì vậy phải khớp chính xác. NULL hợp lệ ở cả hai phía khác với
một dòng chỉ tiêu bị thiếu. Mã thoát 1 nghĩa là có chênh lệch cần điều tra.

## 3. Các kiểm tra có trong CSV

- 5 KPI và SUP-01/SUP-02; KPI-03 gồm số lượng và tỷ trọng đủ 4 loại phòng.
- Mẫu số giá SGD, rating, Calendar và số listing có số review hợp lệ.
- Số dòng ba fact, NULL giá/rating, số dòng dư theo grain.
- Liên kết Calendar/Reviews với dim_listing cùng listing_id và snapshot,
  đồng thời đúng listing_sk. Không JOIN hai fact chi tiết với nhau.

Kỳ vọng snapshot chuẩn:

| Chỉ tiêu | Giá trị |
|---|---:|
| KPI-01 | 3208 |
| KPI-02 | 202.83 SGD |
| Giá SGD hợp lệ | 2725 |
| KPI-04 | 76.9427% |
| KPI-05 | 4.5394 |
| Rating hợp lệ | 1839 |
| SUP-01 | 1.0 |
| SUP-02 (toàn bộ khoảng ngày file) | 46000 |

Giá dùng Listings.price sau parse, hữu hạn >0 và SGD xác nhận từ JSON. Rating
lọc miền quan sát 1–5. SUP-02 đếm cặp (listing_id,review_id) phân biệt có khóa và
ngày hợp lệ trong khoảng đã chọn, thuộc một snapshot. Không gộp nhiều snapshot.

## 4. Khi FAIL thì tìm ở đâu?

| Triệu chứng | Kiểm tra tiếp |
|---|---|
| Số dòng hoặc DUP_* lệch | Grain, lọc snapshot, reject/orphan log, UPSERT và chạy lại pipeline |
| Giá lệch hoặc mẫu giá khác 2725 | Parse `$`/dấu phẩy, SGD trong JSON, giá <=0, NULL có bị điền 0 |
| Rating lệch | Giữ NULL; AVG trên listing có rating, không cân theo số review; không JOIN Calendar/Reviews |
| KPI-03 lệch nhưng số listing đúng | Lookup dim_listing cùng snapshot, room_type bị đổi/thiếu |
| KPI-04 lệch | Cùng cửa sổ ngày, boolean 0/1, mẫu số đêm hợp lệ; không dùng availability_365 thay Calendar |
| SUP-02 lệch | Cùng khoảng review, khóa ghép, không xóa review theo id riêng lẻ |

PASS tổng hợp không chứng minh mọi giá trị từng dòng đều đúng: vẫn phải có
kiểm tra khóa/FK/kiểu/miền ở pipeline, đối chiếu theo listing khi cần và chạy
pipeline hai lần cho TC-20. Phần này không tự thực hiện nạp hay kiểm thử Power BI.
