# Hướng dẫn & Tài liệu Kỹ thuật: SQL Views Tính toán KPI (Task 3.7)

Tài liệu này thuyết minh chi tiết việc thiết kế, cài đặt và kiểm chuẩn các **SQL Views tính toán KPI từ Kho Dữ liệu (Gold Layer)** theo yêu cầu của dự án **Airbnb Singapore Data Warehouse**.

---

## 1. Danh mục Bàn giao (Deliverables)

1. **`sql/04_kpi_views.sql`**: Script DDL MySQL 8.0 khởi tạo 12 Views (7 Core & Supplemental Views, 3 Regional Breakdown Views, 1 Executive Summary View và 1 BI Analytical Base View).
2. **`kpi_sql_results.csv`** (và bản sao tại `outputs/kpi_sql_results.csv`): Bảng kết quả truy vấn đối chiếu số liệu KPI toàn sàn và phân rã khu vực, đo lường thời gian thực thi (query time ms) và kiểm chuẩn 100% PASS so với Raw Data.
3. **`scripts/generate_kpi_results.py`**: Pipeline tự động hóa triển khai DDL views, thực thi benchmark và xuất kết quả ra file CSV.

---

## 2. Đặc tả Chi tiết các Chỉ tiêu KPI (Grain, Filter, Denominator, NULL Handling)

| Mã KPI | Tên Chỉ tiêu | Grain | Bảng Nguồn (Gold) | Bộ lọc (Filters) | Mẫu số (Denominator) | Xử lý NULL | Kết quả Thực tế (Observed) | Trạng thái Đối chiếu |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **KPI-01** | Active Listings Count | 1 listing tại snapshot | `fact_listing_snapshot` | `snapshot_date = '2026-09-23'` AND `listing_id IS NOT NULL` | Không áp dụng (Đếm tuyệt đối) | Bỏ qua listing_id NULL | **3,208 listings** | **PASS (0.00)** |
| **KPI-02** | Median Listed Price SGD | 1 listing tại snapshot | `fact_listing_snapshot` | `quote_currency = 'SGD'` AND `is_price_sgd_verified = 1` AND `listed_price_sgd > 0` | Không áp dụng (Độ phủ: 2,725 / 3,208 = 84.94%) | Loại bỏ giá NULL / tiền tệ rác; tính trung vị bằng CTE Window Function | **202.83 SGD/đêm** | **PASS (0.00)** |
| **KPI-03** | Room Type Share | 1 room_type tại snapshot | `fact_listing_snapshot` JOIN `dim_listing` | `snapshot_date = '2026-09-23'` AND `room_type IS NOT NULL` | Toàn sàn: 3,208 listing (`SUM(COUNT(*)) OVER ()`). Phân vùng: Tổng listing theo vùng (`PARTITION BY neighbourhood_group`) | Loại bỏ room_type trống; mẫu số bọc `NULLIF(..., 0)` | **Private room: 56.95%**<br>**Entire home: 38.40%**<br>**Hotel room: 2.59%**<br>**Shared room: 2.06%** | **PASS (0.00)** |
| **KPI-04** | Calendar Available Nights Ratio | 1 listing-ngày trong snapshot | `fact_calendar` | `snapshot_date = '2026-09-23'` AND `calendar_date BETWEEN '2026-09-25' AND '2027-09-25'` (366 ngày) | Tổng số bản ghi listing-ngày trong cửa sổ: **1,170,950 đêm** | Mẫu số bọc `NULLIF(COUNT(*), 0)`; tử số dùng `SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END)` | **76.94%** (900,960 / 1,170,950 đêm) | **PASS (0.00)** |
| **KPI-05** | Average Overall Review Score | 1 rated listing tại snapshot | `fact_listing_snapshot` | `snapshot_date = '2026-09-23'` AND `review_scores_rating BETWEEN 1.00 AND 5.00` | Số listing có điểm: **1,839 listing** (Độ phủ: 57.33%) | **KHÔNG** thay thế NULL bằng 0; loại trừ tự nhiên trong hàm `AVG()` | **4.54 / 5.00** | **PASS (0.00)** |
| **SUP-01** | Median Review Count per Listing | 1 listing tại snapshot | `fact_listing_snapshot` | `snapshot_date = '2026-09-23'` AND `number_of_reviews >= 0` | Toàn bộ 3,208 listing | Giữ nguyên giá trị 0 của 1,369 listing chưa có review; tính trung vị bằng CTE | **1.00 review/listing** | **PASS (0.00)** |
| **SUP-02** | Review Records in Period | 1 review record | `fact_review` | `snapshot_date = '2026-09-23'` (cặp `listing_id`, `review_id` duy nhất) | Không áp dụng | Đếm bản ghi thực tế; ngày từ 2011-05-04 đến 2026-09-25 | **46,000 reviews** | **PASS (0.00)** |

---

## 3. Chiến lược Ngăn chặn Bùng nổ Tích Descartes (Anti-Cartesian Fan-Out)

