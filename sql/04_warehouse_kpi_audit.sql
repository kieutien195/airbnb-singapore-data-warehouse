-- Task 3.6: kiểm tra chỉ đọc trên Gold đã nạp.
-- Đối chiếu Raw–Gold độc lập: 03_validate_gold_against_raw.sql.

-- 9.1 Bảng tổng hợp KPI cốt lõi và chỉ tiêu hỗ trợ (Overall KPI Summary)
SELECT
    'KPI-01' AS kpi_id,
    'Active Listings' AS kpi_name,
    CAST(COUNT(DISTINCT listing_id) AS CHAR) AS metric_value,
    'Listing' AS unit,
    'Một listing tại snapshot' AS grain,
    CONCAT(COUNT(DISTINCT listing_id), ' listings') AS note
FROM fact_listing_snapshot
WHERE snapshot_date = '2026-09-23'

UNION ALL

-- KPI-02: Trung vị giá niêm yết mỗi đêm (chỉ tính giá SGD đã xác minh)
SELECT
    'KPI-02',
    'Median Listed Price (SGD)',
    CAST(ROUND(AVG(listed_price_sgd), 2) AS CHAR),
    'SGD/đêm',
    'Một listing tại snapshot',
    CONCAT('Calculated over ', MAX(n), ' verified SGD listings (quote_currency = SGD)')
FROM (
    SELECT listed_price_sgd,
           ROW_NUMBER() OVER (ORDER BY listed_price_sgd) AS rn,
           COUNT(*) OVER () AS n
    FROM fact_listing_snapshot
    WHERE snapshot_date = '2026-09-23'
      AND is_price_sgd_verified = 1
      AND quote_currency = 'SGD'
      AND listed_price_sgd > 0
) p
WHERE rn IN (FLOOR((n+1)/2), FLOOR((n+2)/2))

UNION ALL

-- KPI-04: Tỷ lệ mở lịch 365 ngày (cố định cửa sổ 2026-09-25 đến 2027-09-25)
SELECT
    'KPI-04',
    'Calendar Availability Rate',
    CONCAT(CAST(ROUND(SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100, 2) AS CHAR), '%'),
    '% bản ghi listing-ngày',
    'Một listing tại một ngày lịch và một snapshot',
    CONCAT('Window: 2026-09-25 to 2027-09-25 (', SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END), ' / ', COUNT(*), ' nights)')
FROM fact_calendar
WHERE snapshot_date = '2026-09-23'
  AND calendar_date BETWEEN '2026-09-25' AND '2027-09-25'

UNION ALL

-- KPI-05: Điểm đánh giá bình quân (thang điểm xác minh 1..5)
SELECT
    'KPI-05',
    'Average Rating Score',
    CAST(ROUND(AVG(review_scores_rating), 2) AS CHAR),
    'Điểm (thang 1..5)',
    'Một listing tại snapshot',
    CONCAT('Thang điểm 1..5 trên ', COUNT(*), ' tin có đánh giá hợp lệ')
FROM fact_listing_snapshot
WHERE snapshot_date = '2026-09-23'
  AND review_scores_rating BETWEEN 1.00 AND 5.00

UNION ALL

-- SUP-01: Trung vị số lượt đánh giá trên mỗi listing
SELECT
    'SUP-01',
    'Median Review Count per Listing',
    CAST(ROUND(AVG(number_of_reviews), 2) AS CHAR),
    'Review/listing',
    'Một listing tại snapshot',
    CONCAT('Calculated over ', MAX(n), ' listings with valid review count (Grain: 1 listing)')
FROM (
    SELECT number_of_reviews,
           ROW_NUMBER() OVER (ORDER BY number_of_reviews) AS rn,
           COUNT(*) OVER () AS n
    FROM fact_listing_snapshot
    WHERE snapshot_date = '2026-09-23'
      AND number_of_reviews IS NOT NULL
      AND number_of_reviews >= 0
) rev
WHERE rn IN (FLOOR((n+1)/2), FLOOR((n+2)/2))

