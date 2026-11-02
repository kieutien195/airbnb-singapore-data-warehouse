
# Khuyến nghị xử lý dữ liệu – Task 2.3

## 1. Mục đích

Tài liệu tổng hợp các vấn đề chất lượng dữ liệu được ghi nhận
trong quá trình EDA của bộ dữ liệu Singapore Airbnb.

## 2. Nguyên tắc

- Không tự động xóa NULL.
- Không xóa Duplicates khi chưa xác định đúng grain.
- Không tự động xóa Outliers chỉ dựa trên IQR.
- Giữ nguyên dữ liệu nguồn trong quá trình EDA.

## 3. Các khuyến nghị

| dataset | issue | recommendation | priority | note |
| --- | --- | --- | --- | --- |
| Listings | NULL | Đánh giá ý nghĩa từng trường trước khi quyết định giữ nguyên, loại bỏ hoặc thay thế NULL. | High | Không thay thế NULL đồng loạt vì mỗi trường có ý nghĩa nghiệp vụ khác nhau. |
| Listings | Outliers | Kiểm tra các giá trị ngoài ngưỡng IQR kết hợp với ngữ cảnh nghiệp vụ. | Medium | Outliers không đồng nghĩa với dữ liệu sai; không tự động loại bỏ. |
| Calendar | Data volume | Tổng hợp dữ liệu Calendar theo listing_id trước khi kết hợp với bảng có quan hệ một-nhiều khác. | High | Calendar có nhiều bản ghi cho một listing. |
| Reviews | Duplicates | Kiểm tra riêng id và cặp (listing_id, id); giải thích grain quan sát. | High | Báo cáo id riêng lẻ và khóa ghép; không tự động xóa theo id. |
| Listings - Calendar - Reviews | JOIN fan-out | Tổng hợp Calendar và Reviews theo listing_id trước khi JOIN nếu cần một dòng trên mỗi listing. | High | JOIN trực tiếp các bảng một-nhiều có thể làm nhân bản số dòng. |
| Listings - Neighbourhoods | Referential integrity | Đối chiếu theo cặp neighbourhood_group_cleansed và neighbourhood_cleansed. | Medium | Bảng Neighbourhoods sử dụng neighbourhood_group và neighbourhood. |
| Listings | NULL: price_quote_price_per_night | Không điền 0 thay cho dữ liệu thiếu; ghi rõ mẫu số có dữ liệu khi phân tích. | High | 483/3,208 bản ghi (15.0561%). Số lượng giá trị NULL tại trường dữ liệu. |
| Listings | NULL: review_scores_rating | Không điền 0 thay cho dữ liệu thiếu; ghi rõ mẫu số có dữ liệu khi phân tích. | High | 1,369/3,208 bản ghi (42.6746%). Số lượng giá trị NULL tại trường dữ liệu. |
| Listings | Outliers: price_quote_price_per_night | Giữ nguyên để xem xét theo ngữ cảnh; không tự động xóa. | Medium | 134/2,725 bản ghi (4.9174%). Q1=99.9000; Median=202.8300; Q3=333.3100; IQR=233.4100; lower=-250.2150; upper=683.4250. Outliers không tự động bị loại bỏ. |
| Reviews | ID riêng lẻ và khóa ghép | Báo cáo riêng duplicate theo id và (listing_id, id); không tự động xóa theo id riêng lẻ. Khóa ghép là khóa khảo sát trên nguồn hiện tại. | High | Dòng dư theo id: 4,809; id ở nhiều listing: 2,101; dòng dư theo khóa ghép: 0. |
| All sources | Thời gian, tiền tệ và checksum | Giữ nguyên raw và inventory; báo cáo checksum byte gốc và kết quả chuẩn hóa CRLF thành LF riêng biệt. Nếu vẫn lệch, xác minh lại nguồn. | High | Đơn vị giá: SGD/đêm. Giá là giá mỗi đêm trong báo giá tham chiếu; không phải giá giao dịch hoặc doanh thu thực thu. Reviews có 4,809 dòng dư theo id, 2,101 id xuất hiện ở nhiều listing và 0 dòng dư theo (listing_id, id). Khóa ghép là khóa khảo sát trên nguồn hiện tại, chưa tự chứng minh tính đúng đắn nghiệp vụ cho mọi nguồn. Ngày snapshot trong inventory và khoảng ngày scrape được báo cáo riêng. Checksum khớp sau chuẩn hóa xuống dòng không được gọi là khớp byte gốc. |

## 4. Lưu ý

### NULL
Xem xét ý nghĩa của từng trường trước khi quyết định xử lý.

