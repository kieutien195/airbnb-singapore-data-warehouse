# DESIGN REVIEW — AIRBNB SINGAPORE DATA WAREHOUSE

## 1. Mục đích và phạm vi

Tài liệu mô tả thiết kế hệ thống tích hợp dữ liệu Inside Airbnb Singapore, từ CSV/CSV.GZ đến kho dữ liệu đa chiều MySQL và Power BI.

Nội dung tập trung vào:

- Kiến trúc Medallion và luồng dữ liệu.
- Fact/Dimension, grain và khóa liên kết.
- KPI lineage.
- Kiểm soát chất lượng và logging.
- Phân biệt thiết kế mục tiêu với triển khai hiện tại.
- Rủi ro và các điểm cần thống nhất.

Đây là tài liệu rà soát thiết kế, không phải báo cáo nghiệm thu toàn bộ pipeline.

## 2. Phạm vi dữ liệu

Nguồn: Inside Airbnb – Singapore.

Snapshot: `2026-09-23`
`scrape_id`: `20260923225116`
Ngày tải: `2026-10-29`
Encoding: `UTF-8-SIG`

| Tệp nguồn          | Số bản ghi | Số cột |
| ------------------ | ---------: | -----: |
| listings.csv.gz    |      3,208 |     90 |
| calendar.csv.gz    |  1,170,950 |      5 |
| reviews.csv.gz     |     46,000 |      6 |
| neighbourhoods.csv |         55 |      2 |

Tổng cộng có 103 cột nghiệp vụ. File nguồn được lưu nguyên bản trong `data/raw/`.

Lưu ý: `2026-09-23` là snapshot date theo metadata nguồn. Trường `last_scraped` trong Listings quan sát trong khoảng `2026-09-25` đến `2026-09-26`; hai thông tin này không được tự động thay thế cho nhau.

## 3. Kiến trúc tổng thể

### 3.1. Luồng kiến trúc mục tiêu

**CSV/GZ → MySQL Staging (Bronze) → Python Cleaning (Silver) → Transform & Load → MySQL Fact/Dimension (Gold) → Power BI**

- Bronze: lưu file nguồn nguyên bản và vùng tiếp nhận Staging trên MySQL.
- Silver: chuẩn hóa dữ liệu, xử lý NULL, kiểu dữ liệu, giá trị trùng và quy tắc nghiệp vụ.
- Gold: tổ chức dữ liệu thành Dimension và Fact trên MySQL.
- Analytics: SQL/KPI Views, Power BI Semantic Model và dashboards.
- Quality Control & Logging: kiểm soát xuyên suốt các tầng.

### 3.2. Input, process, output và công nghệ

| Tầng      | Đầu vào    | Xử lý chính                                                           | Đầu ra                           | Công nghệ               |
| --------- | ---------- | --------------------------------------------------------------------- | -------------------------------- | ----------------------- |
| Source    | CSV/GZ     | Kiểm tra nguồn, snapshot, schema                                      | File nguồn                       | Inside Airbnb, CSV/GZ   |
| Bronze    | data/raw/  | Tiếp nhận, giữ giá trị thô, bổ sung metadata, nạp Staging             | Bốn bảng stg\_\* và file Staging | Python, Pandas, MySQL 8 |
| Silver    | Staging    | Ép kiểu, chuẩn hóa giá/currency, NULL, boolean, ngày, duplicate       | Bốn file silver\_\*.csv          | Python, Pandas, NumPy   |
| Gold      | Silver     | Transform, ánh xạ surrogate key, tạo Dimension/Fact, kiểm tra và load | MySQL dim\_*, fact\_*            | Python, SQL, MySQL 8    |
| Analytics | MySQL Gold | SQL/KPI Views, semantic model, dashboard                              | Power BI                         | SQL, Power BI           |

### 3.3. Bronze — Raw / Landing

Bronze gồm:

- File nguồn nguyên bản tại `data/raw/`.
- Bốn bảng MySQL Staging: `stg_listings`, `stg_calendar`, `stg_reviews`, `stg_neighbourhoods`.

Metadata:

- `raw_id`
- `source_file`
- `snapshot_date`
- `ingested_at`

Staging ưu tiên bảo toàn giá trị thô. Ép kiểu và chuẩn hóa nghiệp vụ được thực hiện ở Silver.

### 3.4. Silver — Cleaned / Curated

Silver sử dụng Python/Pandas để:

- Chuẩn hóa kiểu số, ngày tháng và boolean.
- Parse giá và trích currency từ `price_quote_raw.quote.currency`.
- Chỉ xác nhận giá SGD khi có bằng chứng `quote.currency = 'SGD'`.
- Giữ NULL hợp lệ; không thay NULL bằng 0.
- Kiểm tra duplicate theo grain.
- Giữ outlier nếu chưa có bằng chứng nghiệp vụ cho phép loại bỏ.
- Tách bản ghi không hợp lệ và ghi lý do.

