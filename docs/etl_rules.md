# Quy tắc Làm sạch, Ánh xạ Nguồn–Đích và Kế hoạch Kiểm thử (Task 2.4)

- **Mã công việc:** WBS 2.4 – Viết quy tắc cleaning, mapping và kiểm thử
- **Phụ trách chính:** Thái (Data Engineer / ETL)
- **Phối hợp nghiệm thu:** Minh (Data Warehouse / MySQL) & Hồng (EDA / Data Quality)
- **Snapshot chuẩn:** `2026-09-23` (theo `docs/source_inventory.csv`; `scrape_id = 20260923225116`)
- **Tệp bàn giao đi kèm:**
  - Bảng ánh xạ chi tiết 103 cột nguồn + 4 cột metadata: [`docs/source_to_target_mapping.csv`](source_to_target_mapping.csv)
  - Danh sách 20 kịch bản kiểm thử bàn giao cho Hồng/Minh: [`tests/etl_test_checklist.csv`](../tests/etl_test_checklist.csv)
  - Kết quả kiểm tra raw và thiết kế tĩnh (chưa chạy SQL Gold): [`tests/task_2_4_2_5_verification.csv`](../tests/task_2_4_2_5_verification.csv)

---

## 1. Nguyên tắc thiết kế quy trình Cleaning & Mapping

1. **Bảo toàn dữ liệu gốc (Bronze/Raw Immutability):** Các tệp trong `data/raw/` và bảng `stg_*` giữ nguyên giá trị thô đọc từ nguồn, chỉ bổ sung metadata (`snapshot_date`, `source_file`, `ingested_at`). Tọa độ `latitude`/`longitude` ở Staging được lưu dạng chuỗi đúng như CSV; khi đọc Listings để nạp Staging, dùng `dtype={"latitude": "string", "longitude": "string"}` hoặc `csv.DictReader`, không ép sang float trước khi ghi. Việc ép kiểu và kiểm tra miền giá trị chỉ thực hiện ở Silver.
2. **Làm sạch dựa trên bằng chứng thực nghiệm (Evidence-based Cleaning):** Mọi quy tắc ép kiểu, xử lý `NULL`, khóa trùng và kiểm tra miền giá trị đều dựa trên kết quả khảo sát thực tế từ Task 2.2 (`docs/data_dictionary/`, `docs/kpi_definitions/`) và Task 2.3 (`docs/eda/cleaning_recommendations.md`, `tests/data_quality_baseline.csv`).
3. **Không suy diễn hoặc làm giả dữ liệu nghiệp vụ:**
   - Tuyệt đối **không thay `NULL` bằng `0`** ở các cột giá (`price`, `price_quote_*`) hoặc điểm đánh giá (`review_scores_*`).
   - Tuyệt đối **không tự động cắt bỏ ngoại lai (outliers)** theo ngưỡng IQR ở tầng dữ liệu kho vì các tin đăng hạng sang/villa nguyên căn có giá cao thực tế.
   - Tuyệt đối **không suy đơn vị tiền tệ `SGD` chỉ từ ký hiệu `$`** mà phải đối chiếu trường `quote.currency` trong `price_quote_raw`.
4. **Tính khả lặp (Idempotency – TQ-05):** Quy trình nạp vào Staging, Silver và Gold phải gắn với `snapshot_date` và khóa tự nhiên (`UNIQUE KEY`) để khi chạy lại cùng một snapshot không phát sinh bản ghi nhân đôi.

---

## 2. Đồng bộ và hiệu chỉnh các lưu ý từ Data Dictionary (`docs/feedback.md`)

Khi chuyển từ Data Dictionary (Task 2.2) sang bảng ánh xạ `docs/source_to_target_mapping.csv` (Task 2.4), nhóm đã chuẩn hóa triệt để 7 nhóm trường dữ liệu dễ gây lỗi ép kiểu tự động trong Pandas:

| Nhóm trường nguồn | Hiện trạng trong Pandas (`dtype_initial`) | Quy tắc chuẩn hóa trong Mapping (Task 2.4) |
|---|---|---|
| `Listings.accommodates` | `int64` (miền giá trị thực tế: `1`–`16`) | Giữ kiểu số nguyên dương `INT UNSIGNED` (sức chứa khách tối đa). **Không** parse thành kiểu ngày (`DATE`). |
| `price_quote_checkin_date`, `price_quote_checkout_date` | `str` (`2026-09-26` .. `2027-09-26`, 318 dòng `NULL`) | Parse thành kiểu **`DATE`**, giữ `NULL` và kiểm tra `checkout_date >= checkin_date`. **Không** xử lý như tiền tệ/`DECIMAL`. |
| `price_quote_raw` | `str` (chuỗi JSON dài tối đa 1,147 ký tự, 318 dòng `NULL`) | Giữ nguyên JSON ở Staging/Silver; parse JSON để trích `quote.currency` (`CHAR(3)`) và bật cờ `is_price_sgd_verified` (`TINYINT(1)`). |
| `minimum_nights_avg_ntm`, `maximum_nights_avg_ntm` | `float64` (lần lượt có **320** và **426** dòng mang phần thập phân) | Giữ kiểu số thập phân **`DECIMAL(10,2)`**. **Không** làm tròn hoặc ép sang số nguyên `INT`. |
| `bedrooms`, `beds`, `minimum_nights`, `maximum_nights`, `minimum_minimum_nights`, `maximum_minimum_nights`, `minimum_maximum_nights`, `maximum_maximum_nights` | `float64` (do có `NULL` trong CSV, nhưng **0 dòng** có phần thập phân) | Chuyển sang số nguyên cho phép `NULL` (**`INT UNSIGNED NULL`** trong MySQL / `Int64` nullable trong Pandas). |
| 13 cột trống toàn bộ (`100% NULL`: `neighborhood_overview`, `host_since`, `host_response_time`, `host_response_rate`, `host_acceptance_rate`, `host_thumbnail_url`, `host_neighbourhood`, `host_total_listings_count`, `host_verifications`, `neighbourhood`, `bathrooms`, `calendar_updated`, `instant_bookable`) | `float64` (mặc định của Pandas khi toàn bộ 3,208 dòng đều `NaN`) | Định nghĩa đúng kiểu nghiệp vụ gốc (`VARCHAR`, `TEXT`, `DATE`, `INT`, `TINYINT(1)`), **không** suy từ `float64` sang `DECIMAL`. Giữ ở Staging để truy vết và lược bỏ ở tầng Gold (`KEEP_RAW_ONLY_ALL_NULL`). |
| `first_review`, `last_review` & 5 cột cờ `t/f` (`host_is_superhost`, `host_has_profile_pic`, `host_identity_verified`, `has_availability`, `Calendar.available`) | `str` | `first_review`, `last_review` chuyển sang **`DATE NULL`**; 5 cột cờ ánh xạ `'t' -> 1`, `'f' -> 0` sang **`TINYINT(1)`** (giữ `NULL` ở 42 dòng `has_availability`). |

---

## 3. Quy tắc làm sạch và biến đổi theo nhóm nghiệp vụ

### 3.1. Chuẩn hóa giá niêm yết và xác minh tiền tệ (`KPI-02`)
- **Bước 1 – Parse số thực từ chuỗi `Listings.price`:**
  - Chuỗi gốc có định dạng `$86.63` hoặc `$1,250.00` (480/3,208 dòng `NULL`, 2,728 dòng có chuỗi giá).
  - Loại bỏ ký tự `$`, dấu phẩy `,` và khoảng trắng; chuyển sang `DECIMAL(12,2)` lưu vào cột `listed_price_raw_amount`.