UNION ALL

-- SUP-02: Số bản ghi review trong kỳ quan sát
SELECT
    'SUP-02',
    'Review Records in Period',
    CAST(COUNT(*) AS CHAR),
    'Bản ghi review',
    'Một bản ghi review',
    CONCAT(COUNT(*), ' valid reviews observed across ', COUNT(DISTINCT listing_id), ' listings (2011-05-04 .. 2026-09-25)')
FROM fact_review
WHERE snapshot_date = '2026-09-23'
  AND review_date BETWEEN '2011-05-04' AND '2026-09-25';


-- 9.2 KPI-03: Tỷ trọng loại phòng toàn Singapore (Overall Room Type Distribution)
SELECT
    'KPI-03' AS kpi_id,
    d.room_type,
    COUNT(*) AS count_listings,
    SUM(COUNT(*)) OVER () AS total_listings,
    ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS pct_share
FROM fact_listing_snapshot f
JOIN dim_listing d
  ON f.listing_sk = d.listing_sk AND f.snapshot_date_sk = d.snapshot_date_sk
WHERE f.snapshot_date = '2026-09-23'
  AND d.room_type IS NOT NULL
GROUP BY d.room_type
ORDER BY count_listings DESC;


-- 9.3 KPI-03: Cơ cấu loại phòng theo từng vùng địa lý (Regional Room Type Distribution)
-- Quy tắc: Bỏ lọc room_type ở mẫu số, giữ nguyên bộ lọc khu vực và snapshot_date
SELECT
    n.neighbourhood_group,
    d.room_type,
    COUNT(*) AS count_listings,
    SUM(COUNT(*)) OVER (PARTITION BY n.neighbourhood_group) AS total_listings_in_region,
    ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (PARTITION BY n.neighbourhood_group), 0), 2) AS pct_in_region
FROM fact_listing_snapshot f
JOIN dim_listing d
  ON f.listing_sk = d.listing_sk AND f.snapshot_date_sk = d.snapshot_date_sk
JOIN dim_neighbourhood n
  ON f.neighbourhood_sk = n.neighbourhood_sk
WHERE f.snapshot_date = '2026-09-23'
  AND d.room_type IS NOT NULL
GROUP BY n.neighbourhood_group, d.room_type
ORDER BY n.neighbourhood_group, count_listings DESC;



