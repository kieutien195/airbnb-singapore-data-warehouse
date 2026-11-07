-- Chỉ SELECT và biến phiên làm việc; không sửa/nạp/xóa dữ liệu.
-- Chạy trên DB đã có 6 bảng Gold. Thay 5 biến theo comparison_context.json.
-- Xuất DUY NHẤT result grid cuối thành CSV UTF-8 có header:
-- snapshot_date,metric,group_value,value (SQL NULL -> ô rỗng hoặc NULL).
SET @snapshot = '2026-09-23';
SET @calendar_start = '2026-09-25';
SET @calendar_end = '2027-09-25';
SET @review_start = '2011-05-04';
SET @review_end = '2026-09-25';

WITH
l AS (SELECT * FROM fact_listing_snapshot WHERE snapshot_date = @snapshot),
c AS (SELECT * FROM fact_calendar WHERE snapshot_date = @snapshot),
r AS (SELECT * FROM fact_review WHERE snapshot_date = @snapshot),
d AS (SELECT * FROM dim_listing WHERE snapshot_date = @snapshot),
p_rank AS (
    SELECT listed_price_sgd AS val,
           ROW_NUMBER() OVER (ORDER BY listed_price_sgd) AS rn,
           COUNT(*) OVER () AS n
    FROM l WHERE is_price_sgd_verified = 1 AND quote_currency = 'SGD' AND listed_price_sgd > 0
),
count_rank AS (
    SELECT number_of_reviews AS val,
           ROW_NUMBER() OVER (ORDER BY number_of_reviews) AS rn,
           COUNT(*) OVER () AS n
    FROM l WHERE number_of_reviews >= 0
),
room AS (
    SELECT d.room_type, COUNT(*) AS n
    FROM l JOIN d ON l.listing_sk = d.listing_sk
                   AND l.listing_id = d.listing_id AND l.snapshot_date = d.snapshot_date
    GROUP BY d.room_type
),
cal_valid AS (
    SELECT * FROM c WHERE calendar_date BETWEEN @calendar_start AND @calendar_end
                          AND is_available IN (0, 1)
),
rating AS (SELECT review_scores_rating AS val FROM l WHERE review_scores_rating BETWEEN 1 AND 5),
review_keys AS (
    SELECT DISTINCT listing_id, review_id FROM r
    WHERE review_date BETWEEN @review_start AND @review_end AND listing_id > 0 AND review_id > 0
),
metrics AS (
    SELECT 'KPI-01' AS metric, 'ALL' AS group_value, COUNT(DISTINCT listing_id) AS value FROM l
    UNION ALL SELECT 'KPI-02', 'ALL', ROUND(AVG(val), 4) FROM p_rank WHERE rn IN (FLOOR((n+1)/2), FLOOR((n+2)/2))
    UNION ALL SELECT 'PRICE_VALID_COUNT', 'ALL', COUNT(*) FROM p_rank
    UNION ALL SELECT 'KPI-03_COUNT', room_type, n FROM room
    UNION ALL SELECT 'KPI-03_PERCENT', room_type, ROUND(n * 100.0 / NULLIF((SELECT COUNT(*) FROM l), 0), 4) FROM room
    UNION ALL SELECT 'KPI-04', 'ALL', ROUND(AVG(CAST(is_available AS DECIMAL(12,6))) * 100, 4) FROM cal_valid
    UNION ALL SELECT 'AVAILABLE_NIGHTS', 'ALL', COALESCE(SUM(is_available), 0) FROM cal_valid
    UNION ALL SELECT 'VALID_CALENDAR_NIGHTS', 'ALL', COUNT(*) FROM cal_valid
    UNION ALL SELECT 'KPI-05', 'ALL', ROUND(AVG(val), 4) FROM rating
    UNION ALL SELECT 'RATING_VALID_COUNT', 'ALL', COUNT(*) FROM rating
    UNION ALL SELECT 'SUP-01', 'ALL', ROUND(AVG(val), 4) FROM count_rank WHERE rn IN (FLOOR((n+1)/2), FLOOR((n+2)/2))
    UNION ALL SELECT 'REVIEW_COUNT_VALID_LISTINGS', 'ALL', COUNT(*) FROM count_rank
    UNION ALL SELECT 'SUP-02', 'ALL', COUNT(*) FROM review_keys
    UNION ALL SELECT 'LISTING_ROWS', 'ALL', COUNT(*) FROM l
    UNION ALL SELECT 'CALENDAR_ROWS', 'ALL', COUNT(*) FROM c
    UNION ALL SELECT 'REVIEW_ROWS', 'ALL', COUNT(*) FROM r
    UNION ALL SELECT 'PRICE_NULL_COUNT', 'ALL', SUM(listed_price_sgd IS NULL) FROM l
    UNION ALL SELECT 'RATING_NULL_COUNT', 'ALL', SUM(review_scores_rating IS NULL) FROM l
    UNION ALL SELECT 'DUP_LISTING_GRAIN', 'ALL', COUNT(*) - COUNT(DISTINCT listing_id, snapshot_date) FROM l
    UNION ALL SELECT 'DUP_CALENDAR_GRAIN', 'ALL', COUNT(*) - COUNT(DISTINCT listing_id, calendar_date, snapshot_date) FROM c
    UNION ALL SELECT 'DUP_REVIEW_GRAIN', 'ALL', COUNT(*) - COUNT(DISTINCT listing_id, review_id, snapshot_date) FROM r
    UNION ALL SELECT 'ORPHAN_CALENDAR_LISTING', 'ALL', COUNT(*) FROM c LEFT JOIN d
        ON c.listing_sk=d.listing_sk AND c.listing_id=d.listing_id AND c.snapshot_date=d.snapshot_date
        WHERE d.listing_sk IS NULL
    UNION ALL SELECT 'ORPHAN_REVIEW_LISTING', 'ALL', COUNT(*) FROM r LEFT JOIN d
        ON r.listing_sk=d.listing_sk AND r.listing_id=d.listing_id AND r.snapshot_date=d.snapshot_date
        WHERE d.listing_sk IS NULL
)
SELECT @snapshot AS snapshot_date, metric, group_value, value
FROM metrics ORDER BY metric, group_value;