- **Bước 2 – Trích xuất và xác minh đơn vị tiền tệ từ `Listings.price_quote_raw`:**
  - Parse chuỗi JSON tại đường dẫn `$.quote.currency` lưu vào cột `quote_currency` (`CHAR(3)`).
  - Thực tế trong snapshot `2026-09-23`:
    - `2,855` dòng có `quote.currency = 'SGD'` (trong đó `2,725` dòng có `price` hợp lệ và `130` dòng `price IS NULL`).
    - `318` dòng `price_quote_raw IS NULL` (cả 318 dòng đều có `price IS NULL`).
    - `35` dòng có JSON nhưng `quote.currency IS NULL`: trong đó `32` dòng `price IS NULL` và **3 dòng** (`id` thuộc `{1371380025584025715, 1399039657808453221, 1542584497208173462}`) có chuỗi `price` (`$230.00`, `$125.10`, `$182.00`) nhưng `quote.currency = null` và `price_quote_price_per_night = null`.
- **Bước 3 – Gán cột chuẩn tính KPI (`listed_price_sgd` & `is_price_sgd_verified`):**
  - `is_price_sgd_verified = 1` khi và chỉ khi `listed_price_raw_amount > 0 AND quote_currency = 'SGD'` (**2,725 dòng**), ngược lại bằng `0`.
  - `listed_price_sgd = CASE WHEN is_price_sgd_verified = 1 THEN listed_price_raw_amount ELSE NULL END`.
  - Nhờ tách rõ `listed_price_raw_amount` (2,728 dòng) và `listed_price_sgd` (2,725 dòng, khớp 100% với `price_quote_price_per_night`), trung vị giá niêm yết `KPI-02` đạt chính xác **`202.83 SGD/đêm`** trên cả Pandas và MySQL.

### 3.2. Chuẩn hóa ngày tháng (`DATE`) và phạm vi thời gian
- Tất cả các cột ngày (`Listings.last_scraped`, `Listings.calendar_last_scraped`, `Listings.first_review`, `Listings.last_review`, `Listings.price_quote_checkin_date`, `Listings.price_quote_checkout_date`, `Calendar.date`, `Reviews.date`) đều có định dạng ISO `YYYY-MM-DD` và `0` lỗi parse trên dữ liệu thực tế.
- Chuyển đổi sang kiểu `DATE` và tạo khóa ngoại số nguyên `YYYYMMDD` (`INT`) để nối với bảng chiều `dim_date`:
  - `snapshot_date_sk` (ví dụ `20260923`)
  - `calendar_date_sk` (phạm vi `20260925` – `20270925`)
  - `review_date_sk` (phạm vi `20110504` – `20260925`)

### 3.3. Chuẩn hóa trạng thái lịch `available` (`KPI-04`) và các cờ Boolean
- Quy tắc ánh xạ thống nhất cho mọi trường boolean:
  - `'t'`, `'true'`, `'1'` (không phân biệt hoa thường, đã `TRIM`) $\rightarrow$ `1` (`TRUE`)
  - `'f'`, `'false'`, `'0'` $\rightarrow$ `0` (`FALSE`)
  - Giá trị `NULL` hoặc chuỗi rỗng:
    - Với `Calendar.available`: thuộc trường bắt buộc (`NOT NULL`) $\rightarrow$ nếu `NULL` hoặc khác miền hợp lệ sẽ bị từ chối và ghi log lỗi (`REJECT_ROW`). Trong dữ liệu hiện tại: `900,960` dòng `'t'` (`1`) và `269,990` dòng `'f'` (`0`), `0` dòng lỗi.
    - Với `Listings.has_availability`, `host_is_superhost`, `host_has_profile_pic`, `host_identity_verified`: cho phép giữ `NULL` khi dữ liệu nguồn bị khuyết (`has_availability` có 42 dòng `NULL`).

---

## 4. Quy định xử lý `NULL`, Bản ghi trùng (`Duplicates`), Khóa mồ côi (`Orphan Keys`) và Outliers

### 4.1. Phân loại cách xử lý `NULL`

