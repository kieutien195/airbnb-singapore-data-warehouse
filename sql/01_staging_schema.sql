-- =============================================================================
-- Dự án: Xây dựng Nhà kho dữ liệu & Báo cáo BI phân tích Airbnb Singapore
-- Phân hệ: Tầng Staging / Bronze (Raw Data Landing Zone)
-- Tệp DDL: sql/01_staging_schema.sql
-- Nhiệm vụ WBS: Task 3.1 - Tạo raw/staging tables trong MySQL
-- Người thực hiện: Minh (Database Administrator / Data Modeler)
-- Người thụ hưởng kế tiếp: Thái (Data Engineer - thực hiện Task 3.2 Ingestion)
--
-- Mục tiêu kỹ thuật:
-- 1. Khởi tạo 4 bảng staging tương ứng 4 tệp nguồn:
--    - stg_neighbourhoods  (từ data/raw/neighbourhoods.csv - 55 bản ghi)
--    - stg_calendar        (từ data/raw/calendar.csv.gz - 1,170,950 bản ghi)
--    - stg_reviews         (từ data/raw/reviews.csv.gz - 46,000 bản ghi)
--    - stg_listings        (từ data/raw/listings.csv.gz - 3,208 bản ghi, 90 cột nguồn)
-- 2. Bảo toàn nguyên vẹn giá trị thô từ nguồn (Bronze/Raw Immutability):
--    - Chưa áp ràng buộc khóa ngoại (Foreign Key) hoặc NOT NULL quá chặt trên dữ liệu nghiệp vụ
--    - Lưu nguyên dạng chuỗi giá có ký hiệu tiền tệ (price: $86.63) và văn bản tự do
--    - Bổ sung trường định danh tự tăng raw_id làm surrogate key cho từng dòng staging
-- 3. Bổ sung đầy đủ 3 trường metadata kiểm toán theo quy chuẩn kiến trúc:
--    - source_file: Tên tệp dữ liệu nguồn
--    - snapshot_date: Ngày snapshot dữ liệu nguồn (mặc định '2026-09-23')
--    - ingestion_time: Thời điểm nạp dữ liệu vào MySQL Staging
-- 4. Đánh chỉ mục (INDEX) inline tối ưu cho truy vấn lọc/JOIN của pipeline Silver (listing_id, date, snapshot_date)
-- 5. Đảm bảo tính khả lặp (Idempotent): Chạy nhiều lần không gây lỗi trùng index hay mất cấu trúc.
-- =============================================================================

USE airbnb_sg_2026;

