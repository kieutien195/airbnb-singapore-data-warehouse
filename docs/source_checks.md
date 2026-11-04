# Chạy lại khảo sát nguồn và Data Dictionary (task 2.1–2.2)

## Chuẩn bị

Chạy từ thư mục gốc của repo trong môi trường Python đã cài `requirements.txt`.
Notebook cần Pandas, Jupyter, nbformat, nbclient và ipykernel. Nếu môi trường
chưa có đủ: `python -m pip install pandas jupyter nbformat nbclient ipykernel`.

Đặt đúng bốn tệp `listings.csv.gz`, `calendar.csv.gz`, `reviews.csv.gz`,
`neighbourhoods.csv` trong `data/raw/`. Metadata nằm ở `docs/source_inventory.csv`.
Giữ nguyên tệp raw; các lệnh dưới đây chỉ ghi kết quả khảo sát/tài liệu.

## Task 2.1

```bash
python scripts/schema_survey.py
```

Lệnh tạo lại `docs/source_schema_summary.csv` và `docs/schema_survey_findings.md`.
Mở `notebooks/schema_survey.ipynb`, chọn đúng Python kernel rồi Run All và lưu.
Notebook cũng tự chạy khảo sát và xuất các tệp này; chạy được từ repo hoặc
thư mục `notebooks`, không cần đường dẫn cá nhân.

Bảng schema chứa dtype quan sát, số dòng/cột, NULL, distinct, mẫu và phạm vi ngày.
Các bảng khóa/liên kết thể hiện grain và khóa ứng viên trên snapshot hiện tại.
Không coi Reviews.id riêng là duy nhất, không dùng Listings.neighbourhood toàn
NULL để nối khu vực. Các sample văn bản cá nhân/mô tả dài được lược khỏi output
khảo sát. Chưa làm cleaning hoặc áp constraint warehouse ở bước này.

## Task 2.2

```bash
python scripts/data_dictionary_kpi.py
```

Lệnh tạo lại Dictionary, định nghĩa KPI và các bảng kiểm tra trong
`outputs/task_2_2/`, đồng thời tạo notebook `notebooks/02_data_dictionary_kpi.ipynb`.
Lệnh mặc định không cần mở Jupyter kernel. Để tạo notebook đã thực thi và lưu output:

```bash
python scripts/data_dictionary_kpi.py --execute-notebook
```

Hoặc mở notebook 2.2, Run All và lưu. Notebook tự tính từ raw bằng các hàm của
script; không yêu cầu `outputs/task_2_2/` tồn tại trước khi chạy.
Chạy lại script sẽ tạo lại notebook, vì vậy chạy notebook và lưu output sau bước sinh file.

Nguồn chỉnh sửa duy nhất là `scripts/data_dictionary_kpi.py`: ý nghĩa trường ở
`MEANINGS`/`meaning_for`, kiểu nghiệp vụ ở `transformation` và các tập trường rõ tên,
định nghĩa ở `BUSINESS_KPIS`/`TECH_KPIS`. Không sửa tay CSV rồi chạy script vì nội dung
sẽ được sinh lại. Bản tổng hợp và bốn bản riêng được tạo cùng một lần từ cùng quy tắc.

`initial_pandas_dtype` là kết quả quan sát, không phải kiểu MySQL đích. Cột toàn NULL
không cung cấp bằng chứng để tự chọn DECIMAL. `snapshot_date` là metadata nguồn,
trong khi `last_scraped` quan sát từ 2026-09-25 đến 2026-09-26.

TQ-01 đến TQ-04 hiện là baseline raw với các luật tối thiểu được công bố trong code.
TQ-05 vẫn là CHƯA ĐÁNH GIÁ cho đến khi có hai lần chạy ETL cùng đầu vào và log đối chiếu.
Miền rating 1–5 là miền quan sát; chưa thay cho việc xác minh metadata nguồn.

## Kiểm tra hồi quy

Sau khi tạo Dictionary:

```bash
python -m unittest discover -s tests -p test_dictionary_schema.py
```

Các kiểm tra bảo vệ các trường từng bị gán sai kiểu, đối chiếu schema/NULL và
tính nhất quán của bản tổng hợp với bốn bản riêng. Không cần MySQL.
