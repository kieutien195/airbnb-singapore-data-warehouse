-- One-time, non-destructive migration for the previous staging schema.
-- Select the MYSQL_DATABASE schema before running this file.
-- Review row counts first. DECIMAL(11,8) values already stored have already
-- lost source precision; reload listings from data/raw after this migration
-- if stg_listings contains rows.

ALTER TABLE stg_neighbourhoods
    CHANGE COLUMN ingestion_time ingested_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm nạp vào staging';

ALTER TABLE stg_calendar
    CHANGE COLUMN ingestion_time ingested_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm nạp vào staging';

ALTER TABLE stg_reviews
    CHANGE COLUMN ingestion_time ingested_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm nạp vào staging';

ALTER TABLE stg_listings
    MODIFY COLUMN latitude VARCHAR(50) NULL
        COMMENT 'Chuỗi vĩ độ thô từ nguồn; chuẩn hóa kiểu số ở Silver',
    MODIFY COLUMN longitude VARCHAR(50) NULL
        COMMENT 'Chuỗi kinh độ thô từ nguồn; chuẩn hóa kiểu số ở Silver',
    CHANGE COLUMN ingestion_time ingested_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm nạp vào staging';