Đầu ra: bốn file Silver CSV trong `data/processed/silver/`.

### 3.5. Gold — Data Warehouse

Gold gồm:

- Dimension: `dim_date`, `dim_neighbourhood`, `dim_listing`.
- Fact: `fact_listing_snapshot`, `fact_calendar`, `fact_review`.

Transform & Load có trách nhiệm đọc Silver, tra cứu surrogate key, xây dựng Dimension/Fact, kiểm tra grain và khóa ngoại, sau đó nạp Dimension trước Fact vào MySQL.

DDL, PK, FK, UNIQUE và INDEX được mô tả trong `sql/02_warehouse_schema_draft.sql`.

Có DDL hoặc Gold CSV không đồng nghĩa dữ liệu đã được nạp và xác thực trong MySQL.

### 3.6. Analytics & Visualization

Power BI lấy dữ liệu từ MySQL Gold thông qua SQL Queries/KPI Views.

Dimension dùng để lọc và phân nhóm; Fact cung cấp số đo theo đúng grain. Semantic Model không nối trực tiếp các Fact với nhau.

## 4. Thiết kế mô hình dữ liệu

### 4.1. Định hướng

Sử dụng Kimball Dimensional Modeling theo cấu trúc **Fact Constellation (Galaxy Schema)**: ba Fact dùng chung ba Dimension.

### 4.2. Grain của Fact

| Fact                  | Grain                                            | Natural Key                                |   Số dòng |
| --------------------- | ------------------------------------------------ | ------------------------------------------ | --------: |
| fact_listing_snapshot | Một listing tại một snapshot                     | (listing_id, snapshot_date)                |     3,208 |
| fact_calendar         | Một listing tại một ngày lịch trong một snapshot | (listing_id, calendar_date, snapshot_date) | 1,170,950 |
| fact_review           | Một review theo listing tại một snapshot         | (listing_id, review_id, snapshot_date)     |    46,000 |

`review_id` không duy nhất nếu xét riêng. Khóa ghép `(listing_id, review_id)` phân biệt đủ 46,000 dòng. Không dùng `review_id` riêng lẻ làm khóa duy nhất.

### 4.3. Dimension

| Dimension         | Surrogate Key    | Vai trò                                   |
| ----------------- | ---------------- | ----------------------------------------- |
| dim_date          | date_sk          | Snapshot date, calendar date, review date |
| dim_neighbourhood | neighbourhood_sk | Phân cấp khu vực                          |
| dim_listing       | listing_sk       | Thuộc tính mô tả listing và host          |

Các thuộc tính host được tích hợp trong `dim_listing`; không tách `dim_host` riêng vì phạm vi phân tích tập trung ở cấp listing, loại phòng và khu vực.

### 4.4. Khóa và quan hệ

Các bảng Dimension được liên kết với Fact qua surrogate key. Natural key dùng kiểm tra tính duy nhất theo grain và snapshot.

Quan hệ quan trọng:

- dim_date → dim_listing: 1.
- dim_neighbourhood → dim_listing: 1.
- dim_listing → fact_listing_snapshot: 1:1 theo snapshot.
- dim_listing → fact_calendar: 1.
- dim_listing → fact_review: 1.
- dim_neighbourhood và dim_date liên kết với các Fact theo các vai trò khóa tương ứng.

`dim_date` là một bảng vật lý dùng cho nhiều vai trò ngày. Trong Power BI cần dùng role-playing dimensions hoặc quản lý quan hệ active/inactive rõ ràng để tránh ambiguous relationship.

**Điểm cần đối chiếu trên ERD:** DDL có `UNIQUE (listing_sk, snapshot_date_sk)` ở `fact_listing_snapshot`, nên quan hệ `dim_listing` → `fact_listing_snapshot` là 1:1 theo snapshot.

Không JOIN trực tiếp `fact_calendar` với `fact_review` ở mức chi tiết. Nếu cần kết hợp, phải tổng hợp từng Fact về cùng grain trước.

## 5. KPI lineage — KPI lấy từ Fact nào?

| Mã     | Chỉ tiêu                            | Fact nguồn                          |
| ------ | ----------------------------------- | ----------------------------------- |
| KPI-01 | Số listing duy nhất theo snapshot   | fact_listing_snapshot               |
| KPI-02 | Trung vị giá niêm yết mỗi đêm       | fact_listing_snapshot               |
| KPI-03 | Tỷ trọng loại phòng                 | fact_listing_snapshot + dim_listing |
| KPI-04 | Tỷ lệ bản ghi lịch còn available    | fact_calendar                       |
| KPI-05 | Điểm review tổng thể trung bình     | fact_listing_snapshot               |
| SUP-01 | Trung vị số review trên mỗi listing | fact_listing_snapshot               |
| SUP-02 | Số bản ghi review trong kỳ          | fact_review                         |

