
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
| Listings | NULL: price | Không điền 0 thay cho dữ liệu thiếu; ghi rõ mẫu số có dữ liệu khi phân tích. | High | 480/3,208 bản ghi (14.9626%). Số lượng giá trị NULL tại trường dữ liệu. |
| Listings | NULL: review_scores_rating | Không điền 0 thay cho dữ liệu thiếu; ghi rõ mẫu số có dữ liệu khi phân tích. | High | 1,369/3,208 bản ghi (42.6746%). Số lượng giá trị NULL tại trường dữ liệu. |
| Listings | Outliers: price | Giữ nguyên để xem xét theo ngữ cảnh; không tự động xóa. | Medium | 134/2,725 bản ghi (4.9174%). Q1=99.9000; Median=202.8300; Q3=333.3100; IQR=233.4100; lower=-250.2150; upper=683.4250. Outliers không tự động bị loại bỏ. |
| Reviews | ID riêng lẻ và khóa ghép | Báo cáo riêng duplicate theo id và (listing_id, id); không tự động xóa theo id riêng lẻ. Khóa ghép là khóa khảo sát trên nguồn hiện tại. | High | Dòng dư theo id: 4,809; id ở nhiều listing: 2,101; dòng dư theo khóa ghép: 0. |
| All sources | Thời gian, tiền tệ và checksum | Giữ nguyên raw và inventory; báo cáo checksum byte gốc và kết quả chuẩn hóa CRLF thành LF riêng biệt. Nếu vẫn lệch, xác minh lại nguồn. | High | Đơn vị giá: SGD/đêm. Giá chính là Listings.price, hữu hạn, >0 và SGD xác nhận từ JSON; không phải giá giao dịch hoặc doanh thu thực thu. Reviews có 4,809 dòng dư theo id, 2,101 id xuất hiện ở nhiều listing và 0 dòng dư theo (listing_id, id). Khóa ghép là khóa khảo sát trên nguồn hiện tại, chưa tự chứng minh tính đúng đắn nghiệp vụ cho mọi nguồn. Ngày snapshot trong inventory và khoảng ngày scrape được báo cáo riêng. Checksum khớp sau chuẩn hóa xuống dòng không được gọi là khớp byte gốc. |
| Listings - Reviews | Review count reconciliation | Giữ hai chỉ tiêu riêng; xác minh phạm vi nguồn nếu lệch, không ghi đè số đếm. | High | 3,208/3,208 listing khớp; 0 lệch; 0 thiếu/sai số review ở Listings. File có 46,000 dòng khóa/ngày hợp lệ và 46,000 khóa (listing_id,id) phân biệt. Đối chiếu toàn bộ ngày review trong file với một snapshot Listings; không lọc theo năm. 0 ở observed_review_records nghĩa là không tìm thấy trong file; NULL từ Listings giữ NULL. Chênh lệch chưa chứng minh nguồn nào sai; cần xác minh phạm vi/lịch sử cập nhật từ nguồn, không ép bằng nhau. |
| Listings | Rating domain | Dùng 1–5 thống nhất với KPI; NULL không điền 0. | Medium | Đây là miền quan sát snapshot, chưa có xác minh metadata chính thức. |
| Listings | Price sample | KPI và EDA dùng price >0, hữu hạn, currency SGD từ JSON; quote là đối chiếu trên cùng tập listing. | High | {'matched_listing_count': 2725.0, 'listed_median_same_sample_sgd': 202.83, 'quote_median_same_sample_sgd': 202.83, 'price_difference_over_0_005_sgd': 0.0, 'max_abs_difference_sgd': 0.0} |

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

Đơn vị giá: SGD/đêm. Giá chính là Listings.price, hữu hạn, >0 và SGD xác nhận từ JSON; không phải giá giao dịch hoặc doanh thu thực thu. Reviews có 4,809 dòng dư theo id, 2,101 id xuất hiện ở nhiều listing và 0 dòng dư theo (listing_id, id). Khóa ghép là khóa khảo sát trên nguồn hiện tại, chưa tự chứng minh tính đúng đắn nghiệp vụ cho mọi nguồn. Ngày snapshot trong inventory và khoảng ngày scrape được báo cáo riêng. Checksum khớp sau chuẩn hóa xuống dòng không được gọi là khớp byte gốc.

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

