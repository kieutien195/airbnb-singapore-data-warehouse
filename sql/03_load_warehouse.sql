-- =============================================================================
-- Dự án: Xây dựng Nhà kho dữ liệu & Báo cáo BI phân tích Airbnb Singapore
-- Phân hệ: Tầng Kho Dữ liệu Đa chiều (Gold Star Schema / Fact Constellation)
-- Tệp SQL: sql/03_load_warehouse.sql
-- Nhiệm vụ WBS: Task 3.6 - Xây dựng quy trình load Dimension và Fact
-- Người thực hiện: Minh (Database Administrator / Data Modeler)
-- Phối hợp: Thái (Data Engineer / ETL), Hồng (QA / DA)
--
-- Mục tiêu kỹ thuật:
-- 1. Nạp Dimension trước Fact theo đúng thứ tự phụ thuộc khóa ngoại (FK):
--    - dim_date -> dim_neighbourhood -> dim_listing -> fact_listing_snapshot -> fact_calendar -> fact_review.
-- 2. Ánh xạ khóa tự nhiên (Business Key) sang khóa đại diện (Surrogate Key).
-- 3. Ràng buộc toàn vẹn, kiểm soát bản ghi trùng lặp và không để lại khóa mồ côi.
-- 4. Đảm bảo tính khả lặp (Idempotency - TQ-05): Chạy lại cùng snapshot không làm tăng số dòng.
-- 5. Ghi log số dòng nạp và kiểm toán vào bảng etl_load_log.
-- =============================================================================

-- Chọn schema đích theo cấu hình biến môi trường trước khi chạy (ví dụ USE airbnb_sg_2026;)

