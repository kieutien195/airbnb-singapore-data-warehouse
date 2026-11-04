# Task 2.1 – Kết luận khảo sát nguồn

- Reviews.id: 41,191 mã khác nhau / 46,000 dòng; 4,809 dòng lặp ID sau lần đầu. Khóa (listing_id,id) có 0 dòng trùng dư trong snapshot này; cần xác minh ngữ nghĩa nguồn trước DDL.

- Listings.neighbourhood có 3,208 NULL; dùng cặp neighbourhood_group_cleansed/neighbourhood_cleansed để nối khu vực.

- Danh mục có 13 khu vực không có listing; không tự coi là lỗi.

- Listings.price và price_quote_price_per_night gần nghĩa nhưng không mặc định thay thế nhau; kiểm tra currency và chênh lệch trước ETL.

- Calendar hiện không có cột price. Reviews không có điểm rating; review_scores_rating lấy từ Listings.

- Các cột toàn NULL cần ghi nhận và quyết định phạm vi sử dụng, không suy kiểu nghiệp vụ từ float64.

- Không JOIN Calendar và Reviews ở mức chi tiết để tính KPI vì hai bảng đều nhiều dòng trên một listing.

- snapshot_date lấy từ docs/source_inventory.csv; không đồng nhất với last_scraped hoặc ngày phát sinh review.