| currency | all_listings | listings_with_numeric_listed_price | listings_with_valid_sgd_listed_price |
| --- | --- | --- | --- |
| MISSING_CURRENCY | 35 | 3 | 0 |
| MISSING_JSON | 318 | 0 | 0 |
| SGD | 2855 | 2725 | 2725 |

#### Đối chiếu checksum

| file_name | expected_sha256 | observed_sha256 | sha256_after_crlf_to_lf | result |
| --- | --- | --- | --- | --- |
| listings.csv.gz | 96dcc23048a03631aec9bbeee2f1e39b3bef871fc614e7a573df2e7dd42cb037 | 96dcc23048a03631aec9bbeee2f1e39b3bef871fc614e7a573df2e7dd42cb037 | None | EXACT_MATCH |
| calendar.csv.gz | 62635a1ffd91bf87b43c7ec32f4a3059f9341e6eb82bd3ff71cc9592a0b0ece3 | 62635a1ffd91bf87b43c7ec32f4a3059f9341e6eb82bd3ff71cc9592a0b0ece3 | None | EXACT_MATCH |
| reviews.csv.gz | a84abeddb76491520626678f979c64c8f8925c881413d0a4043dac457a689ea3 | a84abeddb76491520626678f979c64c8f8925c881413d0a4043dac457a689ea3 | None | EXACT_MATCH |
| neighbourhoods.csv | b230353c2a7a71b53f6f79fa61b3010754b3b2260a70eff66e3e20df735ce38b | 2a0ca66c76d8b21b08382091f1fa774d9de741103367a8d1accf869c956aa074 | b230353c2a7a71b53f6f79fa61b3010754b3b2260a70eff66e3e20df735ce38b | MATCH_AFTER_CRLF_TO_LF |

NULL được thống kê theo cách đọc mặc định của Pandas, bao gồm các
chuỗi như NA, N/A và None được nhận diện là thiếu. Không tự động
coi đây là lý do xóa bản ghi.

## 5. Bằng chứng bổ sung

### Giá niêm yết và quote trên cùng mẫu

| matched_listing_count | listed_median_same_sample_sgd | quote_median_same_sample_sgd | price_difference_over_0_005_sgd | max_abs_difference_sgd |
| --- | --- | --- | --- | --- |
| 2725.0 | 202.83 | 202.83 | 0.0 | 0.0 |

### Số lượng review

3,208/3,208 listing khớp; 0 lệch; 0 thiếu/sai số review ở Listings. File có 46,000 dòng khóa/ngày hợp lệ và 46,000 khóa (listing_id,id) phân biệt. Đối chiếu toàn bộ ngày review trong file với một snapshot Listings; không lọc theo năm. 0 ở observed_review_records nghĩa là không tìm thấy trong file; NULL từ Listings giữ NULL. Chênh lệch chưa chứng minh nguồn nào sai; cần xác minh phạm vi/lịch sử cập nhật từ nguồn, không ép bằng nhau.

| listing_count | matched_listings | different_listings | missing_or_invalid_listings_count | valid_review_rows | unique_review_keys | review_records_linked_to_listings | review_records_not_linked_to_listings | scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3208 | 3208 | 0 | 0 | 46000 | 46000 | 46000 | 0 | All valid review dates in supplied file; one Listings snapshot |

Bảng đầy đủ: `tests/review_reconciliation.csv` và `docs/eda/review_group_summary.csv`.

