# MySQL và KPI

Minh phụ trách SQL khởi tạo database, staging, warehouse, load và KPI views. Xác định grain, khóa và dimension dùng chung trước khi tạo schema; đối chiếu KPI với Pandas.

## Khởi tạo môi trường

Chạy [`00_init_database.sql`](00_init_database.sql) bằng một tài khoản quản trị MySQL để tạo (hoặc chuẩn hóa mặc định của) database `airbnb_sg_2026` với `utf8mb4`. Script cũng kiểm tra phiên bản, charset/collation và tạo/xóa một bảng tạm để xác nhận quyền DDL và truy vấn.

Các bước tạo tài khoản ứng dụng, kết nối Python/Power BI, sao lưu và kiểm tra từ máy thành viên khác nằm trong [`docs/mysql_setup.md`](../docs/mysql_setup.md).