| Nhóm trường | Trường cụ thể | Số lượng `NULL` (Snapshot 2026-09-23) | Hành động xử lý | Lý do nghiệp vụ & kỹ thuật |
|---|---|---:|---|---|
| **Nhóm A – Khóa và trường bắt buộc (`NOT NULL`)** | `Listings`: `id`, `scrape_id`, `last_scraped`, `room_type`, `neighbourhood_cleansed`, `neighbourhood_group_cleansed`, `host_id`, `latitude`, `longitude`, `accommodates`, `number_of_reviews`<br>`Calendar`: `listing_id`, `date`, `available`, `minimum_nights`, `maximum_nights`<br>`Reviews`: `listing_id`, `id`, `date`, `reviewer_id`<br>`Neighbourhoods`: `neighbourhood_group`, `neighbourhood` | `0` | **Loại bỏ bản ghi vi phạm (`REJECT_ROW`)** và ghi vào bảng/file `etl_rejected_records` | Thiếu khóa chính, khóa ngoại hoặc chiều phân tích cốt lõi sẽ làm hỏng grain hoặc sai mẫu số KPI. |
| **Nhóm B – Thước đo KPI có `NULL` hợp lệ** | `Listings.price` (480), `price_quote_price_per_night` (483), `listed_price_sgd` (483), `review_scores_rating` (1,369) và 6 cột điểm thành phần (1,369–1,370), `reviews_per_month` (1,369) | `480` – `1,370` | **Giữ nguyên `NULL` (`KEEP_NULL`)** | Listing chưa mở báo giá hoặc chưa từng có đánh giá (`number_of_reviews = 0`). Thay bằng `0` sẽ kéo tụt giả tạo trung vị giá (`KPI-02`) và điểm trung bình (`KPI-05`). |
| **Nhóm C – Thuộc tính mô tả & cấu hình tùy chọn** | `source` (1,470), `description` (21), `host_location` (1,322), `host_about` (1,292), `bathrooms_text` (10), `bedrooms` (2), `beds` (154), `minimum_nights` (197), `maximum_nights` (197), `has_availability` (42), `first_review` (1,369), `last_review` (1,369), `license` (1,471), `Reviews.comments` (17) | `2` – `1,471` | **Giữ nguyên `NULL` (`KEEP_NULL`)** (riêng `Reviews.comments` trích thêm cờ `has_comment = 0/1`) | Thông tin không bắt buộc trên Airbnb; giữ `NULL` để phản ánh trung thực độ phủ dữ liệu. |
| **Nhóm D – Cột trống 100% trong toàn bộ snapshot** | 13 cột trong `Listings`: `neighborhood_overview`, `host_since`, `host_response_time`, `host_response_rate`, `host_acceptance_rate`, `host_thumbnail_url`, `host_neighbourhood`, `host_total_listings_count`, `host_verifications`, `neighbourhood`, `bathrooms`, `calendar_updated`, `instant_bookable` | `3,208` (`100%`) | **Giữ ở Staging, lược bỏ khỏi bảng Gold (`EXCLUDE_FROM_GOLD`)** | Không mang thông tin phân tích trong snapshot; loại khỏi Gold giúp schema gọn sạch nhưng vẫn giữ ở Staging để truy vết. |

### 4.2. Quy định xử lý bản ghi trùng (`Duplicates`)
- **Nguyên tắc:** Chỉ kiểm tra và khử trùng theo **đúng khóa tự nhiên (grain)** của từng bảng, tuyệt đối không khử trùng theo cột không phải khóa chính:
  1. `Listings`: Khóa kiểm tra `(id, snapshot_date)`. Hiện tại: `0` dòng trùng trên `3,208` dòng. Quy tắc phòng vệ: nếu phát sinh trùng trong cùng file, giữ bản ghi có `last_scraped` mới nhất và ghi log cảnh báo.
  2. `Calendar`: Khóa kiểm tra `(listing_id, date, snapshot_date)`. Hiện tại: `0` dòng trùng trên `1,170,950` dòng.
  3. `Reviews`:
     - **Không xóa theo `id` đơn lẻ:** Dữ liệu thực tế có `4,809` dòng dư theo `id` riêng lẻ; `2,101` mã review xuất hiện trên nhiều listing, liên quan `197` listing. Các mã này gắn với cùng host trong snapshot quan sát, nhưng chưa xác minh cơ chế chia sẻ review từ metadata nguồn. Không tự xóa theo `id`: khóa ghép là khóa ứng viên quan sát, chưa tự chứng minh tính đúng đắn nghiệp vụ cho mọi nguồn.
     - **Kiểm tra theo khóa ghép `(listing_id, id, snapshot_date)`:** Hiện tại có `0` dòng trùng trên `46,000` dòng. Nếu phát sinh bản ghi trùng cả cặp `(listing_id, id)` trong cùng snapshot, giữ dòng đầu tiên và ghi log.
  4. `Neighbourhoods`: Khóa kiểm tra `(neighbourhood_group, neighbourhood)`. Hiện tại: `0` dòng trùng trên `55` dòng.