| group_dimension | group_value | listing_count | listings_with_valid_review_count | median_listing_review_count | total_observed_review_records |
| --- | --- | --- | --- | --- | --- |
| neighbourhood_cleansed | Ang Mo Kio | 16 | 16 | 0.0 | 97 |
| neighbourhood_cleansed | Bedok | 134 | 134 | 1.0 | 1690 |
| neighbourhood_cleansed | Bishan | 16 | 16 | 0.0 | 23 |
| neighbourhood_cleansed | Bukit Batok | 18 | 18 | 0.5 | 99 |
| neighbourhood_cleansed | Bukit Merah | 177 | 177 | 1.0 | 2106 |
| neighbourhood_cleansed | Bukit Panjang | 14 | 14 | 0.0 | 9 |
| neighbourhood_cleansed | Bukit Timah | 38 | 38 | 1.0 | 326 |
| neighbourhood_cleansed | Central Water Catchment | 3 | 3 | 1.0 | 3 |
| neighbourhood_cleansed | Changi | 2 | 2 | 0.0 | 0 |
| neighbourhood_cleansed | Choa Chu Kang | 18 | 18 | 1.0 | 67 |
| neighbourhood_cleansed | Clementi | 65 | 65 | 0.0 | 140 |
| neighbourhood_cleansed | Downtown Core | 178 | 178 | 1.0 | 2808 |
| neighbourhood_cleansed | Geylang | 178 | 178 | 2.0 | 4258 |
| neighbourhood_cleansed | Hougang | 43 | 43 | 1.0 | 156 |
| neighbourhood_cleansed | Jurong East | 29 | 29 | 0.0 | 81 |
| neighbourhood_cleansed | Jurong West | 37 | 37 | 1.0 | 218 |
| neighbourhood_cleansed | Kallang | 269 | 269 | 2.0 | 5658 |
| neighbourhood_cleansed | Marina South | 4 | 4 | 40.5 | 199 |
| neighbourhood_cleansed | Marine Parade | 89 | 89 | 1.0 | 1020 |
| neighbourhood_cleansed | Museum | 22 | 22 | 0.0 | 67 |
| neighbourhood_cleansed | Newton | 52 | 52 | 0.0 | 657 |
| neighbourhood_cleansed | Novena | 198 | 198 | 1.0 | 1751 |
| neighbourhood_cleansed | Orchard | 90 | 90 | 0.0 | 380 |
| neighbourhood_cleansed | Outram | 257 | 257 | 2.0 | 8359 |
| neighbourhood_cleansed | Pasir Ris | 30 | 30 | 1.0 | 205 |
| neighbourhood_cleansed | Punggol | 12 | 12 | 0.0 | 94 |
| neighbourhood_cleansed | Queenstown | 155 | 155 | 0.0 | 1117 |
| neighbourhood_cleansed | River Valley | 456 | 456 | 1.0 | 1989 |
| neighbourhood_cleansed | Rochor | 281 | 281 | 2.0 | 6852 |
| neighbourhood_cleansed | Sembawang | 9 | 9 | 1.0 | 25 |
| neighbourhood_cleansed | Sengkang | 7 | 7 | 5.0 | 36 |
| neighbourhood_cleansed | Serangoon | 30 | 30 | 0.0 | 437 |
| neighbourhood_cleansed | Singapore River | 151 | 151 | 3.0 | 3033 |
| neighbourhood_cleansed | Southern Islands | 21 | 21 | 3.0 | 84 |
| neighbourhood_cleansed | Sungei Kadut | 1 | 1 | 1.0 | 1 |
| neighbourhood_cleansed | Tampines | 25 | 25 | 4.0 | 1443 |
| neighbourhood_cleansed | Tanglin | 33 | 33 | 1.0 | 335 |
| neighbourhood_cleansed | Toa Payoh | 14 | 14 | 0.0 | 20 |
| neighbourhood_cleansed | Tuas | 2 | 2 | 2.5 | 5 |
| neighbourhood_cleansed | Western Water Catchment | 2 | 2 | 0.0 | 0 |
| neighbourhood_cleansed | Woodlands | 19 | 19 | 1.0 | 120 |
| neighbourhood_cleansed | Yishun | 13 | 13 | 1.0 | 32 |
| room_type | Entire home/apt | 1232 | 1232 | 0.0 | 12159 |
| room_type | Hotel room | 83 | 83 | 12.0 | 2324 |
| room_type | Private room | 1827 | 1827 | 1.0 | 29282 |
| room_type | Shared room | 66 | 66 | 7.5 | 2235 |

### Rating

Miền 1–5 là miền quan sát và quy tắc thống nhất với KPI, chưa xác minh metadata chính thức.

## 6. Kết luận

Các kết quả trong data_quality_baseline.csv là cơ sở
để xác định những trường và quan hệ dữ liệu cần được xem xét
trong bước xử lý tiếp theo.

Tài liệu này chỉ đưa ra khuyến nghị, không thực hiện làm sạch
dữ liệu nguồn.
