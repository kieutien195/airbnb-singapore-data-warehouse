-- =============================================================================
-- Task 2.5 (Schema Draft) & Chuẩn bị cho Task 3.5:
-- DDL Khởi tạo Mô hình Kho Dữ liệu Đa chiều (Fact Constellation) trên MySQL 8.0
-- Database: airbnb_sg_2026 | Charset: utf8mb4 | Collation: utf8mb4_0900_ai_ci
-- =============================================================================

-- Chọn schema đích theo MYSQL_DATABASE trong .env trước khi chạy; không cố định USE ở đây.

-- Tùy chọn: Xóa bảng cũ theo thứ tự khóa ngoại nếu muốn tạo lại từ đầu (uncomment khi cần):
-- SET FOREIGN_KEY_CHECKS = 0;
-- DROP TABLE IF EXISTS fact_review;
-- DROP TABLE IF EXISTS fact_calendar;
-- DROP TABLE IF EXISTS fact_listing_snapshot;
-- DROP TABLE IF EXISTS dim_listing;
-- DROP TABLE IF EXISTS dim_neighbourhood;
-- DROP TABLE IF EXISTS dim_date;
-- SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------
-- 1. DIMENSION: dim_date (Chiều thời gian dùng chung: 2011-01-01 .. 2027-12-31)
--    Grain: 1 dòng = 1 ngày dương lịch (full_date)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_sk          INT               NOT NULL COMMENT 'Surrogate key định dạng YYYYMMDD (ví dụ 20260923)',
    full_date        DATE              NOT NULL COMMENT 'Ngày dương lịch chuẩn YYYY-MM-DD',
    day_of_month     TINYINT UNSIGNED  NOT NULL COMMENT 'Ngày trong tháng (1..31)',
    day_of_week_iso  TINYINT UNSIGNED  NOT NULL COMMENT 'Thứ chuẩn ISO (1=Monday .. 7=Sunday)',
    day_name         VARCHAR(15)       NOT NULL COMMENT 'Tên thứ trong tuần (Monday..Sunday)',
    is_weekend       BOOLEAN           NOT NULL COMMENT '1 nếu Thứ Bảy/Chủ Nhật, 0 nếu ngày thường',
    week_of_year     TINYINT UNSIGNED  NOT NULL COMMENT 'Tuần ISO trong năm (1..53)',
    month_num        TINYINT UNSIGNED  NOT NULL COMMENT 'Tháng trong năm (1..12)',
    month_name       VARCHAR(15)       NOT NULL COMMENT 'Tên tháng (January..December)',
    `year_month`     CHAR(7)           NOT NULL COMMENT 'Chuỗi Năm-Tháng YYYY-MM',
    quarter_num      TINYINT UNSIGNED  NOT NULL COMMENT 'Quý trong năm (1..4)',
    year_quarter     CHAR(7)           NOT NULL COMMENT 'Chuỗi Năm-Quý YYYY-Q#',
    year_num         SMALLINT UNSIGNED NOT NULL COMMENT 'Năm dương lịch (2011..2027)',
    CONSTRAINT pk_dim_date PRIMARY KEY (date_sk),
    CONSTRAINT uq_dim_date_full_date UNIQUE (full_date),
    CONSTRAINT chk_dim_date_month CHECK (month_num BETWEEN 1 AND 12),
    CONSTRAINT chk_dim_date_quarter CHECK (quarter_num BETWEEN 1 AND 4),
    CONSTRAINT chk_dim_date_weekend CHECK (is_weekend IN (0, 1)),
    INDEX idx_dim_date_year_month (year_num, month_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Bảng chiều thời gian dùng chung cho snapshot_date, calendar_date và review_date';


-- -----------------------------------------------------------------------------
-- 2. DIMENSION: dim_neighbourhood (Chiều phân cấp khu vực địa lý Singapore)
--    Grain: 1 dòng = 1 khu vực quy hoạch (neighbourhood_name) thuộc 1 vùng (neighbourhood_group)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_neighbourhood (
    neighbourhood_sk    INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Surrogate key khu vực địa lý',
    neighbourhood_group VARCHAR(50)  NOT NULL COMMENT 'Vùng địa lý lớn (5 vùng tại Singapore)',
    neighbourhood_name  VARCHAR(100) NOT NULL COMMENT 'Tên khu vực quy hoạch chuẩn hóa (55 khu vực)',
    snapshot_date       DATE         NOT NULL COMMENT 'Ngày snapshot danh mục nguồn (2026-09-23)',
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dim_neighbourhood PRIMARY KEY (neighbourhood_sk),
    CONSTRAINT uq_dim_neighbourhood_bk UNIQUE (neighbourhood_group, neighbourhood_name),
    CONSTRAINT uq_dim_neighbourhood_name UNIQUE (neighbourhood_name),
    INDEX idx_dim_neighbourhood_group (neighbourhood_group)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Bảng chiều danh mục khu vực địa lý chuẩn từ Inside Airbnb';


-- -----------------------------------------------------------------------------
-- 3. DIMENSION: dim_listing (Chiều thuộc tính mô tả tin đăng & chủ nhà)
--    Grain: 1 dòng = 1 bản ghi mô tả tin đăng tại 1 snapshot (listing_id, snapshot_date)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_listing (
    listing_sk                 BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT COMMENT 'Surrogate key phiên bản tin đăng tại snapshot',
    listing_id                 BIGINT UNSIGNED   NOT NULL COMMENT 'Mã định danh tin đăng Airbnb gốc (Listings.id)',
    snapshot_date              DATE              NOT NULL COMMENT 'Ngày snapshot (2026-09-23)',
    snapshot_date_sk           INT               NOT NULL COMMENT 'FK tham chiếu dim_date(date_sk)',
    neighbourhood_sk           INT UNSIGNED      NOT NULL COMMENT 'FK tham chiếu dim_neighbourhood(neighbourhood_sk)',
    scrape_id                  BIGINT UNSIGNED   NOT NULL COMMENT 'Mã phiên thu thập dữ liệu của nguồn',
    last_scraped_date          DATE              NOT NULL COMMENT 'Ngày thu thập tin đăng lần cuối',
    calendar_last_scraped_date DATE              NOT NULL COMMENT 'Ngày thu thập lịch lần cuối',
    source_type                VARCHAR(50)       NULL     COMMENT 'Nguồn bản ghi trong scrape (ví dụ previous scrape)',
    listing_name               VARCHAR(300)      NOT NULL COMMENT 'Tên tiêu đề tin đăng',
    listing_url                VARCHAR(255)      NOT NULL COMMENT 'Đường dẫn URL của tin đăng',
    picture_url                VARCHAR(500)      NULL     COMMENT 'Đường dẫn ảnh đại diện tin đăng',
    property_type              VARCHAR(100)      NOT NULL COMMENT 'Loại hình cơ sở lưu trú chi tiết',
    room_type                  VARCHAR(50)       NOT NULL COMMENT 'Loại phòng (Entire home/apt, Private room, Hotel room, Shared room)',
    accommodates               INT UNSIGNED      NOT NULL COMMENT 'Sức chứa khách tối đa (số nguyên dương 1..16)',
    bedrooms                   INT UNSIGNED      NULL     COMMENT 'Số phòng ngủ (giữ NULL nếu khuyết)',
    beds                       INT UNSIGNED      NULL     COMMENT 'Số giường (giữ NULL nếu khuyết)',
    bathrooms_text             VARCHAR(100)      NULL     COMMENT 'Mô tả số lượng và loại phòng tắm',
    latitude                   DECIMAL(10,7)     NOT NULL COMMENT 'Vĩ độ địa lý',
    longitude                  DECIMAL(10,7)     NOT NULL COMMENT 'Kinh độ địa lý',
    has_availability           BOOLEAN           NULL     COMMENT 'Cờ có thông tin mở lịch (1=True, 0=False, NULL)',
    license                    VARCHAR(150)      NULL     COMMENT 'Mã giấy phép đăng ký lưu trú',
    host_id                    BIGINT UNSIGNED   NOT NULL COMMENT 'Mã định danh chủ nhà (denormalized)',
    host_profile_id            BIGINT UNSIGNED   NULL     COMMENT 'Mã hồ sơ chủ nhà',
    host_name                  VARCHAR(150)      NOT NULL COMMENT 'Tên hiển thị của chủ nhà',
    host_location              VARCHAR(150)      NULL     COMMENT 'Địa điểm khai báo của chủ nhà',
    host_is_superhost          BOOLEAN           NULL     COMMENT 'Cờ chủ nhà Superhost (1=True, 0=False)',
    host_has_profile_pic       BOOLEAN           NULL     COMMENT 'Cờ chủ nhà có ảnh đại diện (1=True, 0=False)',
    host_identity_verified     BOOLEAN           NULL     COMMENT 'Cờ chủ nhà đã xác minh danh tính (1=True, 0=False)',
    hosts_time_as_user_years   SMALLINT UNSIGNED NULL     COMMENT 'Số năm tham gia Airbnb của chủ nhà',
    hosts_time_as_user_months  TINYINT UNSIGNED  NULL     COMMENT 'Số tháng lẻ tham gia Airbnb',
    hosts_time_as_host_years   SMALLINT UNSIGNED NULL     COMMENT 'Số năm hoạt động với tư cách host',
    hosts_time_as_host_months  TINYINT UNSIGNED  NULL     COMMENT 'Số tháng lẻ hoạt động với tư cách host',
    first_review_date          DATE              NULL     COMMENT 'Ngày đánh giá đầu tiên',
    last_review_date           DATE              NULL     COMMENT 'Ngày đánh giá gần nhất',
    created_at                 DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dim_listing PRIMARY KEY (listing_sk),
    CONSTRAINT uq_dim_listing_bk UNIQUE (listing_id, snapshot_date),
    CONSTRAINT fk_dim_listing_snapshot_date FOREIGN KEY (snapshot_date_sk) REFERENCES dim_date (date_sk),
    CONSTRAINT fk_dim_listing_neighbourhood FOREIGN KEY (neighbourhood_sk) REFERENCES dim_neighbourhood (neighbourhood_sk),
    CONSTRAINT chk_dim_listing_accommodates CHECK (accommodates > 0),
    CONSTRAINT chk_dim_listing_lat CHECK (latitude BETWEEN -90.0 AND 90.0),
    CONSTRAINT chk_dim_listing_lon CHECK (longitude BETWEEN -180.0 AND 180.0),
    INDEX idx_dim_listing_room_type (room_type),
    INDEX idx_dim_listing_neighbourhood (neighbourhood_sk),
    INDEX idx_dim_listing_host_id (host_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Bảng chiều mô tả tin đăng và chủ nhà theo từng kỳ snapshot';


-- -----------------------------------------------------------------------------
-- 4. FACT: fact_listing_snapshot (Bảng sự kiện chụp trạng thái định lượng tin đăng)
--    Grain: 1 dòng = 1 listing tại 1 snapshot_date (3,208 dòng cho snapshot 2026-09-23)
--    Phục vụ: KPI-01, KPI-02, KPI-03, KPI-05, SUP-01 (RQ1, RQ2, RQ4)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_listing_snapshot (
    listing_snapshot_sk                          BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT COMMENT 'Surrogate key bảng fact_listing_snapshot',
    listing_sk                                   BIGINT UNSIGNED   NOT NULL COMMENT 'FK tham chiếu dim_listing(listing_sk)',
    neighbourhood_sk                             INT UNSIGNED      NOT NULL COMMENT 'FK tham chiếu dim_neighbourhood(neighbourhood_sk)',
    snapshot_date_sk                             INT               NOT NULL COMMENT 'FK tham chiếu dim_date(date_sk)',
    listing_id                                   BIGINT UNSIGNED   NOT NULL COMMENT 'Natural key thành phần 1 (Listings.id)',
    snapshot_date                                DATE              NOT NULL COMMENT 'Natural key thành phần 2 (2026-09-23)',
    listed_price_raw_amount                      DECIMAL(12,2)     NULL     COMMENT 'Giá niêm yết dạng số sau khi bỏ ký hiệu tiền tệ (2,728 dòng)',
    quote_currency                               CHAR(3)           NULL     COMMENT 'Mã tiền tệ trích từ price_quote_raw.quote.currency',
    is_price_sgd_verified                        BOOLEAN           NOT NULL DEFAULT 0 COMMENT '1 nếu có giá > 0 và quote_currency = SGD (2,725 dòng)',
    listed_price_sgd                             DECIMAL(12,2)     NULL     COMMENT 'Giá niêm yết SGD hợp lệ dùng tính KPI-02 (2,725 dòng, Median=202.83)',
    price_quote_price_per_night                  DECIMAL(12,2)     NULL     COMMENT 'Giá mỗi đêm từ báo giá tham chiếu',
    price_quote_total_price                      DECIMAL(14,2)     NULL     COMMENT 'Tổng giá từ báo giá tham chiếu',
    price_quote_checkin_date                     DATE              NULL     COMMENT 'Ngày check-in báo giá tham chiếu',
    price_quote_checkout_date                    DATE              NULL     COMMENT 'Ngày check-out báo giá tham chiếu',
    minimum_nights                               INT UNSIGNED      NULL     COMMENT 'Số đêm lưu trú tối thiểu',
    maximum_nights                               INT UNSIGNED      NULL     COMMENT 'Số đêm lưu trú tối đa',
    minimum_minimum_nights                       INT UNSIGNED      NULL     COMMENT 'Cực tiểu của số đêm lưu trú tối thiểu',
    maximum_minimum_nights                       INT UNSIGNED      NULL     COMMENT 'Cực đại của số đêm lưu trú tối thiểu',
    minimum_maximum_nights                       INT UNSIGNED      NULL     COMMENT 'Cực tiểu của số đêm lưu trú tối đa',
    maximum_maximum_nights                       INT UNSIGNED      NULL     COMMENT 'Cực đại của số đêm lưu trú tối đa',
    minimum_nights_avg_ntm                       DECIMAL(10,2)     NOT NULL COMMENT 'Trung bình số đêm tối thiểu 12 tháng tới (giữ phần thập phân)',
    maximum_nights_avg_ntm                       DECIMAL(10,2)     NOT NULL COMMENT 'Trung bình số đêm tối đa 12 tháng tới (giữ phần thập phân)',
    availability_30                              SMALLINT UNSIGNED NOT NULL COMMENT 'Số đêm mở lịch trong 30 ngày tới',
    availability_60                              SMALLINT UNSIGNED NOT NULL COMMENT 'Số đêm mở lịch trong 60 ngày tới',
    availability_90                              SMALLINT UNSIGNED NOT NULL COMMENT 'Số đêm mở lịch trong 90 ngày tới',
    availability_365                             SMALLINT UNSIGNED NOT NULL COMMENT 'Số đêm mở lịch trong 365 ngày tới',
    availability_eoy                             SMALLINT UNSIGNED NOT NULL COMMENT 'Số đêm mở lịch đến cuối năm',
    number_of_reviews                            INT UNSIGNED      NOT NULL COMMENT 'Tổng số lượt đánh giá tích lũy (dùng tính SUP-01)',
    number_of_reviews_ltm                        INT UNSIGNED      NOT NULL COMMENT 'Số lượt đánh giá trong 12 tháng gần nhất',
    number_of_reviews_l30d                       INT UNSIGNED      NOT NULL COMMENT 'Số lượt đánh giá trong 30 ngày gần nhất',
    number_of_reviews_ly                         INT UNSIGNED      NOT NULL COMMENT 'Số lượt đánh giá trong năm trước',
    reviews_per_month                            DECIMAL(8,2)      NULL     COMMENT 'Số lượt đánh giá trung bình mỗi tháng',
    review_scores_rating                         DECIMAL(4,2)      NULL     COMMENT 'Điểm đánh giá tổng thể thang 1..5 (dùng tính KPI-05)',
    review_scores_accuracy                       DECIMAL(4,2)      NULL     COMMENT 'Điểm độ chính xác',
    review_scores_cleanliness                    DECIMAL(4,2)      NULL     COMMENT 'Điểm độ sạch sẽ',
    review_scores_checkin                        DECIMAL(4,2)      NULL     COMMENT 'Điểm nhận phòng',
    review_scores_communication                  DECIMAL(4,2)      NULL     COMMENT 'Điểm giao tiếp',
    review_scores_location                       DECIMAL(4,2)      NULL     COMMENT 'Điểm vị trí',
    review_scores_value                          DECIMAL(4,2)      NULL     COMMENT 'Điểm giá trị',
    host_listings_count                          INT UNSIGNED      NOT NULL COMMENT 'Số tin đăng của chủ nhà theo hồ sơ',
    calculated_host_listings_count               INT UNSIGNED      NOT NULL COMMENT 'Tổng số tin đăng của chủ nhà trong snapshot',
    calculated_host_listings_count_entire_homes  INT UNSIGNED      NOT NULL COMMENT 'Số tin đăng nguyên căn của chủ nhà',
    calculated_host_listings_count_private_rooms INT UNSIGNED      NOT NULL COMMENT 'Số tin đăng phòng riêng của chủ nhà',
    calculated_host_listings_count_shared_rooms  INT UNSIGNED      NOT NULL COMMENT 'Số tin đăng phòng chung của chủ nhà',
    estimated_occupancy_l365d                    INT UNSIGNED      NOT NULL COMMENT 'Số ngày lấp đầy ước tính của nguồn (không phải giao dịch thực)',
    estimated_revenue_l365d                      DECIMAL(14,2)     NULL     COMMENT 'Doanh thu ước tính của nguồn (không phải doanh thu thực)',
    created_at                                   DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_fact_listing_snapshot PRIMARY KEY (listing_snapshot_sk),
    CONSTRAINT uq_fact_listing_snapshot_grain UNIQUE (listing_id, snapshot_date),
    CONSTRAINT uq_fact_listing_sk_snap UNIQUE (listing_sk, snapshot_date_sk),
    CONSTRAINT fk_fls_listing FOREIGN KEY (listing_sk) REFERENCES dim_listing (listing_sk),
    CONSTRAINT fk_fls_neighbourhood FOREIGN KEY (neighbourhood_sk) REFERENCES dim_neighbourhood (neighbourhood_sk),
    CONSTRAINT fk_fls_snapshot_date FOREIGN KEY (snapshot_date_sk) REFERENCES dim_date (date_sk),
    CONSTRAINT chk_fls_price_sgd CHECK (listed_price_sgd IS NULL OR listed_price_sgd > 0),
    CONSTRAINT chk_fls_rating CHECK (review_scores_rating IS NULL OR (review_scores_rating BETWEEN 1.00 AND 5.00)),
    INDEX idx_fls_neighbourhood_snap (neighbourhood_sk, snapshot_date_sk),
    INDEX idx_fls_price_sgd (is_price_sgd_verified, listed_price_sgd)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Bảng Fact định lượng cấp Listing tại mỗi kỳ Snapshot';


-- -----------------------------------------------------------------------------
-- 5. FACT: fact_calendar (Bảng sự kiện lịch mở/đóng theo ngày của từng tin đăng)
--    Grain: 1 dòng = 1 listing tại 1 ngày lịch (calendar_date) trong 1 snapshot_date
--    Phục vụ: KPI-04 (RQ3) trên cửa sổ ngày 2026-09-25 .. 2027-09-25 (1,170,950 dòng)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_calendar (
    calendar_sk      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Surrogate key bảng fact_calendar',
    listing_sk       BIGINT UNSIGNED NOT NULL COMMENT 'FK tham chiếu dim_listing(listing_sk)',
    neighbourhood_sk INT UNSIGNED    NOT NULL COMMENT 'FK tham chiếu dim_neighbourhood(neighbourhood_sk)',
    calendar_date_sk INT             NOT NULL COMMENT 'FK tham chiếu ngày lịch trong dim_date(date_sk)',
    snapshot_date_sk INT             NOT NULL COMMENT 'FK tham chiếu ngày snapshot trong dim_date(date_sk)',
    listing_id       BIGINT UNSIGNED NOT NULL COMMENT 'Natural key thành phần 1 (Calendar.listing_id)',
    calendar_date    DATE            NOT NULL COMMENT 'Natural key thành phần 2 (Calendar.date)',
    snapshot_date    DATE            NOT NULL COMMENT 'Natural key thành phần 3 (2026-09-23)',
    is_available     BOOLEAN         NOT NULL COMMENT '1 nếu available=t (còn mở lịch), 0 nếu available=f (đóng lịch)',
    minimum_nights   INT UNSIGNED    NOT NULL COMMENT 'Số đêm lưu trú tối thiểu áp dụng cho ngày lịch',
    maximum_nights   INT UNSIGNED    NOT NULL COMMENT 'Số đêm lưu trú tối đa áp dụng cho ngày lịch',
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_fact_calendar PRIMARY KEY (calendar_sk),
    CONSTRAINT uq_fact_calendar_grain UNIQUE (listing_id, calendar_date, snapshot_date),
    CONSTRAINT fk_fc_listing FOREIGN KEY (listing_sk) REFERENCES dim_listing (listing_sk),
    CONSTRAINT fk_fc_neighbourhood FOREIGN KEY (neighbourhood_sk) REFERENCES dim_neighbourhood (neighbourhood_sk),
    CONSTRAINT fk_fc_calendar_date FOREIGN KEY (calendar_date_sk) REFERENCES dim_date (date_sk),
    CONSTRAINT fk_fc_snapshot_date FOREIGN KEY (snapshot_date_sk) REFERENCES dim_date (date_sk),
    CONSTRAINT chk_fc_available CHECK (is_available IN (0, 1)),
    CONSTRAINT chk_fc_min_nights CHECK (minimum_nights > 0),
    CONSTRAINT chk_fc_max_nights CHECK (maximum_nights > 0),
    INDEX idx_fc_snapshot_caldate (snapshot_date_sk, calendar_date_sk, is_available),
    INDEX idx_fc_listing_caldate (listing_sk, calendar_date_sk),
    INDEX idx_fc_neighbourhood_avail (neighbourhood_sk, is_available)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Bảng Fact trạng thái mở/đóng lịch theo từng listing - ngày lịch - snapshot';


-- -----------------------------------------------------------------------------
-- 6. FACT: fact_review (Bảng sự kiện đánh giá lịch sử của người dùng)
--    Grain: 1 dòng = 1 bản ghi đánh giá theo cặp (listing_id, review_id) tại 1 snapshot_date
--    Phục vụ: SUP-02 (RQ4) (46,000 dòng cho snapshot 2026-09-23)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_review (
    review_sk        BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT 'Surrogate key bảng fact_review',
    listing_sk       BIGINT UNSIGNED  NOT NULL COMMENT 'FK tham chiếu dim_listing(listing_sk)',
    neighbourhood_sk INT UNSIGNED     NOT NULL COMMENT 'FK tham chiếu dim_neighbourhood(neighbourhood_sk)',
    review_date_sk   INT              NOT NULL COMMENT 'FK tham chiếu ngày đánh giá trong dim_date(date_sk)',
    snapshot_date_sk INT              NOT NULL COMMENT 'FK tham chiếu ngày snapshot trong dim_date(date_sk)',
    listing_id       BIGINT UNSIGNED  NOT NULL COMMENT 'Natural key thành phần 1 (Reviews.listing_id)',
    review_id        BIGINT UNSIGNED  NOT NULL COMMENT 'Natural key thành phần 2 / Degenerate key (Reviews.id)',
    review_date      DATE             NOT NULL COMMENT 'Ngày đăng đánh giá (Reviews.date)',
    snapshot_date    DATE             NOT NULL COMMENT 'Natural key thành phần 3 (2026-09-23)',
    reviewer_id      BIGINT UNSIGNED  NOT NULL COMMENT 'Mã người viết đánh giá',
    reviewer_name    VARCHAR(150)     NOT NULL COMMENT 'Tên hiển thị người viết đánh giá',
    has_comment      BOOLEAN          NOT NULL DEFAULT 1 COMMENT '1 nếu có nội dung bình luận, 0 nếu comments IS NULL',
    comment_length   INT UNSIGNED     NOT NULL DEFAULT 0 COMMENT 'Độ dài ký tự của bình luận',
    review_count     TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'Thước đo cộng được (=1) phục vụ đếm SUP-02',
    created_at       DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_fact_review PRIMARY KEY (review_sk),
    CONSTRAINT uq_fact_review_grain UNIQUE (listing_id, review_id, snapshot_date),
    CONSTRAINT fk_fr_listing FOREIGN KEY (listing_sk) REFERENCES dim_listing (listing_sk),
    CONSTRAINT fk_fr_neighbourhood FOREIGN KEY (neighbourhood_sk) REFERENCES dim_neighbourhood (neighbourhood_sk),
    CONSTRAINT fk_fr_review_date FOREIGN KEY (review_date_sk) REFERENCES dim_date (date_sk),
    CONSTRAINT fk_fr_snapshot_date FOREIGN KEY (snapshot_date_sk) REFERENCES dim_date (date_sk),
    CONSTRAINT chk_fr_has_comment CHECK (has_comment IN (0, 1)),
    CONSTRAINT chk_fr_review_count CHECK (review_count = 1),
    INDEX idx_fr_review_date (review_date_sk),
    INDEX idx_fr_listing_date (listing_sk, review_date_sk),
    INDEX idx_fr_neighbourhood_date (neighbourhood_sk, review_date_sk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Bảng Fact ghi nhận sự kiện đánh giá theo khóa ghép (listing_id, review_id, snapshot_date)';