### 4.3. Quy định xử lý khóa mồ côi (`Orphan Keys`)
- **Quan hệ 1 (`Calendar.listing_id -> Listings.id`):** Hiện tại `0/1,170,950` dòng mồ côi (`100%` khớp). Quy tắc ETL: nếu có bản ghi `Calendar` mà `listing_id` không tồn tại trong `Listings` của cùng `snapshot_date`, **không nạp vào `fact_calendar`**, chuyển sang bảng/file `etl_orphan_records` và báo cáo trong `TQ-03`.
- **Quan hệ 2 (`Reviews.listing_id -> Listings.id`):** Hiện tại `0/46,000` dòng mồ côi (`100%` khớp). Quy tắc ETL: tương tự, cô lập dòng mồ côi vào `etl_orphan_records` nếu phát sinh.
- **Quan hệ 3 (`Listings.(neighbourhood_group_cleansed, neighbourhood_cleansed) -> Neighbourhoods.(neighbourhood_group, neighbourhood)`):** Hiện tại `3,208/3,208` dòng (`42` cặp khu vực duy nhất) đều khớp `100%` vào `55` dòng của `Neighbourhoods`. Quy tắc ETL: nếu phát sinh khu vực mới chưa có trong `Neighbourhoods`, báo cảnh báo `TQ-03` và ánh xạ về dòng `Unknown Neighbourhood` (`neighbourhood_sk = 0`) thay vì làm rơi bản ghi listing.

### 4.4. Quy định xử lý giá trị ngoại lai (`Outliers`)
- Các giá trị vượt ngưỡng IQR (ví dụ `134/2,725` dòng giá niêm yết `> 683.425 SGD`, `56` dòng `accommodates > 7`, `19` dòng `minimum_nights > 228.5`) **được giữ nguyên 100% trong Silver và Gold**.
- Lý do: Đây là đặc trưng phân phối lệch phải tự nhiên của thị trường lưu trú (penthouse, villa nguyên căn, căn hộ dịch vụ dài hạn tại Singapore). Việc dùng **trung vị (`MEDIAN`)** cho `KPI-02` và `SUP-01` đã đảm bảo tính bền vững thống kê mà không cần xóa dữ liệu thật.

---

## 5. Tổng hợp Khóa dự kiến ở từng lớp dữ liệu

| Tập dữ liệu | Khóa trong file RAW (1 snapshot) | Khóa tự nhiên ở Silver & Gold (Hỗ trợ đa snapshot) | Khóa đại diện (Surrogate Key) ở Gold Warehouse |
|---|---|---|---|
| **Listings** | `id` | `(listing_id, snapshot_date)` | `dim_listing.listing_sk` (`BIGINT UNSIGNED AUTO_INCREMENT`)<br>`fact_listing_snapshot.listing_snapshot_sk` |
| **Calendar** | `(listing_id, date)` | `(listing_id, calendar_date, snapshot_date)` | `fact_calendar.calendar_sk` (`BIGINT UNSIGNED AUTO_INCREMENT`) |
| **Reviews** | `(listing_id, id)` | `(listing_id, review_id, snapshot_date)` | `fact_review.review_sk` (`BIGINT UNSIGNED AUTO_INCREMENT`) |
| **Neighbourhoods** | `(neighbourhood_group, neighbourhood)` | `(neighbourhood_group, neighbourhood_name)` | `dim_neighbourhood.neighbourhood_sk` (`INT UNSIGNED AUTO_INCREMENT`) |
| **Date (Chiều thời gian)** | N/A (sinh từ khoảng ngày `2011-01-01`..`2027-12-31`) | `full_date` (`DATE`) | `dim_date.date_sk` (`INT` định dạng `YYYYMMDD`) |