### Duplicates
Kiểm tra theo grain của từng bảng. Đối với Reviews,
sử dụng cặp listing_id và id.

### Outliers
Đối chiếu các giá trị ngoài ngưỡng IQR với ngữ cảnh nghiệp vụ.

### Referential integrity
Kiểm tra các khóa tham chiếu giữa Listings, Calendar,
Reviews và Neighbourhoods.

### JOIN fan-out
Tổng hợp dữ liệu Calendar và Reviews theo listing_id
trước khi JOIN nếu cần một dòng trên mỗi listing.

### Thời gian, tiền tệ và xuất xứ

Đơn vị giá: SGD/đêm. Giá là giá mỗi đêm trong báo giá tham chiếu; không phải giá giao dịch hoặc doanh thu thực thu. Reviews có 4,809 dòng dư theo id, 2,101 id xuất hiện ở nhiều listing và 0 dòng dư theo (listing_id, id). Khóa ghép là khóa khảo sát trên nguồn hiện tại, chưa tự chứng minh tính đúng đắn nghiệp vụ cho mọi nguồn. Ngày snapshot trong inventory và khoảng ngày scrape được báo cáo riêng. Checksum khớp sau chuẩn hóa xuống dòng không được gọi là khớp byte gốc.

#### Khoảng ngày thực tế

| dataset | field | min_date | max_date | unparseable_non_null |
| --- | --- | --- | --- | --- |
| Listings | last_scraped | 2026-09-25 | 2026-09-26 | 0 |
| Calendar | date | 2026-09-25 | 2027-09-25 | 0 |
| Reviews | date | 2011-05-04 | 2026-09-25 | 0 |

#### Snapshot theo inventory

| file_name | snapshot_date |
| --- | --- |
| listings.csv.gz | 2026-09-23 |
| calendar.csv.gz | 2026-09-23 |
| reviews.csv.gz | 2026-09-23 |
| neighbourhoods.csv | 2026-09-23 |

#### Bằng chứng tiền tệ từ JSON nguồn

| currency | all_listings | listings_with_numeric_price |
| --- | --- | --- |
| MISSING_CURRENCY | 35 | 0 |
| MISSING_JSON | 318 | 0 |
| SGD | 2855 | 2725 |

#### Đối chiếu checksum

| file_name | expected_sha256 | observed_sha256 | sha256_after_crlf_to_lf | result |
| --- | --- | --- | --- | --- |
| listings.csv.gz | 96dcc23048a03631aec9bbeee2f1e39b3bef871fc614e7a573df2e7dd42cb037 | 96dcc23048a03631aec9bbeee2f1e39b3bef871fc614e7a573df2e7dd42cb037 | 7715f32c8dad9e6b6fc54aa24d3d1c631a8da30db79b8ecf3a30234353839460 | EXACT_MATCH |
| calendar.csv.gz | 62635a1ffd91bf87b43c7ec32f4a3059f9341e6eb82bd3ff71cc9592a0b0ece3 | 62635a1ffd91bf87b43c7ec32f4a3059f9341e6eb82bd3ff71cc9592a0b0ece3 | bf5379660adf9d68b197fc5867e5eefb70e8060c037eb4e0271b7923b2d7b0d2 | EXACT_MATCH |
| reviews.csv.gz | a84abeddb76491520626678f979c64c8f8925c881413d0a4043dac457a689ea3 | a84abeddb76491520626678f979c64c8f8925c881413d0a4043dac457a689ea3 | 93a85044dedf48f99951ba8f5f523790a5feebdd78491e3db895ad7f610457e0 | EXACT_MATCH |
| neighbourhoods.csv | b230353c2a7a71b53f6f79fa61b3010754b3b2260a70eff66e3e20df735ce38b | 2a0ca66c76d8b21b08382091f1fa774d9de741103367a8d1accf869c956aa074 | b230353c2a7a71b53f6f79fa61b3010754b3b2260a70eff66e3e20df735ce38b | MATCH_AFTER_CRLF_TO_LF |

NULL được thống kê theo cách đọc mặc định của Pandas, bao gồm các
chuỗi như NA, N/A và None được nhận diện là thiếu. Không tự động
coi đây là lý do xóa bản ghi.

## 5. Kết luận

Các kết quả trong data_quality_baseline.csv là cơ sở
để xác định những trường và quan hệ dữ liệu cần được xem xét
trong bước xử lý tiếp theo.

Tài liệu này chỉ đưa ra khuyến nghị, không thực hiện làm sạch
dữ liệu nguồn.
