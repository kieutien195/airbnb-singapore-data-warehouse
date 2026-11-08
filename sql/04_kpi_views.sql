-- =============================================================================
-- Task 3.7: Xây dựng các SQL View tính toán KPI từ Kho Dữ liệu (Gold Layer)
-- File: sql/04_kpi_views.sql
-- Database: airbnb_sg_2026 | MySQL 8.0+
-- Tác giả: Minh (Database Administrator / Data Modeler)
--
-- TỔNG QUAN VÀ NGUYÊN TẮC THIẾT KẾ:
-- 1. Snapshot quy chuẩn: '2026-09-23' (Snapshot duy nhất theo source_inventory.csv).
-- 2. Độc lập Fact & Chống bùng nổ tích Descartes (Anti-Cartesian Fan-Out):
--    - Tuyệt đối KHÔNG JOIN trực tiếp fact_calendar (1.17M dòng) và fact_review (46K dòng)
--      với fact_listing_snapshot trong cùng một câu đếm đơn tầng.
--    - Mọi phép tổng hợp nhiều Fact đều phải pre-aggregate tại cấp listing_sk trước khi ghép.
-- 3. Xử lý NULL và Mẫu số (Zero-division & NULL safety):
--    - Sử dụng NULLIF(denominator, 0) ở tất cả các phép chia tỷ lệ để tránh lỗi chia cho 0.
--    - Giữ nguyên NULL tự nhiên (không tự ý thay thế NULL bằng 0 ở điểm rating hay giá).
-- 4. Tính toán Trung vị (Median Calculation) trên MySQL 8.0:
--    - Vì MySQL không có hàm MEDIAN() và View không cho phép biến người dùng (@var),
--      ta sử dụng CTE kết hợp Window Functions ROW_NUMBER() và COUNT(*) OVER().
-- 5. Cấu trúc gồm:
--    - Phần 1: Các View phân tích KPI cốt lõi (KPI-01 đến KPI-05)
--    - Phần 2: Các View phân tích chỉ tiêu bổ sung (SUP-01, SUP-02)
--    - Phần 3: View Báo cáo Tổng hợp (vw_kpi_summary_overall)
--    - Phần 4: View Dữ liệu Gold phục vụ Kết nối BI (vw_gold_bi_analytical_base)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PHẦN 1: CÁC VIEW PHÂN TÍCH KPI CỐT LÕI (CORE KPIS)
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- KPI-01: Số tin đăng hoạt động duy nhất (Active Listings Count)
-- Grain: 1 dòng = 1 snapshot
-- Nguồn: fact_listing_snapshot
-- Bộ lọc: snapshot_date = '2026-09-23' AND listing_id IS NOT NULL
-- Mẫu số: Không áp dụng (Đếm số lượng tin đăng tuyệt đối)
-- Xử lý NULL: Bỏ qua các listing_id NULL
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpi01_active_listings AS
SELECT 
    'KPI-01' AS kpi_id,
    'Active Listings Count' AS kpi_name,
    'One listing at snapshot' AS grain,
    snapshot_date,
    COUNT(DISTINCT listing_id) AS active_listings_count,
    COUNT(*) AS total_snapshot_records
FROM fact_listing_snapshot
WHERE snapshot_date = '2026-09-23'
  AND listing_id IS NOT NULL
GROUP BY snapshot_date;


