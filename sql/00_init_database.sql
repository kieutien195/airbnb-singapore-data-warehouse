-- Task 1.5: khởi tạo database Airbnb Singapore trên MySQL 8.0.
-- Chạy bằng một tài khoản quản trị (ví dụ root) trong MySQL Workbench.
-- Script không chứa tài khoản hoặc mật khẩu.

CREATE DATABASE IF NOT EXISTS airbnb_sg_2026
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

-- Cập nhật mặc định cho các bảng tạo mới; không chuyển đổi dữ liệu bảng đã tồn tại.
ALTER DATABASE airbnb_sg_2026
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE airbnb_sg_2026;

SELECT
    VERSION() AS mysql_version,
    DATABASE() AS selected_database,
    @@character_set_database AS database_character_set,
    @@collation_database AS database_collation,
    @@character_set_connection AS connection_character_set;

-- Bài kiểm tra không để lại bảng hay dữ liệu sau khi chạy.
CREATE TEMPORARY TABLE task_1_5_connection_test (
    test_id INT NOT NULL PRIMARY KEY,
    test_message VARCHAR(100) CHARACTER SET utf8mb4 NOT NULL
) ENGINE=InnoDB;

INSERT INTO task_1_5_connection_test (test_id, test_message)
VALUES (1, 'Airbnb Singapore - kiểm tra tiếng Việt');

SELECT test_id, test_message
FROM task_1_5_connection_test
WHERE test_id = 1;

DROP TEMPORARY TABLE task_1_5_connection_test;
