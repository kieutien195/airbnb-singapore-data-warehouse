-- Task 3.6: DDL hỗ trợ nạp kho Gold.
-- Loader chính: python scripts/load_warehouse.py
-- Loader dùng Gold CSV từ 3.4 và tự chạy DDL kiểm toán này trước transaction.
-- Đối chiếu độc lập: sql/03_validate_gold_against_raw.sql.

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