### 5.1. Liên hệ câu hỏi nghiên cứu

- RQ1: KPI-01, KPI-03.
- RQ2: KPI-02.
- RQ3: KPI-04.
- RQ4: KPI-05, SUP-01, SUP-02.
- RQ5: các kiểm tra chất lượng, grain, uniqueness, referential integrity và đối chiếu KPI.

### 5.2. Quy ước tính toán

- Snapshot chính: `2026-09-23`.
- Cửa sổ Calendar: `2026-09-25` đến `2027-09-25` (366 ngày).
- KPI-02 chỉ dùng giá xác minh được SGD.
- KPI-03 tính tử số và mẫu số ở cấp listing.
- KPI-04 dùng số dòng thỏa điều kiện; SQL dùng `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`.
- KPI-05 loại NULL, không thay NULL bằng 0.
- Tập rỗng hoặc mẫu số bằng 0 trả NULL/không xác định.
- Giữ độ chính xác gốc khi đối chiếu; chỉ làm tròn khi trình bày.

### 5.3. Raw baseline để đối chiếu

Đây là baseline tính từ Raw, không phải kết quả SQL Gold/MySQL.

| Chỉ tiêu |                                                                 Raw baseline |
| -------- | ---------------------------------------------------------------------------: |
| KPI-01   |                                                                3,208 listing |
| KPI-02   |                                                               202.83 SGD/đêm |
| KPI-03   | Entire home/apt: 1,232; Hotel room: 83; Private room: 1,827; Shared room: 66 |
| KPI-04   |                                                                     76.9427% |
| KPI-05   |                                                                  4.5394 điểm |
| SUP-01   |                                                           1.0 review/listing |
| SUP-02   |                                                        46,000 bản ghi review |

## 6. Quality Control & Logging

| Vị trí    | Nội dung kiểm tra                                             | Log / đầu ra                                       |
| --------- | ------------------------------------------------------------- | -------------------------------------------------- |
| Source    | File, encoding, schema, số dòng, snapshot, checksum           | docs/source_inventory.csv                          |
| Bronze    | Số dòng đọc/nạp/lỗi, thời gian chạy, metadata                 | logs/ingest.log, etl_ingest_log                    |
| Silver    | Kiểu dữ liệu, NULL, duplicate, miền giá trị, rejected records | logs/clean.log, outputs/cleaning_audit_summary.csv |
| Gold      | Mapping key, grain, FK coverage, orphan                       | logs/transform.log, outputs/join_coverage.csv      |
| Analytics | Đối chiếu KPI Raw/Pandas, SQL/MySQL và Power BI               | sql/03_validate_gold_against_raw\.sql              |

### 6.1. Bằng chứng hiện có

- Source inventory: bốn file có trạng thái đọc và schema PASS.
- Kiểm tra MySQL hiện có: xác nhận phần MySQL Staging.
- Cleaning audit: số dòng đầu vào và đầu ra không thay đổi; rejected ghi nhận 0.
- Join coverage: bốn quan hệ báo cáo 100% match, 0 orphan trong luồng Silver CSV → Gold CSV.
- Verification: mapping 103/103 cột, grain và kiểm tra Raw PASS; raw KPI baseline PASS; mapping/schema CSV đối chiếu tĩnh với DDL khớp.

**Giới hạn bằng chứng:**

- Join coverage không phải kết quả JOIN trực tiếp trên Gold MySQL.
- KPI baseline hiện tại là Raw-only.
- Kiểm tra mapping CSV với DDL là kiểm tra tĩnh.
- Bộ SQL validation cần được thực thi trên database có đủ bảng Gold mới có thể kết luận PASS.
- Technical KPI và ngưỡng mục tiêu chưa được chốt.

## 7. Thiết kế mục tiêu và triển khai hiện tại

| Công đoạn | Thiết kế mục tiêu                     | Hiện trạng                                                         |
| --------- | ------------------------------------- | ------------------------------------------------------------------ |
| Ingestion | CSV/GZ → MySQL Staging                | ingest.py đọc CSV/GZ, có thể nạp MySQL Staging và xuất Staging CSV |
| Cleaning  | MySQL Staging → Python Cleaning       | clean.py hiện đọc stg\_\*.csv và xuất Silver CSV                   |
| Transform | Silver → Transform & Load             | transform.py đọc Silver CSV và xuất sáu Gold CSV                   |
| Warehouse | Gold → MySQL Fact/Dimension           | DDL có bản nháp; cần thực thi DDL, nạp Gold và kiểm tra            |
| BI        | MySQL Gold → SQL/KPI Views → Power BI | Cần kiểm tra kết nối, semantic model, refresh và KPI               |