---

## 6. Cấu trúc Bảng ánh xạ Nguồn $\rightarrow$ Đích (`docs/source_to_target_mapping.csv`)

Toàn bộ **103 cột nguồn** (90 cột `Listings`, 5 cột `Calendar`, 6 cột `Reviews`, 2 cột `Neighbourhoods`) cùng **4 quy tắc sinh cột metadata `snapshot_date`** (tổng cộng **107 dòng quy tắc**) đã được lập thành bảng chuẩn tại [`docs/source_to_target_mapping.csv`](source_to_target_mapping.csv).

**Thống kê phân bổ 103 cột nguồn khi đi qua các lớp:**
- **Tầng Staging (`stg_listings`, `stg_calendar`, `stg_reviews`, `stg_neighbourhoods`):** Giữ toàn bộ **103/103** cột nguồn + các cột metadata nạp dữ liệu.
- **Tầng Silver:**
  - `KEEP_CLEANED`: **84** cột nguồn được làm sạch, chuẩn hóa kiểu và nạp lên tầng Gold Warehouse.
  - `KEEP_AUDIT_ONLY`: **6** cột văn bản dài / URL phụ (`description`, `host_about`, `amenities`, `host_url`, `host_profile_url`, `host_picture_url`) giữ ở Silver để tra cứu, không đưa vào bảng Fact/Dimension Gold nhằm tối ưu hiệu năng truy vấn SQL và dung lượng nạp Power BI.
  - `KEEP_RAW_ONLY_ALL_NULL`: **13** cột trống 100% (`3,208/3,208 NULL`) trong `Listings` được ghi nhận trạng thái và không đưa vào bảng Gold.

---

## 7. Danh sách kịch bản kiểm thử bàn giao cho Hồng và Minh (`tests/etl_test_checklist.csv`)

Bảng dưới đây tóm tắt **20 kịch bản kiểm thử (`TC-01` $\rightarrow$ `TC-20`)** được thiết kế cho giai đoạn ETL & Data Warehouse (chi tiết đầy đủ xem tại [`tests/etl_test_checklist.csv`](../tests/etl_test_checklist.csv)):