-- =============================================================================
-- 1. BẢNG STAGING: stg_neighbourhoods
-- Nguồn dữ liệu: neighbourhoods.csv (2 cột nghiệp vụ + 3 cột metadata + 1 PK)
-- =============================================================================
CREATE TABLE IF NOT EXISTS stg_neighbourhoods (
    raw_id               INT UNSIGNED      NOT NULL AUTO_INCREMENT COMMENT 'Khóa chính tự tăng kỹ thuật của tầng staging',
    neighbourhood_group  VARCHAR(100)      NULL COMMENT 'Vùng địa lý lớn thô (Central Region, East Region,...)',
    neighbourhood        VARCHAR(100)      NULL COMMENT 'Tên khu vực quy hoạch thô (55 khu vực)',
    source_file          VARCHAR(100)      NOT NULL DEFAULT 'neighbourhoods.csv' COMMENT 'Tên tệp nguồn',
    snapshot_date        DATE              NOT NULL DEFAULT '2026-09-23' COMMENT 'Ngày snapshot dữ liệu',
    ingestion_time       DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm nạp vào staging',
    CONSTRAINT pk_stg_neighbourhoods PRIMARY KEY (raw_id),
    INDEX idx_stg_neighbourhoods_lookup (neighbourhood_group, neighbourhood),
    INDEX idx_stg_neighbourhoods_snapshot (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Staging thô danh mục khu vực địa lý từ tệp neighbourhoods.csv';


-- =============================================================================
-- 2. BẢNG STAGING: stg_calendar
-- Nguồn dữ liệu: calendar.csv.gz (5 cột nghiệp vụ + 3 cột metadata + 1 PK)
-- =============================================================================
CREATE TABLE IF NOT EXISTS stg_calendar (
    raw_id               BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT COMMENT 'Khóa chính tự tăng kỹ thuật của tầng staging',
    listing_id           BIGINT UNSIGNED   NULL COMMENT 'Mã phòng Airbnb thô (tương ứng listings.id)',
    date                 DATE              NULL COMMENT 'Ngày lịch thô (YYYY-MM-DD)',
    available            VARCHAR(10)       NULL COMMENT 'Trạng thái sẵn sàng đặt phòng thô (t/f)',
    minimum_nights       INT               NULL COMMENT 'Số đêm lưu trú tối thiểu thô',
    maximum_nights       INT               NULL COMMENT 'Số đêm lưu trú tối đa thô',
    source_file          VARCHAR(100)      NOT NULL DEFAULT 'calendar.csv.gz' COMMENT 'Tên tệp nguồn',
    snapshot_date        DATE              NOT NULL DEFAULT '2026-09-23' COMMENT 'Ngày snapshot dữ liệu',
    ingestion_time       DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm nạp vào staging',
    CONSTRAINT pk_stg_calendar PRIMARY KEY (raw_id),
    INDEX idx_stg_calendar_listing_date (listing_id, date),
    INDEX idx_stg_calendar_date (date),
    INDEX idx_stg_calendar_snapshot (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Staging thô lịch phòng và tình trạng sẵn sàng 365 ngày từ tệp calendar.csv.gz';


-- =============================================================================
-- 3. BẢNG STAGING: stg_reviews
-- Nguồn dữ liệu: reviews.csv.gz (6 cột nghiệp vụ + 3 cột metadata + 1 PK)
-- =============================================================================
CREATE TABLE IF NOT EXISTS stg_reviews (
    raw_id               BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT COMMENT 'Khóa chính tự tăng kỹ thuật của tầng staging',
    listing_id           BIGINT UNSIGNED   NULL COMMENT 'Mã phòng Airbnb thô (tương ứng listings.id)',
    id                   BIGINT UNSIGNED   NULL COMMENT 'Mã bài đánh giá thô (review_id)',
    date                 DATE              NULL COMMENT 'Ngày gửi đánh giá thô (YYYY-MM-DD)',
    reviewer_id          BIGINT UNSIGNED   NULL COMMENT 'Mã tài khoản khách đánh giá thô',
    reviewer_name        VARCHAR(255)      NULL COMMENT 'Tên người đánh giá thô',
    comments             MEDIUMTEXT        NULL COMMENT 'Nội dung nhận xét thô (hỗ trợ xuống dòng và ký tự quốc tế)',
    source_file          VARCHAR(100)      NOT NULL DEFAULT 'reviews.csv.gz' COMMENT 'Tên tệp nguồn',
    snapshot_date        DATE              NOT NULL DEFAULT '2026-09-23' COMMENT 'Ngày snapshot dữ liệu',
    ingestion_time       DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm nạp vào staging',
    CONSTRAINT pk_stg_reviews PRIMARY KEY (raw_id),
    INDEX idx_stg_reviews_listing_id (listing_id),
    INDEX idx_stg_reviews_id (id),
    INDEX idx_stg_reviews_date (date),
    INDEX idx_stg_reviews_snapshot (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Staging thô bài đánh giá của khách hàng từ tệp reviews.csv.gz';


-- =============================================================================
-- 4. BẢNG STAGING: stg_listings
-- Nguồn dữ liệu: listings.csv.gz (90 cột nghiệp vụ + 3 cột metadata + 1 PK)
-- =============================================================================
CREATE TABLE IF NOT EXISTS stg_listings (
    raw_id                                       BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT COMMENT 'Khóa chính tự tăng kỹ thuật của tầng staging',
    id                                           BIGINT UNSIGNED   NULL COMMENT 'Mã tin đăng Airbnb thô (Listings.id)',
    listing_url                                  VARCHAR(255)      NULL COMMENT 'Đường dẫn URL tin đăng',
    scrape_id                                    BIGINT UNSIGNED   NULL COMMENT 'Mã phiên thu thập dữ liệu nguồn',
    last_scraped                                 DATE              NULL COMMENT 'Ngày thu thập snapshot',
    source                                       VARCHAR(50)       NULL COMMENT 'Phân loại nguồn cào dữ liệu',
    name                                         VARCHAR(500)      NULL COMMENT 'Tiêu đề tin đăng thô',
    description                                  TEXT              NULL COMMENT 'Mô tả chi tiết phòng',
    neighborhood_overview                        TEXT              NULL COMMENT 'Mô tả tổng quan khu phố (100% NULL ở snapshot này)',
    picture_url                                  VARCHAR(500)      NULL COMMENT 'Đường dẫn ảnh đại diện tin đăng',
    host_id                                      BIGINT UNSIGNED   NULL COMMENT 'Mã tài khoản chủ nhà thô',
    host_url                                     VARCHAR(255)      NULL COMMENT 'Đường dẫn hồ sơ chủ nhà',
    host_profile_id                              BIGINT UNSIGNED   NULL COMMENT 'Mã hồ sơ định danh chủ nhà',
    host_profile_url                             VARCHAR(255)      NULL COMMENT 'Đường dẫn trang cá nhân chủ nhà',
    host_name                                    VARCHAR(255)      NULL COMMENT 'Tên hiển thị chủ nhà thô',
    host_since                                   DATE              NULL COMMENT 'Ngày tham gia làm chủ nhà (100% NULL ở snapshot này)',
    hosts_time_as_user_years                     SMALLINT          NULL COMMENT 'Số năm chủ nhà tham gia với tư cách người dùng',
    hosts_time_as_user_months                    SMALLINT          NULL COMMENT 'Số tháng lẻ tham gia với tư cách người dùng',
    hosts_time_as_host_years                     SMALLINT          NULL COMMENT 'Số năm chủ nhà tham gia tiếp đón khách',
    hosts_time_as_host_months                    SMALLINT          NULL COMMENT 'Số tháng lẻ tham gia tiếp đón khách',
    host_location                                VARCHAR(255)      NULL COMMENT 'Địa điểm cư trú chủ nhà khai báo',
    host_about                                   MEDIUMTEXT        NULL COMMENT 'Thông tin tự giới thiệu của chủ nhà',
    host_response_time                           VARCHAR(50)       NULL COMMENT 'Thời gian phản hồi trung bình (100% NULL ở snapshot này)',
    host_response_rate                           VARCHAR(20)       NULL COMMENT 'Tỷ lệ phản hồi thô (100% NULL ở snapshot này)',
    host_acceptance_rate                         VARCHAR(20)       NULL COMMENT 'Tỷ lệ chấp thuận thô (100% NULL ở snapshot này)',
    host_is_superhost                            VARCHAR(10)       NULL COMMENT 'Cờ chủ nhà siêu cấp thô (t/f)',
    host_thumbnail_url                           VARCHAR(500)      NULL COMMENT 'Ảnh thu nhỏ hồ sơ chủ nhà (100% NULL ở snapshot này)',
    host_picture_url                             VARCHAR(500)      NULL COMMENT 'Ảnh đại diện hồ sơ chủ nhà',
    host_neighbourhood                           VARCHAR(100)      NULL COMMENT 'Khu vực cư trú của chủ nhà (100% NULL ở snapshot này)',
    host_listings_count                          INT               NULL COMMENT 'Số lượng tin đăng của chủ nhà',
    host_total_listings_count                    INT               NULL COMMENT 'Tổng số tin đăng khai báo (100% NULL ở snapshot này)',
    host_verifications                           VARCHAR(100)      NULL COMMENT 'Hình thức xác minh hồ sơ chủ nhà',
    host_has_profile_pic                         VARCHAR(10)       NULL COMMENT 'Chủ nhà có ảnh đại diện thô (t/f)',
    host_identity_verified                       VARCHAR(10)       NULL COMMENT 'Chủ nhà đã xác minh danh tính thô (t/f)',
    neighbourhood                                VARCHAR(100)      NULL COMMENT 'Tên khu phố chưa chuẩn hóa (100% NULL ở snapshot này)',
    neighbourhood_cleansed                       VARCHAR(100)      NULL COMMENT 'Tên khu vực quy hoạch chuẩn hóa',
    neighbourhood_group_cleansed                 VARCHAR(100)      NULL COMMENT 'Tên vùng địa lý lớn chuẩn hóa',
    latitude                                     DECIMAL(11, 8)    NULL COMMENT 'Tọa độ vĩ độ địa lý WGS84',
    longitude                                    DECIMAL(11, 8)    NULL COMMENT 'Tọa độ kinh độ địa lý WGS84',
    property_type                                VARCHAR(100)      NULL COMMENT 'Loại hình bất động sản chi tiết',
    room_type                                    VARCHAR(50)       NULL COMMENT 'Phân loại hình thức thuê phòng',
    accommodates                                 SMALLINT          NULL COMMENT 'Sức chứa khách tối đa',
    bathrooms                                    DECIMAL(4, 1)     NULL COMMENT 'Số lượng phòng tắm số (100% NULL ở snapshot này)',
    bathrooms_text                               VARCHAR(50)       NULL COMMENT 'Chuỗi mô tả phòng tắm thô (ví dụ: 1 private bath)',
    bedrooms                                     SMALLINT          NULL COMMENT 'Số lượng phòng ngủ',
    beds                                         SMALLINT          NULL COMMENT 'Số lượng giường ngủ',
    amenities                                    MEDIUMTEXT        NULL COMMENT 'Danh sách tiện nghi dạng chuỗi JSON thô',
    price                                        VARCHAR(50)       NULL COMMENT 'Giá niêm yết thô nguyên bản kèm ký hiệu tiền tệ (ví dụ: $86.63)',
    price_quote_checkin_date                     DATE              NULL COMMENT 'Ngày check-in của lượt báo giá thô',
    price_quote_checkout_date                    DATE              NULL COMMENT 'Ngày check-out của lượt báo giá thô',
    price_quote_total_price                      DECIMAL(12, 2)    NULL COMMENT 'Tổng tiền báo giá thô',
    price_quote_price_per_night                  DECIMAL(10, 2)    NULL COMMENT 'Giá mỗi đêm báo giá thô',
    price_quote_raw                              MEDIUMTEXT        NULL COMMENT 'Chuỗi JSON chi tiết cấu phần giá và thuế thô',
    minimum_nights                               INT               NULL COMMENT 'Số đêm tối thiểu cho tin đăng',
    maximum_nights                               INT               NULL COMMENT 'Số đêm tối đa cho tin đăng',
    minimum_minimum_nights                       INT               NULL COMMENT 'Số đêm tối thiểu thấp nhất',
    maximum_minimum_nights                       INT               NULL COMMENT 'Số đêm tối thiểu cao nhất',
    minimum_maximum_nights                       INT               NULL COMMENT 'Số đêm tối đa thấp nhất',
    maximum_maximum_nights                       INT               NULL COMMENT 'Số đêm tối đa cao nhất',
    minimum_nights_avg_ntm                       DECIMAL(10, 2)    NULL COMMENT 'Số đêm tối thiểu trung bình các tháng tới',
    maximum_nights_avg_ntm                       DECIMAL(10, 2)    NULL COMMENT 'Số đêm tối đa trung bình các tháng tới',
    calendar_updated                             VARCHAR(50)       NULL COMMENT 'Thời điểm cập nhật lịch cuối (100% NULL ở snapshot này)',
    has_availability                             VARCHAR(10)       NULL COMMENT 'Có phòng khả dụng thô (t/f)',
    availability_30                              SMALLINT          NULL COMMENT 'Số ngày trống trong 30 ngày tới',
    availability_60                              SMALLINT          NULL COMMENT 'Số ngày trống trong 60 ngày tới',
    availability_90                              SMALLINT          NULL COMMENT 'Số ngày trống trong 90 ngày tới',
    availability_365                             SMALLINT          NULL COMMENT 'Số ngày trống trong 365 ngày tới',
    calendar_last_scraped                        DATE              NULL COMMENT 'Ngày cào dữ liệu lịch gần nhất',
    number_of_reviews                            INT               NULL COMMENT 'Tổng số lượt đánh giá tích lũy',
    number_of_reviews_ltm                        INT               NULL COMMENT 'Số lượt đánh giá trong 12 tháng qua',
    number_of_reviews_l30d                       INT               NULL COMMENT 'Số lượt đánh giá trong 30 ngày qua',
    availability_eoy                             SMALLINT          NULL COMMENT 'Số ngày trống từ snapshot đến hết năm dương lịch',
    number_of_reviews_ly                         INT               NULL COMMENT 'Số lượt đánh giá trong năm trước',
    estimated_occupancy_l365d                    SMALLINT          NULL COMMENT 'Ước tính số ngày có khách trong 365 ngày',
    estimated_revenue_l365d                      DECIMAL(12, 2)    NULL COMMENT 'Ước tính doanh thu 365 ngày qua',
    first_review                                 DATE              NULL COMMENT 'Ngày nhận bài đánh giá đầu tiên',
    last_review                                  DATE              NULL COMMENT 'Ngày nhận bài đánh giá gần nhất',
    review_scores_rating                         DECIMAL(4, 2)     NULL COMMENT 'Điểm đánh giá tổng thể thô (1..5)',
    review_scores_accuracy                       DECIMAL(4, 2)     NULL COMMENT 'Điểm đánh giá độ chính xác thô (1..5)',
    review_scores_cleanliness                    DECIMAL(4, 2)     NULL COMMENT 'Điểm đánh giá vệ sinh thô (1..5)',
    review_scores_checkin                        DECIMAL(4, 2)     NULL COMMENT 'Điểm đánh giá quy trình nhận phòng thô (1..5)',
    review_scores_communication                  DECIMAL(4, 2)     NULL COMMENT 'Điểm đánh giá mức độ giao tiếp thô (1..5)',
    review_scores_location                       DECIMAL(4, 2)     NULL COMMENT 'Điểm đánh giá vị trí thô (1..5)',
    review_scores_value                          DECIMAL(4, 2)     NULL COMMENT 'Điểm đánh giá giá trị thô (1..5)',
    license                                      VARCHAR(100)      NULL COMMENT 'Mã giấy phép lưu trú khai báo thô',
    instant_bookable                             VARCHAR(10)       NULL COMMENT 'Cho phép đặt ngay thô (100% NULL ở snapshot này)',
    calculated_host_listings_count               INT               NULL COMMENT 'Số tin đăng chủ nhà tính toán lại',
    calculated_host_listings_count_entire_homes  INT               NULL COMMENT 'Số căn nguyên căn của chủ nhà',
    calculated_host_listings_count_private_rooms INT               NULL COMMENT 'Số phòng riêng của chủ nhà',
    calculated_host_listings_count_shared_rooms  INT               NULL COMMENT 'Số phòng chung của chủ nhà',
    reviews_per_month                            DECIMAL(6, 2)     NULL COMMENT 'Tần suất đánh giá bình quân mỗi tháng',
    source_file                                  VARCHAR(100)      NOT NULL DEFAULT 'listings.csv.gz' COMMENT 'Tên tệp nguồn',
    snapshot_date                                DATE              NOT NULL DEFAULT '2026-09-23' COMMENT 'Ngày snapshot dữ liệu',
    ingestion_time                               DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm nạp vào staging',
    CONSTRAINT pk_stg_listings PRIMARY KEY (raw_id),
    INDEX idx_stg_listings_id (id),
    INDEX idx_stg_listings_host_id (host_id),
    INDEX idx_stg_listings_snapshot (snapshot_date),
    INDEX idx_stg_listings_neighbourhood (neighbourhood_cleansed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Staging thô chi tiết tin đăng phòng Airbnb từ tệp listings.csv.gz';