**Lưu ý triển khai:** `clean.py` hiện đọc Staging CSV. Đọc trực tiếp từ MySQL Staging là phần cần đồng bộ khi triển khai.

Kết quả đã có vẫn dùng được theo đúng phạm vi: kiểm tra MySQL xác nhận phần Staging; cleaning audit xác nhận bước xử lý file và đầu ra Silver; join coverage xác nhận quan hệ trong luồng Silver CSV → Gold CSV; Raw baseline xác nhận phép tính độc lập trên dữ liệu nguồn.

## 8. Rủi ro và điểm cần thống nhất

| Mức độ      | Rủi ro                                                      | Hướng xử lý                                                             |
| ----------- | ----------------------------------------------------------- | ----------------------------------------------------------------------- |
| Cao         | clean.py đọc Staging CSV thay vì truy vấn MySQL Staging     | Đồng bộ phương thức đọc khi triển khai                                  |
| Cao         | Chưa có bằng chứng nạp Gold vào MySQL và đối chiếu SQL      | Chạy DDL, load Dimension trước Fact, kiểm tra PK/FK/UNIQUE và row count |
| Cao         | review_id không duy nhất nếu xét riêng                      | Dùng khóa ghép listing_id + review_id + snapshot_date                   |
| Cao         | JOIN trực tiếp Calendar với Reviews                         | Tổng hợp từng Fact về cùng grain trước khi kết hợp                      |
| Trung bình  | Một dim_date phục vụ nhiều vai trò                          | Dùng role-playing dimensions hoặc active/inactive relationships         |
| Trung bình  | Thiếu currency ở một số bản ghi                             | Chỉ xác nhận SGD khi quote.currency = SGD                               |
| Trung bình  | Điểm review có NULL                                         | Loại NULL, công bố coverage                                             |
| Trung bình  | available FALSE bị hiểu thành booking                       | Không gọi là booked hoặc occupancy                                      |
| Trung bình  | Giá niêm yết bị hiểu thành doanh thu                        | Không suy ra doanh thu thực tế                                          |
| Trung bình  | Technical KPI chưa có ngưỡng                                | Thống nhất định nghĩa và ngưỡng sau baseline                            |
| Cần rà soát | dim_listing → fact_listing_snapshot có UNIQUE theo snapshot | Thể hiện 1:1 trên ERD                                                   |
| Cần rà soát | snapshot_date_sk giữa ERD, DDL và Power BI                  | Đảm bảo cột và vai trò ngày nhất quán                                   |

## 9. Tiêu chí thống nhất thiết kế

- Thống nhất luồng Bronze → Silver → Gold → Power BI và vai trò MySQL Staging.
- Xác định input, output, công nghệ, log và Quality Gate từng tầng.
- Giữ đúng grain và natural key của ba Fact.
- Ba Dimension dùng chung; PK/FK/UNIQUE khớp giữa ERD và DDL.
- Quan hệ dim_listing với fact_listing_snapshot là 1:1 theo snapshot.
- Mô hình hóa rõ các vai trò ngày trong dim_date.
- KPI-01 đến KPI-05, SUP-01 và SUP-02 có Fact nguồn, grain, công thức, bộ lọc và quy tắc NULL.
- Không JOIN trực tiếp Calendar và Reviews ở grain chi tiết.
- Có kế hoạch thực thi DDL, load Gold, đối chiếu số dòng và SQL validation.
- Có kế hoạch đối chiếu KPI Raw/Pandas, SQL/MySQL và Power BI.
- Technical KPI được định nghĩa riêng.

## 10. Kết luận

Thiết kế phù hợp với định hướng xây dựng kho dữ liệu Airbnb Singapore theo Medallion Architecture và Kimball Fact Constellation. Việc tách ba Fact theo ba grain riêng giúp kiểm soát mức độ chi tiết, hỗ trợ KPI và hạn chế sai lệch do JOIN nhiều bảng.

Các kiểm tra nguồn, cleaning, mapping tĩnh và join coverage đã cung cấp bằng chứng cho những phần tương ứng. Tuy nhiên, cần giữ ranh giới rõ giữa kiểm tra trên file CSV và kiểm tra trên MySQL: Staging đã được kiểm tra theo phạm vi hiện có; Silver/Gold CSV có báo cáo kiểm tra; việc nạp và xác thực Gold trong MySQL cùng kết nối Power BI cần được kiểm chứng ở giai đoạn triển khai.

Bản thiết kế có thể được dùng làm cơ sở rà soát và thống nhất kiến trúc. Trạng thái triển khai từng công đoạn cần được cập nhật riêng, không dùng trạng thái thực thi hiện tại để thay đổi luồng kiến trúc mục tiêu.