| Mã Test | Chỉ số liên quan | Lớp kiểm tra | Đối tượng / Cột kiểm tra | Nội dung & Tiêu chí PASS | Người thực hiện |
|---|---|---|---|---|---|
| `TC-01`..`TC-04` | `TQ-01` | Staging $\rightarrow$ Silver $\rightarrow$ Gold | 4 nguồn dữ liệu | Kiểm tra `0` giá trị `NULL`/rỗng ở toàn bộ các cột bắt buộc (`3,657,376` ô bắt buộc). | Thái / Hồng |
| `TC-05` | `TQ-01` | Silver $\rightarrow$ Gold | `listed_price_sgd`, `review_scores_rating` | Bảo toàn đúng số lượng `NULL` hợp lệ (`483` dòng giá `NULL`, `1,369` dòng điểm `NULL`), không tự điền `0`. | Hồng / Minh |
| `TC-06`..`TC-09` | `TQ-02` | Silver $\rightarrow$ Gold | 4 bảng theo khóa grain | `COUNT(*) - COUNT(DISTINCT grain_key) = 0` trên cả `dim_listing` (`3,208`), `fact_calendar` (`1,170,950`), `fact_review` (`46,000` theo `(listing_id, review_id, snapshot_date)`), `dim_neighbourhood` (`55`). | Minh / Hồng |
| `TC-10`..`TC-13` | `TQ-03` | Silver $\rightarrow$ Gold | Khóa ngoại `FK` giữa các Fact và Dimension | `100%` bản ghi con khớp khóa cha (`0` orphan key ở `listing_sk`, `neighbourhood_sk`, `date_sk`). | Minh / Hồng |
| `TC-14` | `TQ-04`, `KPI-02` | Silver $\rightarrow$ Gold | `listed_price_raw_amount`, `quote_currency`, `listed_price_sgd` | Xác nhận `2,728` dòng có giá số, `2,855` dòng `SGD`, giao nhau đúng **`2,725` dòng** hợp lệ với `Median = 202.83 SGD` (tách riêng 3 dòng thiếu currency trong JSON). | Thái / Minh / Hồng |
| `TC-15` | `TQ-04` | Silver $\rightarrow$ Gold | `accommodates`, `minimum_nights_avg_ntm`, `maximum_nights_avg_ntm` | Xác nhận `accommodates` là `INT` (`1`–`16`) và hai cột `*_avg_ntm` giữ nguyên phần thập phân `DECIMAL(10,2)` cho `320` và `426` dòng lẻ. | Thái / Hồng |
| `TC-16` | `TQ-04`, `KPI-04` | Silver $\rightarrow$ Gold | 5 cột boolean (`is_available`, `host_is_superhost`, ...) | `100%` giá trị nằm trong `{0, 1, NULL}`; `fact_calendar.is_available` có đúng `900,960` dòng `= 1` và `269,990` dòng `= 0`. | Thái / Hồng |
| `TC-17` | `TQ-04`, `KPI-05` | Silver $\rightarrow$ Gold | `review_scores_*` (7 cột) | `100%` giá trị không `NULL` (`1,839` dòng) nằm trong miền `[1.00, 5.00]`. | Thái / Hồng |
| `TC-18` | `TQ-04` | Raw $\rightarrow$ Silver $\rightarrow$ Gold | Đối chiếu số dòng (Row Count) | Khớp tuyệt đối số dòng qua các lớp: `Listings = 3,208`, `Calendar = 1,170,950`, `Reviews = 46,000`, `Neighbourhoods = 55`. | Thái / Minh / Hồng |
| `TC-19` | `KPI-01..05`, `SUP-01..02` | Silver (Pandas) vs Gold (SQL) | 7 chỉ tiêu phân tích | Chênh lệch bằng `0` giữa kết quả truy vấn SQL trên MySQL Gold và tính toán độc lập bằng Pandas trên Silver. | Minh / Hồng |
| `TC-20` | `TQ-05` | End-to-End Pipeline | Chạy lại lần 2 cùng snapshot `2026-09-23` | Số dòng mọi bảng và giá trị 7 KPI sau lần chạy thứ 2 khớp `100%` với lần chạy thứ 1 (`PASS` tính nhất quán khi chạy lại). | Thái / Minh / Tiên |


## 8. Phạm vi nghiệm thu và đối chiếu Gold

Task 2.4 bàn giao quy tắc/mapping/checklist; Task 2.5 bàn giao grain và schema
nháp. Không cần triển khai xong pipeline để hoàn tất hai bản thiết kế này.
`tests/task_2_4_2_5_verification.csv` chỉ ghi kiểm tra raw và thiết kế tĩnh;
V-12 kiểm tra mapping đích/schema CSV/DDL, không xác nhận đã tạo bảng hoặc nạp Gold.

Quy trình chạy SELECT MySQL, xuất CSV và đối chiếu độc lập với Pandas nằm tại
[`docs/gold_reconciliation.md`](gold_reconciliation.md). SQL/ETL và TC-20 còn
phải chạy trên môi trường nhóm trước khi nghiệm thu triển khai. Không thay
`NOT_RUN` bằng `PASS` khi chưa có kết quả thực tế.