-- -----------------------------------------------------------------------------
-- KPI-02: Trung vị giá niêm yết mỗi đêm bằng SGD (Median Listed Price per Night SGD)
-- Grain: 1 dòng = 1 snapshot
-- Nguồn: fact_listing_snapshot
-- Bộ lọc: snapshot_date = '2026-09-23'
--         AND is_price_sgd_verified = 1
--         AND quote_currency = 'SGD'
--         AND listed_price_sgd IS NOT NULL
--         AND listed_price_sgd > 0
-- Mẫu số: Không áp dụng cho Median (Đo độ phủ Coverage: 2,725 / 3,208 listing = 84.94%)
-- Xử lý NULL: Loại bỏ giá NULL hoặc tiền tệ không xác định (35 listing không có currency)
-- Phương pháp: CTE Window Function ROW_NUMBER() / COUNT(*) OVER() xác định vị trí trung vị
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpi02_median_price_sgd AS
WITH ordered_prices AS (
    SELECT 
        snapshot_date,
        listed_price_sgd,
        ROW_NUMBER() OVER (ORDER BY listed_price_sgd, listing_id) AS row_num,
        COUNT(*) OVER () AS total_count
    FROM fact_listing_snapshot
    WHERE snapshot_date = '2026-09-23'
      AND is_price_sgd_verified = 1
      AND quote_currency = 'SGD'
      AND listed_price_sgd IS NOT NULL
      AND listed_price_sgd > 0
)
SELECT 
    'KPI-02' AS kpi_id,
    'Median Listed Price per Night (SGD)' AS kpi_name,
    'One listing at snapshot' AS grain,
    snapshot_date,
    'SGD' AS quote_currency,
    ROUND(AVG(listed_price_sgd), 2) AS median_price_sgd,
    MAX(total_count) AS verified_listings_count
FROM ordered_prices
WHERE row_num IN (FLOOR((total_count + 1) / 2), CEIL((total_count + 1) / 2))
GROUP BY snapshot_date;


-- -----------------------------------------------------------------------------
-- KPI-03: Tỷ trọng loại phòng toàn sàn (Overall Room Type Share)
-- Grain: 1 dòng = 1 room_type tại snapshot
-- Nguồn: fact_listing_snapshot JOIN dim_listing
-- Bộ lọc: snapshot_date = '2026-09-23' AND room_type IS NOT NULL AND room_type != ''
-- Mẫu số: Tổng số listing có room_type hợp lệ trong snapshot (Window: SUM(COUNT(*)) OVER ())
-- Xử lý NULL: Loại bỏ room_type trống/NULL; mẫu số bảo vệ bởi NULLIF(..., 0)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpi03_room_type_share AS
SELECT 
    'KPI-03' AS kpi_id,
    'Room Type Share' AS kpi_name,
    'One room type at snapshot' AS grain,
    fls.snapshot_date,
    dl.room_type,
    COUNT(fls.listing_id) AS listing_count,
    SUM(COUNT(fls.listing_id)) OVER () AS total_listings,
    ROUND(COUNT(fls.listing_id) * 100.0 / NULLIF(SUM(COUNT(fls.listing_id)) OVER (), 0), 2) AS room_type_share_pct
FROM fact_listing_snapshot fls
JOIN dim_listing dl ON fls.listing_sk = dl.listing_sk
WHERE fls.snapshot_date = '2026-09-23'
  AND dl.room_type IS NOT NULL
  AND dl.room_type != ''
GROUP BY fls.snapshot_date, dl.room_type;


-- -----------------------------------------------------------------------------
-- KPI-03 (Phân rã khu vực): Tỷ trọng loại phòng theo Vùng quy hoạch (Regional Room Type Share)
-- Grain: 1 dòng = 1 room_type trong 1 neighbourhood_group tại snapshot
-- Nguồn: fact_listing_snapshot JOIN dim_listing JOIN dim_neighbourhood
-- Bộ lọc: snapshot_date = '2026-09-23' AND room_type IS NOT NULL
-- Mẫu số: Tổng số listing trong VÙNG đó (Window: SUM(COUNT(*)) OVER (PARTITION BY dn.neighbourhood_group))
--         *LƯU Ý NGHIỆP VỤ*: Không áp dụng bộ lọc room_type vào mẫu số khu vực!
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpi03_regional_room_type_share AS
SELECT 
    'KPI-03-REGIONAL' AS kpi_id,
    'Regional Room Type Share' AS kpi_name,
    'One room type per neighbourhood group at snapshot' AS grain,
    fls.snapshot_date,
    dn.neighbourhood_group,
    dl.room_type,
    COUNT(fls.listing_id) AS listing_count,
    SUM(COUNT(fls.listing_id)) OVER (PARTITION BY dn.neighbourhood_group) AS regional_total_listings,
    ROUND(COUNT(fls.listing_id) * 100.0 / NULLIF(SUM(COUNT(fls.listing_id)) OVER (PARTITION BY dn.neighbourhood_group), 0), 2) AS room_type_share_pct