Một lỗi rất phổ biến khi viết SQL tổng hợp từ Data Warehouse là thực hiện `JOIN` đồng thời giữa bảng Listing với hai bảng Fact con có quan hệ 1-N là `fact_calendar` (1,170,950 dòng) và `fact_review` (46,000 dòng):
$$\text{Cartesian Rows} = 3,208 \times 365 \times \text{reviews per listing} \gg 50,000,000 \text{ dòng!}$$
Hậu quả là:
1. Số đếm listing bị nhân bản hàng chục nghìn lần, làm sai lệch hoàn toàn KPI-01, KPI-02, KPI-03, KPI-05.
2. Tiêu tốn hàng gigabyte RAM máy chủ MySQL và làm treo ứng dụng BI.

### Giải pháp Kiến trúc đã Triển khai:
1. **Đối với các View đo lường độc lập (`vw_kpi01` .. `vw_kpi05`, `vw_sup01`, `vw_sup02`)**: Mỗi view chỉ truy vấn đúng bảng Fact tương ứng theo Grain quy chuẩn.
2. **Đối với View dữ liệu tổng hợp BI (`vw_gold_bi_analytical_base`)**:
   - Sử dụng CTE `cal_agg` để gom nhóm và tính toán các chỉ tiêu lịch (`calendar_total_nights`, `calendar_available_nights`, `calendar_availability_ratio_pct`) theo `listing_sk` trước.
   - Sử dụng CTE `rev_agg` để gom nhóm và tính toán các chỉ tiêu đánh giá (`historical_review_records`, `earliest_review_date`, `latest_review_date`) theo `listing_sk` trước.
   - Sau đó mới `LEFT JOIN` với `fact_listing_snapshot`, `dim_listing` và `dim_neighbourhood`.
   - Kết quả: **Chính xác tuyệt đối 3,208 dòng (1 dòng = 1 listing)**, bảo toàn 100% tính toàn vẹn dữ liệu.

---

## 4. Kết quả Đo lường Hiệu năng Truy vấn (Query Benchmark)

Kiểm thử thực tế trên hệ cơ sở dữ liệu MySQL 8.0.46 (InnoDB Engine):

| View / Query | Số dòng kết quả | Thời gian thực thi (ms) | Nhận xét hiệu năng |
| :--- | :---: | :---: | :--- |
| `vw_kpi01_active_listings` | 1 | **2.55 ms** | Cực nhanh; tận dụng index PK `snapshot_date_sk`. |
| `vw_kpi02_median_price_sgd` | 1 | **5.69 ms** | CTE Window function quét 2,725 dòng và tính trung vị dưới 6 ms. |
| `vw_kpi03_room_type_share` | 4 | **7.03 ms** | Nhóm 4 loại phòng với hàm `SUM() OVER ()` tối ưu. |
| `vw_kpi03_regional_room_type_share` | 13 | **18.21 ms** | Phân rã 5 vùng x loại phòng hoàn tất tức thì. |
| `vw_kpi04_calendar_availability` | 1 | **1,177.78 ms** | Quét và tính toán trên **1,170,950 dòng lịch**, hoàn thành ~1.1 giây nhờ index `idx_fc_listing_caldate`. |
| `vw_kpi04_regional_calendar_availability` | 5 | **2,980.93 ms** | Quét 1.17M dòng kèm JOIN phân cấp địa lý hoàn thành dưới 3 giây. |
| `vw_kpi05_average_rating` | 1 | **1.74 ms** | Tính trung bình trên 1,839 dòng có điểm chỉ tốn 1.74 ms. |
| `vw_sup01_median_review_count` | 1 | **7.25 ms** | CTE Window function trung vị trên 3,208 dòng hoàn thành trong 7.25 ms. |
| `vw_sup02_review_records_period` | 1 | **28.71 ms** | Đếm trên 46,000 bản ghi review lịch sử tốn chưa tới 30 ms. |
| `vw_kpi_summary_overall` | 10 | **35.12 ms** | View báo cáo tổng hợp hợp nhất các chỉ tiêu toàn sàn hiển thị ngay lập tức. |

---

## 5. Hướng dẫn Kết nối Công cụ BI (Power BI / Tableau / Looker Studio)

Dữ liệu Gold Warehouse đã sẵn sàng 100% để kết nối trực tiếp với công cụ BI thông qua MySQL Connector:

1. **Kết nối trực tiếp View BI Base**:
   - Tên View: `airbnb_sg_2026.vw_gold_bi_analytical_base`
   - Grain: `listing_id` (3,208 dòng, 33 cột thuộc tính và chỉ số định lượng).
   - Thiết lập trong Power BI / Tableau:
     + Chiều phân tích (Dimensions): `neighbourhood_group`, `neighbourhood_name`, `room_type`, `property_type`, `host_is_superhost`.
     + Bản đồ địa lý (Geo): `latitude`, `longitude`.
     + Thước đo (Measures): `listed_price_sgd`, `calendar_availability_ratio_pct`, `review_scores_rating`, `number_of_reviews`.
2. **Kết nối các View KPI Tổng hợp**:
   - Sử dụng `vw_kpi_summary_overall` để tạo các thẻ KPI Card trên trang tổng quan (Executive Dashboard).
   - Sử dụng `vw_kpi03_regional_room_type_share` và `vw_kpi04_regional_calendar_availability` để vẽ các biểu đồ phân tích cơ cấu và so sánh giữa 5 vùng địa lý Singapore.