-- Audit kỹ thuật Gold. Mỗi lỗi đếm theo bản ghi hoặc nhóm grain bị lặp.
-- TQ-05 cần log của lượt nạp lại, không thể suy ra từ một lần SELECT.
WITH
dim_date_scope AS (SELECT * FROM dim_date),
dim_neighbourhood_scope AS (SELECT * FROM dim_neighbourhood),
dim_listing_scope AS (SELECT * FROM dim_listing WHERE snapshot_date = '2026-09-23'),
fact_listing_snapshot_scope AS (SELECT * FROM fact_listing_snapshot WHERE snapshot_date = '2026-09-23'),
fact_calendar_scope AS (SELECT * FROM fact_calendar WHERE snapshot_date = '2026-09-23'),
fact_review_scope AS (SELECT * FROM fact_review WHERE snapshot_date = '2026-09-23'),
required_checks AS (
    SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN
            `date_sk` IS NULL
            OR `full_date` IS NULL
            OR `day_of_month` IS NULL
            OR `day_of_week_iso` IS NULL
            OR `day_name` IS NULL OR TRIM(`day_name`) = ''
            OR `is_weekend` IS NULL
            OR `week_of_year` IS NULL
            OR `month_num` IS NULL
            OR `month_name` IS NULL OR TRIM(`month_name`) = ''
            OR `year_month` IS NULL OR TRIM(`year_month`) = ''
            OR `quarter_num` IS NULL
            OR `year_quarter` IS NULL OR TRIM(`year_quarter`) = ''
            OR `year_num` IS NULL
        THEN 1 ELSE 0 END), 0) AS bad
    FROM dim_date_scope
    UNION ALL
    SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN
            `neighbourhood_sk` IS NULL
            OR `neighbourhood_group` IS NULL OR TRIM(`neighbourhood_group`) = ''
            OR `neighbourhood_name` IS NULL OR TRIM(`neighbourhood_name`) = ''
            OR `snapshot_date` IS NULL
            OR `created_at` IS NULL
        THEN 1 ELSE 0 END), 0) AS bad
    FROM dim_neighbourhood_scope
    UNION ALL
    SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN
            `listing_sk` IS NULL
            OR `listing_id` IS NULL
            OR `snapshot_date` IS NULL
            OR `snapshot_date_sk` IS NULL
            OR `neighbourhood_sk` IS NULL
            OR `scrape_id` IS NULL
            OR `last_scraped_date` IS NULL
            OR `calendar_last_scraped_date` IS NULL
            OR `listing_name` IS NULL OR TRIM(`listing_name`) = ''
            OR `listing_url` IS NULL OR TRIM(`listing_url`) = ''
            OR `property_type` IS NULL OR TRIM(`property_type`) = ''
            OR `room_type` IS NULL OR TRIM(`room_type`) = ''
            OR `accommodates` IS NULL
            OR `latitude` IS NULL
            OR `longitude` IS NULL
            OR `host_id` IS NULL
            OR `host_name` IS NULL OR TRIM(`host_name`) = ''
            OR `created_at` IS NULL
        THEN 1 ELSE 0 END), 0) AS bad
    FROM dim_listing_scope
    UNION ALL
    SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN
            `listing_snapshot_sk` IS NULL
            OR `listing_sk` IS NULL
            OR `neighbourhood_sk` IS NULL
            OR `snapshot_date_sk` IS NULL
            OR `listing_id` IS NULL
            OR `snapshot_date` IS NULL
            OR `is_price_sgd_verified` IS NULL
            OR `minimum_nights_avg_ntm` IS NULL
            OR `maximum_nights_avg_ntm` IS NULL
            OR `availability_30` IS NULL
            OR `availability_60` IS NULL
            OR `availability_90` IS NULL
            OR `availability_365` IS NULL
            OR `availability_eoy` IS NULL
            OR `number_of_reviews` IS NULL
            OR `number_of_reviews_ltm` IS NULL
            OR `number_of_reviews_l30d` IS NULL
            OR `number_of_reviews_ly` IS NULL
            OR `host_listings_count` IS NULL
            OR `calculated_host_listings_count` IS NULL
            OR `calculated_host_listings_count_entire_homes` IS NULL
            OR `calculated_host_listings_count_private_rooms` IS NULL
            OR `calculated_host_listings_count_shared_rooms` IS NULL
            OR `estimated_occupancy_l365d` IS NULL
            OR `created_at` IS NULL
        THEN 1 ELSE 0 END), 0) AS bad
    FROM fact_listing_snapshot_scope
    UNION ALL
    SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN
            `calendar_sk` IS NULL
            OR `listing_sk` IS NULL
            OR `neighbourhood_sk` IS NULL
            OR `calendar_date_sk` IS NULL
            OR `snapshot_date_sk` IS NULL
            OR `listing_id` IS NULL
            OR `calendar_date` IS NULL
            OR `snapshot_date` IS NULL
            OR `is_available` IS NULL
            OR `minimum_nights` IS NULL
            OR `maximum_nights` IS NULL
            OR `created_at` IS NULL
        THEN 1 ELSE 0 END), 0) AS bad
    FROM fact_calendar_scope
    UNION ALL
    SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN
            `review_sk` IS NULL
            OR `listing_sk` IS NULL
            OR `neighbourhood_sk` IS NULL
            OR `review_date_sk` IS NULL
            OR `snapshot_date_sk` IS NULL
            OR `listing_id` IS NULL
            OR `review_id` IS NULL
            OR `review_date` IS NULL
            OR `snapshot_date` IS NULL
            OR `reviewer_id` IS NULL
            OR `reviewer_name` IS NULL OR TRIM(`reviewer_name`) = ''
            OR `has_comment` IS NULL
            OR `comment_length` IS NULL
            OR `review_count` IS NULL
            OR `created_at` IS NULL
        THEN 1 ELSE 0 END), 0) AS bad
    FROM fact_review_scope
),
duplicate_checks AS (
    SELECT COALESCE(SUM(n - 1), 0) AS bad
    FROM (SELECT COUNT(*) AS n FROM dim_date_scope GROUP BY full_date HAVING COUNT(*) > 1) AS grouped
    UNION ALL
    SELECT COALESCE(SUM(n - 1), 0) AS bad
    FROM (SELECT COUNT(*) AS n FROM dim_neighbourhood_scope GROUP BY neighbourhood_group, neighbourhood_name HAVING COUNT(*) > 1) AS grouped
    UNION ALL
    SELECT COALESCE(SUM(n - 1), 0) AS bad
    FROM (SELECT COUNT(*) AS n FROM dim_listing_scope GROUP BY listing_id, snapshot_date HAVING COUNT(*) > 1) AS grouped
    UNION ALL
    SELECT COALESCE(SUM(n - 1), 0) AS bad
    FROM (SELECT COUNT(*) AS n FROM fact_listing_snapshot_scope GROUP BY listing_id, snapshot_date HAVING COUNT(*) > 1) AS grouped
    UNION ALL
    SELECT COALESCE(SUM(n - 1), 0) AS bad
    FROM (SELECT COUNT(*) AS n FROM fact_calendar_scope GROUP BY listing_id, calendar_date, snapshot_date HAVING COUNT(*) > 1) AS grouped
    UNION ALL
    SELECT COALESCE(SUM(n - 1), 0) AS bad
    FROM (SELECT COUNT(*) AS n FROM fact_review_scope GROUP BY listing_id, review_id, snapshot_date HAVING COUNT(*) > 1) AS grouped
),
reference_checks AS (
    SELECT COUNT(*) AS bad FROM dim_listing_scope f
    LEFT JOIN dim_neighbourhood n ON n.neighbourhood_sk = f.neighbourhood_sk
    LEFT JOIN dim_date s ON s.date_sk = f.snapshot_date_sk AND s.full_date = f.snapshot_date
    WHERE n.neighbourhood_sk IS NULL OR s.date_sk IS NULL
    UNION ALL
    SELECT COUNT(*) AS bad FROM fact_listing_snapshot_scope f
    LEFT JOIN dim_neighbourhood n ON n.neighbourhood_sk = f.neighbourhood_sk
    LEFT JOIN dim_date s ON s.date_sk = f.snapshot_date_sk AND s.full_date = f.snapshot_date
    LEFT JOIN dim_listing d ON d.listing_sk = f.listing_sk
        AND d.listing_id = f.listing_id AND d.snapshot_date = f.snapshot_date
        AND d.snapshot_date_sk = f.snapshot_date_sk AND d.neighbourhood_sk = f.neighbourhood_sk
    WHERE n.neighbourhood_sk IS NULL OR s.date_sk IS NULL OR d.listing_sk IS NULL
    UNION ALL
    SELECT COUNT(*) AS bad FROM fact_calendar_scope f
    LEFT JOIN dim_neighbourhood n ON n.neighbourhood_sk = f.neighbourhood_sk
    LEFT JOIN dim_date s ON s.date_sk = f.snapshot_date_sk AND s.full_date = f.snapshot_date
    LEFT JOIN dim_listing d ON d.listing_sk = f.listing_sk
        AND d.listing_id = f.listing_id AND d.snapshot_date = f.snapshot_date
        AND d.snapshot_date_sk = f.snapshot_date_sk AND d.neighbourhood_sk = f.neighbourhood_sk
    LEFT JOIN dim_date e ON e.date_sk = f.calendar_date_sk AND e.full_date = f.calendar_date
    WHERE n.neighbourhood_sk IS NULL OR s.date_sk IS NULL OR d.listing_sk IS NULL OR e.date_sk IS NULL
    UNION ALL
    SELECT COUNT(*) AS bad FROM fact_review_scope f
    LEFT JOIN dim_neighbourhood n ON n.neighbourhood_sk = f.neighbourhood_sk
    LEFT JOIN dim_date s ON s.date_sk = f.snapshot_date_sk AND s.full_date = f.snapshot_date
    LEFT JOIN dim_listing d ON d.listing_sk = f.listing_sk
        AND d.listing_id = f.listing_id AND d.snapshot_date = f.snapshot_date
        AND d.snapshot_date_sk = f.snapshot_date_sk AND d.neighbourhood_sk = f.neighbourhood_sk
    LEFT JOIN dim_date e ON e.date_sk = f.review_date_sk AND e.full_date = f.review_date
    WHERE n.neighbourhood_sk IS NULL OR s.date_sk IS NULL OR d.listing_sk IS NULL OR e.date_sk IS NULL
),
domain_checks AS (
    SELECT COUNT(*) AS bad FROM dim_listing_scope
    WHERE accommodates NOT BETWEEN 1 AND 16 OR latitude NOT BETWEEN -90 AND 90
        OR longitude NOT BETWEEN -180 AND 180
        OR room_type NOT IN ('Private room', 'Entire home/apt', 'Hotel room', 'Shared room')
        OR host_is_superhost NOT IN (0, 1) OR host_has_profile_pic NOT IN (0, 1)
        OR host_identity_verified NOT IN (0, 1) OR has_availability NOT IN (0, 1)
    UNION ALL
    SELECT COUNT(*) AS bad FROM fact_listing_snapshot_scope
    WHERE review_scores_rating NOT BETWEEN 1 AND 5 OR review_scores_accuracy NOT BETWEEN 1 AND 5
        OR review_scores_cleanliness NOT BETWEEN 1 AND 5 OR review_scores_checkin NOT BETWEEN 1 AND 5
        OR review_scores_communication NOT BETWEEN 1 AND 5 OR review_scores_location NOT BETWEEN 1 AND 5
        OR review_scores_value NOT BETWEEN 1 AND 5
        OR is_price_sgd_verified <> CASE WHEN listed_price_raw_amount > 0 AND quote_currency = 'SGD' THEN 1 ELSE 0 END
        OR (is_price_sgd_verified = 1 AND
            (listed_price_sgd IS NULL OR listed_price_sgd <> listed_price_raw_amount))
        OR (is_price_sgd_verified = 0 AND listed_price_sgd IS NOT NULL)
    UNION ALL
    SELECT COUNT(*) AS bad FROM fact_calendar_scope
    WHERE is_available NOT IN (0, 1) OR minimum_nights <= 0 OR maximum_nights < minimum_nights
    UNION ALL
    SELECT COUNT(*) AS bad FROM fact_review_scope
    WHERE has_comment NOT IN (0, 1) OR review_count <> 1 OR (has_comment = 0 AND comment_length <> 0)
),
metrics AS (
    SELECT 'TQ-01' AS metric, 'Gold rows with a missing required field' AS test, SUM(bad) AS violations
    FROM required_checks
    UNION ALL SELECT 'TQ-02', 'Extra Gold rows per business grain', SUM(bad) FROM duplicate_checks
    UNION ALL SELECT 'TQ-03', 'Gold rows with an invalid dimension reference', SUM(bad) FROM reference_checks
    UNION ALL SELECT 'TQ-04', 'Gold rows outside audited business domains', SUM(bad) FROM domain_checks
)
SELECT metric, test, violations,
       CASE WHEN violations > 0 THEN 'FAIL'
            WHEN (SELECT MIN(n) FROM required_checks) = 0 THEN 'NOT_RUN'
            ELSE 'PASS' END AS status
FROM metrics
UNION ALL
SELECT 'TQ-05', 'Check loader replay log for row counts and Raw–Gold metrics', NULL, 'NOT_RUN'
ORDER BY metric;