-- -----------------------------------------------------------------------------
-- 0. KHỞI TẠO BẢNG KIỂM TOÁN NẠP KHO: etl_load_log
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS etl_load_log (
    log_id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    step_order          TINYINT UNSIGNED NOT NULL COMMENT 'Thứ tự nạp (1..6)',
    table_name          VARCHAR(50)      NOT NULL COMMENT 'Tên bảng đích trong Gold Warehouse',
    table_type          VARCHAR(20)      NOT NULL COMMENT 'DIMENSION hoặc FACT',
    snapshot_date       DATE             NOT NULL COMMENT 'Ngày snapshot dữ liệu',
    rows_source         INT UNSIGNED     NOT NULL COMMENT 'Số dòng dữ liệu nguồn/Silver đầu vào',
    rows_loaded         INT UNSIGNED     NOT NULL COMMENT 'Số dòng nạp thành công vào MySQL',
    rows_failed         INT UNSIGNED     NOT NULL DEFAULT 0 COMMENT 'Số dòng lỗi (nếu có)',
    duration_seconds    DECIMAL(8,2)     NOT NULL COMMENT 'Thời gian nạp tính bằng giây',
    status              VARCHAR(20)      NOT NULL COMMENT 'SUCCESS / FAIL / SKIPPED',
    started_at          DATETIME         NOT NULL COMMENT 'Thời điểm bắt đầu nạp',
    completed_at        DATETIME         NOT NULL COMMENT 'Thời điểm hoàn thành',
    notes               TEXT             NULL     COMMENT 'Ghi chú kiểm toán',
    INDEX idx_load_snapshot (snapshot_date, table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Bảng kiểm toán quy trình nạp kho dữ liệu Warehouse (Task 3.6)';


-- =============================================================================
-- BƯỚC 1: NẠP CHIỀU THỜI GIAN: dim_date (2011-01-01 .. 2027-12-31)
-- Grain: 1 dòng = 1 ngày dương lịch (Tổng cộng 6,209 dòng ngày)
-- =============================================================================
SET SESSION cte_max_recursion_depth = 10000;

INSERT INTO dim_date (
    date_sk, full_date, day_of_month, day_of_week_iso, day_name,
    is_weekend, week_of_year, month_num, month_name, `year_month`,
    quarter_num, year_quarter, year_num
)
WITH RECURSIVE date_series AS (
    SELECT CAST('2011-01-01' AS DATE) AS dt
    UNION ALL
    SELECT dt + INTERVAL 1 DAY FROM date_series WHERE dt < '2027-12-31'
)
SELECT
    CAST(DATE_FORMAT(dt, '%Y%m%d') AS SIGNED) AS date_sk,
    dt AS full_date,
    DAY(dt) AS day_of_month,
    WEEKDAY(dt) + 1 AS day_of_week_iso,
    DATE_FORMAT(dt, '%W') AS day_name,
    CASE WHEN WEEKDAY(dt) IN (5, 6) THEN 1 ELSE 0 END AS is_weekend,
    WEEKOFYEAR(dt) AS week_of_year,
    MONTH(dt) AS month_num,
    DATE_FORMAT(dt, '%M') AS month_name,
    DATE_FORMAT(dt, '%Y-%m') AS `year_month`,
    QUARTER(dt) AS quarter_num,
    CONCAT(YEAR(dt), '-Q', QUARTER(dt)) AS year_quarter,
    YEAR(dt) AS year_num
FROM date_series
ON DUPLICATE KEY UPDATE full_date = VALUES(full_date);


-- =============================================================================
-- BƯỚC 2: NẠP CHIỀU PHÂN CẤP ĐỊA LÝ: dim_neighbourhood
-- Grain: 1 dòng = 1 khu vực quy hoạch (55 khu vực quy hoạch tại Singapore)
-- =============================================================================
INSERT INTO dim_neighbourhood (
    neighbourhood_group, neighbourhood_name, snapshot_date
)
SELECT DISTINCT
    TRIM(neighbourhood_group) AS neighbourhood_group,
    TRIM(neighbourhood) AS neighbourhood_name,
    snapshot_date
FROM stg_neighbourhoods
WHERE snapshot_date = '2026-09-23'
ON DUPLICATE KEY UPDATE snapshot_date = VALUES(snapshot_date);


-- =============================================================================
-- BƯỚC 3: NẠP CHIỀU MÔ TẢ TIN ĐĂNG: dim_listing
-- Grain: 1 dòng = 1 tin đăng tại 1 snapshot_date (3,208 dòng)
-- Ánh xạ khóa ngoại: neighbourhood_sk từ dim_neighbourhood, snapshot_date_sk từ dim_date
-- =============================================================================
INSERT INTO dim_listing (
    listing_id, snapshot_date, snapshot_date_sk, neighbourhood_sk,
    scrape_id, last_scraped_date, calendar_last_scraped_date, source_type,
    listing_name, listing_url, picture_url, property_type, room_type,
    accommodates, bedrooms, beds, bathrooms_text, latitude, longitude,
    has_availability, license, host_id, host_profile_id, host_name,
    host_location, host_is_superhost, host_has_profile_pic,
    host_identity_verified, hosts_time_as_user_years, hosts_time_as_user_months,
    hosts_time_as_host_years, hosts_time_as_host_months,
    first_review_date, last_review_date
)
SELECT
    l.id AS listing_id,
    l.snapshot_date,
    CAST(DATE_FORMAT(l.snapshot_date, '%Y%m%d') AS SIGNED) AS snapshot_date_sk,
    n.neighbourhood_sk,
    l.scrape_id,
    l.last_scraped AS last_scraped_date,
    l.calendar_last_scraped AS calendar_last_scraped_date,
    l.source AS source_type,
    COALESCE(TRIM(l.name), 'Unknown') AS listing_name,
    l.listing_url,
    l.picture_url,
    l.property_type,
    l.room_type,
    l.accommodates,
    l.bedrooms,
    l.beds,
    l.bathrooms_text,
    CAST(l.latitude AS DECIMAL(10,7)) AS latitude,
    CAST(l.longitude AS DECIMAL(10,7)) AS longitude,
    CASE WHEN l.has_availability = 't' THEN 1 WHEN l.has_availability = 'f' THEN 0 ELSE NULL END AS has_availability,
    l.license,
    l.host_id,
    l.host_profile_id,
    COALESCE(TRIM(l.host_name), 'Unknown') AS host_name,
    l.host_location,
    CASE WHEN l.host_is_superhost = 't' THEN 1 WHEN l.host_is_superhost = 'f' THEN 0 ELSE NULL END AS host_is_superhost,
    CASE WHEN l.host_has_profile_pic = 't' THEN 1 WHEN l.host_has_profile_pic = 'f' THEN 0 ELSE NULL END AS host_has_profile_pic,
    CASE WHEN l.host_identity_verified = 't' THEN 1 WHEN l.host_identity_verified = 'f' THEN 0 ELSE NULL END AS host_identity_verified,
    l.hosts_time_as_user_years,
    l.hosts_time_as_user_months,
    l.hosts_time_as_host_years,
    l.hosts_time_as_host_months,
    l.first_review AS first_review_date,
    l.last_review AS last_review_date
FROM stg_listings l
JOIN dim_neighbourhood n
  ON l.neighbourhood_cleansed = n.neighbourhood_name
WHERE l.snapshot_date = '2026-09-23'
ON DUPLICATE KEY UPDATE
    listing_name = VALUES(listing_name),
    last_scraped_date = VALUES(last_scraped_date);


-- =============================================================================
-- BƯỚC 4: NẠP BẢNG SỰ KIỆN ĐỊNH LƯỢNG TIN ĐĂNG: fact_listing_snapshot
-- Grain: 1 dòng = 1 listing tại 1 snapshot_date (3,208 dòng)
-- Phục vụ: KPI-01, KPI-02, KPI-03, KPI-05, SUP-01
-- =============================================================================
INSERT INTO fact_listing_snapshot (
    listing_sk, neighbourhood_sk, snapshot_date_sk, listing_id, snapshot_date,
    listed_price_raw_amount, quote_currency, is_price_sgd_verified, listed_price_sgd,
    price_quote_price_per_night, price_quote_total_price, price_quote_checkin_date,
    price_quote_checkout_date, minimum_nights, maximum_nights, minimum_minimum_nights,
    maximum_minimum_nights, minimum_maximum_nights, maximum_maximum_nights,
    minimum_nights_avg_ntm, maximum_nights_avg_ntm, availability_30, availability_60,
    availability_90, availability_365, availability_eoy, number_of_reviews,
    number_of_reviews_ltm, number_of_reviews_l30d, number_of_reviews_ly,
    reviews_per_month, review_scores_rating, review_scores_accuracy,
    review_scores_cleanliness, review_scores_checkin, review_scores_communication,
    review_scores_location, review_scores_value, host_listings_count,
    calculated_host_listings_count, calculated_host_listings_count_entire_homes,
    calculated_host_listings_count_private_rooms, calculated_host_listings_count_shared_rooms,
    estimated_occupancy_l365d, estimated_revenue_l365d
)
SELECT
    d.listing_sk,
    d.neighbourhood_sk,
    d.snapshot_date_sk,
    l.id AS listing_id,
    l.snapshot_date,
    -- Trích xuất giá dạng số sau khi bỏ ký hiệu tiền tệ
    CAST(REPLACE(REPLACE(l.price, '$', ''), ',', '') AS DECIMAL(12,2)) AS listed_price_raw_amount,
    -- Kiểm tra mã tiền tệ quote_currency từ chuỗi JSON price_quote_raw
    CASE WHEN l.price_quote_raw LIKE '%"currency": "SGD"%' THEN 'SGD'
         WHEN l.price_quote_raw LIKE '%"currency": "USD"%' THEN 'USD'
         ELSE NULL END AS quote_currency,
    -- Đánh dấu cờ xác minh giá SGD hợp lệ
    CASE WHEN l.price IS NOT NULL
          AND CAST(REPLACE(REPLACE(l.price, '$', ''), ',', '') AS DECIMAL(12,2)) > 0
          AND l.price_quote_raw LIKE '%"currency": "SGD"%' THEN 1 ELSE 0 END AS is_price_sgd_verified,
    -- Giá SGD hợp lệ dùng tính KPI-02
    CASE WHEN l.price IS NOT NULL
          AND CAST(REPLACE(REPLACE(l.price, '$', ''), ',', '') AS DECIMAL(12,2)) > 0
          AND l.price_quote_raw LIKE '%"currency": "SGD"%'
         THEN CAST(REPLACE(REPLACE(l.price, '$', ''), ',', '') AS DECIMAL(12,2))
         ELSE NULL END AS listed_price_sgd,
    l.price_quote_price_per_night,
    l.price_quote_total_price,
    l.price_quote_checkin_date,
    l.price_quote_checkout_date,
    l.minimum_nights,
    l.maximum_nights,
    l.minimum_minimum_nights,
    l.maximum_minimum_nights,
    l.minimum_maximum_nights,
    l.maximum_maximum_nights,
    l.minimum_nights_avg_ntm,
    l.maximum_nights_avg_ntm,
    l.availability_30,
    l.availability_60,
    l.availability_90,
    l.availability_365,
    l.availability_eoy,
    l.number_of_reviews,
    l.number_of_reviews_ltm,
    l.number_of_reviews_l30d,
    l.number_of_reviews_ly,
    l.reviews_per_month,
    l.review_scores_rating,
    l.review_scores_accuracy,
    l.review_scores_cleanliness,
    l.review_scores_checkin,
    l.review_scores_communication,
    l.review_scores_location,
    l.review_scores_value,
    l.host_listings_count,
    l.calculated_host_listings_count,
    l.calculated_host_listings_count_entire_homes,
    l.calculated_host_listings_count_private_rooms,
    l.calculated_host_listings_count_shared_rooms,
    l.estimated_occupancy_l365d,
    l.estimated_revenue_l365d
FROM stg_listings l
JOIN dim_listing d
  ON l.id = d.listing_id AND l.snapshot_date = d.snapshot_date
WHERE l.snapshot_date = '2026-09-23'
ON DUPLICATE KEY UPDATE
    listed_price_sgd = VALUES(listed_price_sgd),
    review_scores_rating = VALUES(review_scores_rating);


-- =============================================================================
-- BƯỚC 5: NẠP BẢNG SỰ KIỆN LỊCH PHÒNG: fact_calendar
-- Grain: 1 dòng = 1 listing tại 1 ngày lịch trong 1 snapshot (1,170,950 dòng)
-- Phục vụ: KPI-04 (Tỷ lệ đêm mở lịch 365 ngày)
-- =============================================================================
INSERT INTO fact_calendar (
    listing_sk, neighbourhood_sk, calendar_date_sk, snapshot_date_sk,
    listing_id, calendar_date, snapshot_date, is_available,
    minimum_nights, maximum_nights
)
SELECT
    d.listing_sk,
    d.neighbourhood_sk,
    CAST(DATE_FORMAT(c.date, '%Y%m%d') AS SIGNED) AS calendar_date_sk,
    CAST(DATE_FORMAT(c.snapshot_date, '%Y%m%d') AS SIGNED) AS snapshot_date_sk,
    c.listing_id,
    c.date AS calendar_date,
    c.snapshot_date,
    CASE WHEN c.available = 't' THEN 1 ELSE 0 END AS is_available,
    c.minimum_nights,
    c.maximum_nights
FROM stg_calendar c
JOIN dim_listing d
  ON c.listing_id = d.listing_id AND c.snapshot_date = d.snapshot_date
WHERE c.snapshot_date = '2026-09-23'
ON DUPLICATE KEY UPDATE is_available = VALUES(is_available);


-- =============================================================================
-- BƯỚC 6: NẠP BẢNG SỰ KIỆN ĐÁNH GIÁ: fact_review
-- Grain: 1 dòng = 1 review của 1 listing tại snapshot (46,000 dòng)
-- Phục vụ: SUP-02 (Tổng số lượt đánh giá lịch sử)
-- =============================================================================
INSERT INTO fact_review (
    listing_sk, neighbourhood_sk, review_date_sk, snapshot_date_sk,
    listing_id, review_id, review_date, snapshot_date,
    reviewer_id, reviewer_name, has_comment, comment_length, review_count
)
SELECT
    d.listing_sk,
    d.neighbourhood_sk,
    CAST(DATE_FORMAT(r.date, '%Y%m%d') AS SIGNED) AS review_date_sk,
    CAST(DATE_FORMAT(r.snapshot_date, '%Y%m%d') AS SIGNED) AS snapshot_date_sk,
    r.listing_id,
    r.id AS review_id,
    r.date AS review_date,
    r.snapshot_date,
    r.reviewer_id,
    COALESCE(TRIM(r.reviewer_name), 'Anonymous') AS reviewer_name,
    CASE WHEN r.comments IS NOT NULL AND CHAR_LENGTH(TRIM(r.comments)) > 0 THEN 1 ELSE 0 END AS has_comment,
    COALESCE(CHAR_LENGTH(r.comments), 0) AS comment_length,
    1 AS review_count
FROM stg_reviews r
JOIN dim_listing d
  ON r.listing_id = d.listing_id AND r.snapshot_date = d.snapshot_date
WHERE r.snapshot_date = '2026-09-23'
ON DUPLICATE KEY UPDATE review_date = VALUES(review_date);


-- =============================================================================
-- BƯỚC 7: KIỂM TOÁN ĐỐI CHIẾU SỐ LƯỢNG DÒNG (ROW COUNT RECONCILIATION)
-- =============================================================================
SELECT
    'dim_date' AS table_name,
    COUNT(*) AS row_count,
    6209 AS expected_count,
    CASE WHEN COUNT(*) = 6209 THEN 'PASS' ELSE 'FAIL' END AS status
FROM dim_date
UNION ALL
SELECT
    'dim_neighbourhood', COUNT(*), 55,
    CASE WHEN COUNT(*) = 55 THEN 'PASS' ELSE 'FAIL' END
FROM dim_neighbourhood
UNION ALL
SELECT
    'dim_listing', COUNT(*), 3208,
    CASE WHEN COUNT(*) = 3208 THEN 'PASS' ELSE 'FAIL' END
FROM dim_listing WHERE snapshot_date = '2026-09-23'
UNION ALL
SELECT
    'fact_listing_snapshot', COUNT(*), 3208,
    CASE WHEN COUNT(*) = 3208 THEN 'PASS' ELSE 'FAIL' END
FROM fact_listing_snapshot WHERE snapshot_date = '2026-09-23'
UNION ALL
SELECT
    'fact_calendar', COUNT(*), 1170950,
    CASE WHEN COUNT(*) = 1170950 THEN 'PASS' ELSE 'FAIL' END
FROM fact_calendar WHERE snapshot_date = '2026-09-23'
UNION ALL
SELECT
    'fact_review', COUNT(*), 46000,
    CASE WHEN COUNT(*) = 46000 THEN 'PASS' ELSE 'FAIL' END
FROM fact_review WHERE snapshot_date = '2026-09-23';


-- =============================================================================
-- BƯỚC 8: KIỂM TRA KHÓA MỒ CÔI (ORPHAN KEY VERIFICATION)
-- =============================================================================
SELECT
    'fact_listing_snapshot -> dim_listing' AS relationship,
    COUNT(*) AS orphan_count,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM fact_listing_snapshot f
LEFT JOIN dim_listing d
  ON f.listing_sk = d.listing_sk
 AND f.snapshot_date_sk = d.snapshot_date_sk
 AND f.neighbourhood_sk = d.neighbourhood_sk
WHERE d.listing_sk IS NULL
UNION ALL
SELECT
    'fact_calendar -> dim_listing', COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM fact_calendar f
LEFT JOIN dim_listing d
  ON f.listing_sk = d.listing_sk
 AND f.snapshot_date_sk = d.snapshot_date_sk
 AND f.neighbourhood_sk = d.neighbourhood_sk
WHERE d.listing_sk IS NULL
UNION ALL
SELECT
    'fact_review -> dim_listing', COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM fact_review f
LEFT JOIN dim_listing d
  ON f.listing_sk = d.listing_sk
 AND f.snapshot_date_sk = d.snapshot_date_sk
 AND f.neighbourhood_sk = d.neighbourhood_sk
WHERE d.listing_sk IS NULL
UNION ALL
SELECT
    'dim_listing -> dim_neighbourhood', COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM dim_listing d
LEFT JOIN dim_neighbourhood n ON d.neighbourhood_sk = n.neighbourhood_sk
WHERE n.neighbourhood_sk IS NULL;


-- =============================================================================
-- BƯỚC 9: TRUY VẤN XÁC THỰC KHO DỮ LIỆU & 5 KPI CỐT LÕI
-- =============================================================================
-- KPI-01: Tổng số tin đăng hoạt động
SELECT
    'KPI-01' AS kpi_id,
    'Active Listings' AS kpi_name,
    COUNT(DISTINCT listing_id) AS metric_value,
    '3,208 listings' AS note
FROM fact_listing_snapshot
WHERE snapshot_date = '2026-09-23'

UNION ALL

-- KPI-02: Số tin niêm yết SGD hợp lệ
SELECT
    'KPI-02' AS kpi_id,
    'Valid SGD Listings' AS kpi_name,
    COUNT(*) AS metric_value,
    '2,725 verified listings (Median: 202.83 SGD)' AS note
FROM fact_listing_snapshot
WHERE snapshot_date = '2026-09-23'
  AND is_price_sgd_verified = 1
  AND listed_price_sgd > 0

UNION ALL

-- KPI-04: Tỷ lệ mở lịch 365 ngày
SELECT
    'KPI-04' AS kpi_id,
    'Calendar Availability Rate' AS kpi_name,
    ROUND(SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS metric_value,
    '76.94% available nights (2026-09-25 .. 2027-09-25)' AS note
FROM fact_calendar
WHERE snapshot_date = '2026-09-23'
  AND calendar_date BETWEEN '2026-09-25' AND '2027-09-25'

UNION ALL

-- KPI-05: Điểm đánh giá bình quân
SELECT
    'KPI-05' AS kpi_id,
    'Average Rating' AS kpi_name,
    ROUND(AVG(review_scores_rating), 2) AS metric_value,
    'Thang điểm 1..5 trên 1,839 tin có đánh giá' AS note
FROM fact_listing_snapshot
WHERE snapshot_date = '2026-09-23'
  AND review_scores_rating IS NOT NULL;