FROM fact_listing_snapshot fls
JOIN dim_listing dl ON fls.listing_sk = dl.listing_sk
JOIN dim_neighbourhood dn ON fls.neighbourhood_sk = dn.neighbourhood_sk
WHERE fls.snapshot_date = '2026-09-23'
  AND dl.room_type IS NOT NULL
  AND dl.room_type != ''
GROUP BY fls.snapshot_date, dn.neighbourhood_group, dl.room_type;


-- -----------------------------------------------------------------------------
-- KPI-04: Tỷ lệ bản ghi lịch còn khả dụng (Calendar Available Nights Ratio)
-- Grain: 1 dòng = 1 snapshot (tổng hợp 1,170,950 bản ghi listing-ngày)
-- Nguồn: fact_calendar
-- Cửa sổ thời gian chuẩn hóa: 2026-09-25 đến 2027-09-25 (366 ngày)
-- Bộ lọc: snapshot_date = '2026-09-23' AND calendar_date BETWEEN '2026-09-25' AND '2027-09-25'
-- Tử số: SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) - số đêm mở lịch (900,960 đêm)
-- Mẫu số: COUNT(*) - tổng số bản ghi listing-ngày hợp lệ trong cửa sổ (1,170,950 đêm)
-- Xử lý NULL: Mẫu số bọc NULLIF(COUNT(*), 0)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpi04_calendar_availability AS
SELECT 
    'KPI-04' AS kpi_id,
    'Calendar Available Nights Ratio' AS kpi_name,
    'Listing-day records across 366-day window' AS grain,
    snapshot_date,
    '2026-09-25' AS calendar_window_start,
    '2027-09-25' AS calendar_window_end,
    SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) AS available_nights_count,
    COUNT(*) AS total_nights_count,
    ROUND(SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS available_nights_ratio_pct
FROM fact_calendar
WHERE snapshot_date = '2026-09-23'
  AND calendar_date BETWEEN '2026-09-25' AND '2027-09-25'
GROUP BY snapshot_date;


-- -----------------------------------------------------------------------------
-- KPI-04 (Phân rã khu vực): Tỷ lệ lịch khả dụng theo Vùng quy hoạch (Regional Calendar Availability)
-- Grain: 1 dòng = 1 neighbourhood_group tại snapshot
-- Nguồn: fact_calendar JOIN dim_neighbourhood
-- Cửa sổ thời gian: 2026-09-25 đến 2027-09-25
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpi04_regional_calendar_availability AS
SELECT 
    'KPI-04-REGIONAL' AS kpi_id,
    'Regional Calendar Available Nights Ratio' AS kpi_name,
    'Listing-day records per neighbourhood group' AS grain,
    fc.snapshot_date,
    dn.neighbourhood_group,
    '2026-09-25' AS calendar_window_start,
    '2027-09-25' AS calendar_window_end,
    SUM(CASE WHEN fc.is_available = 1 THEN 1 ELSE 0 END) AS available_nights_count,
    COUNT(*) AS total_nights_count,
    ROUND(SUM(CASE WHEN fc.is_available = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS available_nights_ratio_pct
FROM fact_calendar fc
JOIN dim_neighbourhood dn ON fc.neighbourhood_sk = dn.neighbourhood_sk
WHERE fc.snapshot_date = '2026-09-23'
  AND fc.calendar_date BETWEEN '2026-09-25' AND '2027-09-25'
GROUP BY fc.snapshot_date, dn.neighbourhood_group;


-- -----------------------------------------------------------------------------
-- KPI-05: Điểm đánh giá tổng thể trung bình (Average Overall Review Score)
-- Grain: 1 dòng = 1 snapshot
-- Nguồn: fact_listing_snapshot
-- Miền giá trị chuẩn hóa: 1.00 đến 5.00
-- Bộ lọc: snapshot_date = '2026-09-23'
--         AND review_scores_rating IS NOT NULL
--         AND review_scores_rating BETWEEN 1.00 AND 5.00
-- Mẫu số: Số listing có điểm đánh giá hợp lệ (1,839 listing; độ phủ Coverage = 57.33%)
-- Xử lý NULL: KHÔNG thay thế NULL bằng 0 (loại trừ tự nhiên trong hàm AVG)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpi05_average_rating AS
SELECT 
    'KPI-05' AS kpi_id,
    'Average Overall Review Score' AS kpi_name,
    'One rated listing at snapshot' AS grain,
    snapshot_date,
    '1.00 - 5.00' AS score_scale,
    COUNT(review_scores_rating) AS rated_listings_count,
    ROUND(SUM(review_scores_rating), 2) AS sum_review_score,
    ROUND(AVG(review_scores_rating), 2) AS avg_review_score
FROM fact_listing_snapshot
WHERE snapshot_date = '2026-09-23'
  AND review_scores_rating IS NOT NULL
  AND review_scores_rating BETWEEN 1.00 AND 5.00
GROUP BY snapshot_date;


-- -----------------------------------------------------------------------------
-- KPI-05 (Phân rã khu vực): Điểm đánh giá trung bình theo Vùng quy hoạch (Regional Average Rating)
-- Grain: 1 dòng = 1 neighbourhood_group tại snapshot
-- Nguồn: fact_listing_snapshot JOIN dim_neighbourhood
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpi05_regional_average_rating AS
SELECT 
    'KPI-05-REGIONAL' AS kpi_id,
    'Regional Average Overall Review Score' AS kpi_name,
    'One rated listing per neighbourhood group at snapshot' AS grain,
    fls.snapshot_date,
    dn.neighbourhood_group,
    COUNT(fls.review_scores_rating) AS rated_listings_count,
    ROUND(SUM(fls.review_scores_rating), 2) AS sum_review_score,
    ROUND(AVG(fls.review_scores_rating), 2) AS avg_review_score
FROM fact_listing_snapshot fls
JOIN dim_neighbourhood dn ON fls.neighbourhood_sk = dn.neighbourhood_sk
WHERE fls.snapshot_date = '2026-09-23'
  AND fls.review_scores_rating IS NOT NULL
  AND fls.review_scores_rating BETWEEN 1.00 AND 5.00
GROUP BY fls.snapshot_date, dn.neighbourhood_group;


-- -----------------------------------------------------------------------------
-- PHẦN 2: CÁC VIEW PHÂN TÍCH CHỈ TIÊU BỔ SUNG (SUPPLEMENTAL INDICATORS)
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- SUP-01: Trung vị số review trên mỗi listing (Median Review Count per Listing)
-- Grain: 1 dòng = 1 snapshot
-- Nguồn: fact_listing_snapshot
-- Bộ lọc: snapshot_date = '2026-09-23' AND number_of_reviews IS NOT NULL AND number_of_reviews >= 0
-- Quy ước nghiệp vụ: Tính trên toàn bộ 3,208 listing (giữ nguyên giá trị 0 của 1,369 listing chưa có review)
-- Phương pháp: CTE Window Function ROW_NUMBER() / COUNT(*) OVER()
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_sup01_median_review_count AS
WITH ordered_reviews AS (
    SELECT 
        snapshot_date,
        number_of_reviews,
        ROW_NUMBER() OVER (ORDER BY number_of_reviews, listing_id) AS row_num,
        COUNT(*) OVER () AS total_count
    FROM fact_listing_snapshot
    WHERE snapshot_date = '2026-09-23'
      AND number_of_reviews IS NOT NULL
      AND number_of_reviews >= 0
)
SELECT 
    'SUP-01' AS kpi_id,
    'Median Review Count per Listing' AS kpi_name,
    'One listing at snapshot' AS grain,
    snapshot_date,
    ROUND(AVG(number_of_reviews), 2) AS median_review_count,
    MAX(total_count) AS total_listings_count
FROM ordered_reviews
WHERE row_num IN (FLOOR((total_count + 1) / 2), CEIL((total_count + 1) / 2))
GROUP BY snapshot_date;


-- -----------------------------------------------------------------------------
-- SUP-02: Số bản ghi review trong kỳ (Review Records in Period)
-- Grain: 1 dòng = 1 snapshot
-- Nguồn: fact_review (đã được khử trùng lặp theo khóa ghép (listing_id, review_id, snapshot_date))
-- Bộ lọc: snapshot_date = '2026-09-23'
-- Lưu ý: Không JOIN với Calendar hay Listings khi đếm để tránh nhân số dòng.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_sup02_review_records_period AS
SELECT 
    'SUP-02' AS kpi_id,
    'Review Records in Period' AS kpi_name,
    'One review record in snapshot' AS grain,
    snapshot_date,
    COUNT(*) AS review_records_count,
    COUNT(DISTINCT listing_id) AS distinct_reviewed_listings_count,
    MIN(review_date) AS earliest_review_date,
    MAX(review_date) AS latest_review_date
FROM fact_review
WHERE snapshot_date = '2026-09-23'
GROUP BY snapshot_date;


-- -----------------------------------------------------------------------------
-- PHẦN 3: VIEW BÁO CÁO TỔNG HỢP HỢP NHẤT (EXECUTIVE KPI SUMMARY)
-- Grain: 1 dòng = 1 chỉ tiêu KPI tại snapshot
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_kpi_summary_overall AS
SELECT 
    'KPI-01' AS kpi_id,
    'Active Listings Count' AS kpi_name,
    snapshot_date,
    active_listings_count AS metric_value,
    'Listings' AS unit,
    'Quy mô tin đăng tại snapshot 2026-09-23' AS description
FROM vw_kpi01_active_listings

UNION ALL

SELECT 
    'KPI-02' AS kpi_id,
    'Median Listed Price SGD' AS kpi_name,
    snapshot_date,
    median_price_sgd AS metric_value,
    'SGD/night' AS unit,
    'Trung vị giá niêm yết trên 2,725 listing có giá SGD hợp lệ' AS description
FROM vw_kpi02_median_price_sgd

UNION ALL

SELECT 
    CONCAT('KPI-03 (', room_type, ')') AS kpi_id,
    'Room Type Share' AS kpi_name,
    snapshot_date,
    room_type_share_pct AS metric_value,
    '% listings' AS unit,
    CONCAT('Tỷ trọng loại phòng: ', listing_count, ' / ', total_listings, ' listings') AS description
FROM vw_kpi03_room_type_share

UNION ALL

SELECT 
    'KPI-04' AS kpi_id,
    'Calendar Available Nights Ratio' AS kpi_name,
    snapshot_date,
    available_nights_ratio_pct AS metric_value,
    '% listing-nights' AS unit,
    'Tỷ lệ mở phòng trên cửa sổ 366 ngày (900,960 / 1,170,950 đêm)' AS description
FROM vw_kpi04_calendar_availability

UNION ALL

SELECT 
    'KPI-05' AS kpi_id,
    'Average Overall Review Score' AS kpi_name,
    snapshot_date,
    avg_review_score AS metric_value,
    'Points (1.00..5.00)' AS unit,
    'Điểm đánh giá trung bình trên 1,839 listing có điểm' AS description
FROM vw_kpi05_average_rating

UNION ALL

SELECT 
    'SUP-01' AS kpi_id,
    'Median Review Count per Listing' AS kpi_name,
    snapshot_date,
    median_review_count AS metric_value,
    'Reviews/listing' AS unit,
    'Trung vị số lượng đánh giá trên 3,208 listing' AS description
FROM vw_sup01_median_review_count

UNION ALL

SELECT 
    'SUP-02' AS kpi_id,
    'Review Records in Period' AS kpi_name,
    snapshot_date,
    review_records_count AS metric_value,
    'Review records' AS unit,
    'Tổng số bản ghi đánh giá lịch sử (từ 2011-05-04 đến 2026-09-25)' AS description
FROM vw_sup02_review_records_period;


-- -----------------------------------------------------------------------------
-- PHẦN 4: VIEW DỮ LIỆU GOLD PHỤC VỤ KẾT NỐI BI (BI ANALYTICAL BASE)
-- Grain: 1 dòng = 1 listing duy nhất tại snapshot (3,208 dòng)
-- 
-- CHIẾN LƯỢC CHỐNG TÍCH DESCARTES (FAN-OUT PREVENTION):
-- - Fact Calendar (1.17M dòng) được pre-aggregate theo listing_sk trong CTE cal_agg.
-- - Fact Review (46K dòng) được pre-aggregate theo listing_sk trong CTE rev_agg.
-- - Khi JOIN với dim_listing và fact_listing_snapshot, số dòng được bảo toàn chính xác 
--   tuyệt đối là 3,208 dòng (Zero Duplication), không gây phình to bộ nhớ hay làm chậm BI.
-- - Cung cấp đầy đủ các chiều: Địa lý (Group, Name), Thuộc tính phòng (Room type, Beds), 
--   Chủ nhà (Superhost), Giá, Lịch khả dụng và Đánh giá.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_gold_bi_analytical_base AS
WITH cal_agg AS (
    SELECT 
        listing_sk,
        COUNT(*) AS calendar_total_nights,
        SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) AS calendar_available_nights,
        ROUND(SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS calendar_availability_ratio_pct
    FROM fact_calendar
    WHERE snapshot_date = '2026-09-23'
      AND calendar_date BETWEEN '2026-09-25' AND '2027-09-25'
    GROUP BY listing_sk
),
rev_agg AS (
    SELECT 
        listing_sk,
        COUNT(*) AS historical_review_records,
        MIN(review_date) AS earliest_review_date,
        MAX(review_date) AS latest_review_date
    FROM fact_review
    WHERE snapshot_date = '2026-09-23'
    GROUP BY listing_sk
)
SELECT 
    -- 1. Grain & Surrogate Keys
    fls.listing_snapshot_sk,
    fls.listing_sk,
    fls.listing_id,
    fls.snapshot_date,
    fls.snapshot_date_sk,
    
    -- 2. Chiều Địa lý (Geographic Dimension)
    dn.neighbourhood_sk,
    dn.neighbourhood_group,
    dn.neighbourhood_name,
    dl.latitude,
    dl.longitude,
    
    -- 3. Chiều Thuộc tính Tin đăng (Listing Attributes)
    dl.listing_name,
    dl.listing_url,
    dl.property_type,
    dl.room_type,
    dl.accommodates,
    dl.bedrooms,
    dl.beds,
    dl.bathrooms_text,
    
    -- 4. Chiều Chủ nhà (Host Dimension)
    dl.host_id,
    dl.host_name,
    dl.host_is_superhost,
    dl.host_identity_verified,
    
    -- 5. Định lượng Giá & Trạng thái tại Snapshot (Listing Snapshot Measures)
    fls.listed_price_raw_amount,
    fls.quote_currency,
    fls.is_price_sgd_verified,
    fls.listed_price_sgd,
    fls.minimum_nights,
    fls.maximum_nights,
    fls.availability_30,
    fls.availability_60,
    fls.availability_90,
    fls.availability_365,
    fls.number_of_reviews,
    fls.review_scores_rating,
    
    -- 6. Chỉ tiêu Lịch đã tiền tổng hợp (Pre-aggregated Calendar Metrics - KPI-04)
    COALESCE(cal.calendar_total_nights, 0) AS calendar_total_nights,
    COALESCE(cal.calendar_available_nights, 0) AS calendar_available_nights,
    cal.calendar_availability_ratio_pct,
    
    -- 7. Chỉ tiêu Đánh giá đã tiền tổng hợp (Pre-aggregated Review Metrics - SUP-02)
    COALESCE(rev.historical_review_records, 0) AS historical_review_records,
    rev.earliest_review_date,
    rev.latest_review_date

FROM fact_listing_snapshot fls
JOIN dim_listing dl ON fls.listing_sk = dl.listing_sk
JOIN dim_neighbourhood dn ON fls.neighbourhood_sk = dn.neighbourhood_sk
LEFT JOIN cal_agg cal ON fls.listing_sk = cal.listing_sk
LEFT JOIN rev_agg rev ON fls.listing_sk = rev.listing_sk
WHERE fls.snapshot_date = '2026-09-23';

-- =============================================================================
-- KẾT THÚC DDL VIEW
-- =============================================================================
