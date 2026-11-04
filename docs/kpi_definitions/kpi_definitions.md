# Định nghĩa KPI – Airbnb Singapore (Task 2.2)

## Quy ước chung
- Phạm vi chính là một snapshot Listings; file hiện tại có scrape_id `20260923225116`, trong khi last_scraped quan sát từ `2026-09-25` đến `2026-09-26`.
- Grain: Listings = listing/snapshot; Calendar = listing/ngày/snapshot; Reviews = một review; Neighbourhoods = một khu vực.
- KPI cấp listing tính từ Listings trước khi nối với Calendar/Reviews để tránh nhân bản.
- Tập rỗng hoặc mẫu số bằng 0: trả NULL/không xác định, không trả 0%. NULL không được tự động thay bằng 0.
- Giữ độ chính xác gốc khi đối chiếu; chỉ làm tròn khi trình bày: tỷ lệ 2 chữ số thập phân, giá/điểm 2 chữ số thập phân, số đếm là số nguyên.
- KPI-04 so sánh các nhóm trên cùng cửa sổ ngày Calendar hiện tại: `2026-09-25` đến `2027-09-25` (366 ngày).
- Currency: `price_quote_raw.quote.currency` quan sát là SGD ở 2.855 bản ghi; 35 bản ghi không có currency trong JSON nên không được mặc định SGD.
- Miền điểm review_scores_rating quan sát trong snapshot là 1–5; cần đối chiếu metadata phiên bản nguồn khi chốt ETL.
- Snapshot chính theo source_inventory.csv: `2026-09-23`. Đây là metadata của nguồn, không phải cột có sẵn trong các file RAW.

## KPI-01 – Số listing duy nhất theo snapshot

**Định nghĩa:** Số lượng mã listing phân biệt được ghi nhận trong một file Listings thuộc snapshot được chọn.

**Nguồn:** Listings.id; Listings.scrape_id; Listings.last_scraped

**Công thức:** COUNT(DISTINCT id)

**Bộ lọc:** Chỉ dùng một snapshot; loại id NULL; xác nhận snapshot theo scrape_id và metadata nguồn. Với file hiện tại, scrape_id = 20260923225116; last_scraped quan sát từ 2026-09-25 đến 2026-09-26.

**Tử số:** Số mã listing duy nhất hợp lệ.

**Mẫu số:** Không áp dụng.

**Đơn vị:** Listing

**Grain:** Một listing tại snapshot

**Diễn giải:** Quy mô tin đăng được ghi nhận tại snapshot, không phải số listing còn available trong một ngày.

**Lưu ý:** Không đếm dòng Calendar/Reviews; không gộp nhiều snapshot nếu chưa có quy tắc chọn snapshot.

## KPI-02 – Trung vị giá niêm yết mỗi đêm

**Định nghĩa:** Trung vị giá niêm yết mỗi đêm của các listing có giá hợp lệ và xác định được tiền tệ SGD tại snapshot.

**Nguồn:** Listings.id; Listings.price; Listings.price_quote_raw; Listings.price_quote_price_per_night

**Công thức:** MEDIAN(price_clean), mỗi listing một lần; price_clean chỉ nhận khi quote.currency = 'SGD'.

**Bộ lọc:** Một snapshot; price không NULL, parse được, hữu hạn và > 0; trích currency từ quote.currency trong price_quote_raw; loại bản ghi không xác định được currency; đối chiếu price với price_quote_price_per_night.

**Tử số:** Không áp dụng cho median.

**Mẫu số:** Không áp dụng; báo cáo coverage = listing có giá SGD hợp lệ / tổng listing snapshot.

**Đơn vị:** SGD/đêm

**Grain:** Một listing tại snapshot

**Diễn giải:** Một nửa listing có giá hợp lệ có giá không lớn hơn median và một nửa không nhỏ hơn median.

**Lưu ý:** Trong dữ liệu hiện tại có 2.855 báo giá ghi rõ currency=SGD; 35 báo giá không có currency trong JSON. Không suy luận SGD chỉ từ ký hiệu '$'. Giá niêm yết/báo giá không phải giá giao dịch hay doanh thu.

## KPI-03 – Tỷ trọng loại phòng

**Định nghĩa:** Tỷ lệ listing thuộc từng room_type trên tổng listing có room_type hợp lệ trong cùng snapshot và phạm vi lọc.

**Nguồn:** Listings.id; Listings.room_type; Listings.neighbourhood_cleansed

**Công thức:** Số listing duy nhất thuộc room_type X / tổng listing duy nhất có room_type hợp lệ × 100%.

**Bộ lọc:** Giữ bộ lọc snapshot và khu vực; khi tính tỷ trọng trong khu vực, bỏ riêng bộ lọc room_type ở mẫu số; chỉ nhận room_type không NULL/rỗng và mỗi id một lần.

**Tử số:** Số listing duy nhất thuộc room_type X trong phạm vi đang xét.

**Mẫu số:** Tổng listing duy nhất có room_type hợp lệ trong cùng phạm vi snapshot/khu vực; không áp bộ lọc room_type vào mẫu số.

**Đơn vị:** % listing

**Grain:** Một listing tại snapshot

**Diễn giải:** Mô tả cơ cấu loại phòng trong tổng tin đăng có phân loại của phạm vi đang xét.

**Lưu ý:** Không dùng số dòng Calendar/Reviews làm mẫu số. Nếu một id có nhiều room_type xung đột, đưa vào kiểm tra thay vì tự chọn.

## KPI-04 – Tỷ lệ bản ghi lịch còn available

**Định nghĩa:** Tỷ lệ bản ghi listing-ngày có trạng thái available trong tổng bản ghi listing-ngày có trạng thái hợp lệ.

**Nguồn:** Calendar.listing_id; Calendar.date; Calendar.available

**Công thức:** SUM(CASE WHEN available = TRUE THEN 1 ELSE 0 END) / SUM(CASE WHEN available IN (TRUE,FALSE) THEN 1 ELSE 0 END) × 100%. Tử số là số dòng thỏa điều kiện, không viết COUNT(điều kiện).

**Bộ lọc:** listing_id và date hợp lệ; available chuẩn hóa thành TRUE/FALSE; kiểm tra và xử lý duplicate theo (listing_id,date) trong file RAW hiện tại vì chỉ có một snapshot; khi tích hợp nhiều snapshot trong Warehouse, grain gồm thêm snapshot_date; so sánh các khu vực và room_type trên cùng cửa sổ ngày 2026-09-25 đến 2027-09-25.

**Tử số:** Số dòng listing-ngày hợp lệ có available = TRUE.

**Mẫu số:** Số dòng listing-ngày hợp lệ có available = TRUE hoặc FALSE trong cùng cửa sổ ngày.

**Đơn vị:** % bản ghi listing-ngày

**Grain:** Một listing tại một ngày lịch và một snapshot

**Diễn giải:** Tỷ lệ trạng thái lịch được đánh dấu còn khả dụng trong cùng khoảng thời gian quan sát.

**Lưu ý:** FALSE chỉ là không khả dụng, không chứng minh đã có booking. Không gọi là occupancy rate. Chỉ so sánh nhóm trên cùng cửa sổ ngày; loại trùng theo grain trước khi tính.

## KPI-05 – Điểm review tổng thể trung bình

**Định nghĩa:** Điểm review tổng thể trung bình giữa các listing có review_scores_rating hợp lệ tại snapshot; mỗi listing có trọng số bằng nhau.

**Nguồn:** Listings.id; Listings.review_scores_rating

**Công thức:** AVG(review_scores_rating) trên mỗi listing duy nhất có điểm hợp lệ.

**Bộ lọc:** Một snapshot; điểm là số hữu hạn trong miền 1–5; loại NULL; mỗi listing tính một lần.

**Tử số:** Tổng điểm review tổng thể của các listing có điểm hợp lệ.

**Mẫu số:** Số listing duy nhất có điểm review tổng thể hợp lệ.

**Đơn vị:** Điểm (thang quan sát 1–5)

**Grain:** Một listing tại snapshot

**Diễn giải:** Điểm tổng thể trung bình giữa các listing có điểm, không phải trung bình của từng review trong Reviews.

**Lưu ý:** Dữ liệu snapshot hiện tại quan sát được miền 1–5; xác nhận lại với metadata của phiên bản nguồn. Không thay NULL bằng 0; công bố coverage.

## SUP-01 – Trung vị số review trên mỗi listing

**Định nghĩa:** Trung vị số review được ghi nhận trên mỗi listing tại snapshot.

**Nguồn:** Listings.id; Listings.number_of_reviews

**Công thức:** MEDIAN(number_of_reviews), mỗi listing một lần.

**Bộ lọc:** Một snapshot; number_of_reviews là số hợp lệ và không âm; giữ giá trị 0; không thay NULL bằng 0.

**Tử số:** Không áp dụng.

**Mẫu số:** Không áp dụng.

**Đơn vị:** Review/listing

**Grain:** Một listing tại snapshot

**Diễn giải:** Mức số lượng review điển hình của listing trong nhóm đang phân tích.

**Lưu ý:** Không thay NULL bằng 0; không mặc định số dòng Reviews luôn bằng number_of_reviews nếu chưa đối chiếu cùng snapshot/phạm vi.

## SUP-02 – Số bản ghi review trong kỳ

**Định nghĩa:** Số bản ghi review hợp lệ được ghi nhận trong khoảng ngày được chọn.

**Nguồn:** Reviews.listing_id; Reviews.id; Reviews.date

**Công thức:** Đếm bản ghi theo khóa (listing_id, id) sau kiểm tra trùng; lọc date trong khoảng chọn.

**Bộ lọc:** Ngày review hợp lệ và nằm trong kỳ; listing_id hợp lệ; kiểm tra trùng khóa ghép (listing_id,id); không đếm DISTINCT id riêng nếu id có thể trùng giữa listing.

**Tử số:** Số bản ghi review hợp lệ trong kỳ.

**Mẫu số:** Không áp dụng.

**Đơn vị:** Bản ghi review

**Grain:** Một bản ghi review

**Diễn giải:** Lượng review quan sát được trong kỳ, có thể phân tích theo thời gian/khu vực/loại phòng sau khi liên kết listing đúng grain.

**Lưu ý:** Không suy ra số booking; không coi review date là ngày đặt phòng; Reviews.id hiện có trùng lặp nên dùng khóa ghép sau khi kiểm tra.

## Technical KPI / Data Quality

Các chỉ tiêu dưới đây phải được đo ở các lớp raw/staging/Silver/Gold và lưu kết quả kiểm thử. TQ-05 chỉ xác nhận được sau khi chạy pipeline ít nhất hai lần với cùng đầu vào.

### TQ-01 – Tỷ lệ thiếu dữ liệu (Missing Value Rate)

**Định nghĩa:** Tỷ lệ ô NULL/thiếu trên tổng số ô thuộc danh sách trường bắt buộc được kiểm tra.

**Công thức:** Tổng số ô NULL ở các trường bắt buộc / tổng số ô được kiểm tra × 100%.

**Phạm vi:** Báo cáo theo từng trường và tổng hợp theo nguồn/lớp dữ liệu; danh sách trường bắt buộc phải được nhóm chốt trước.

**Đơn vị:** %

**Grain:** Một trường dữ liệu trong một nguồn/lớp và snapshot

**Diễn giải:** Tỷ lệ càng thấp cho thấy mức độ đầy đủ càng cao; phải xem cùng số dòng và mức độ quan trọng của trường.

**Lưu ý:** Không gộp mọi cột tùy ý; phân biệt NULL hợp lệ (ví dụ comments có thể thiếu) với NULL ở trường bắt buộc.

### TQ-02 – Số bản ghi trùng khóa (Duplicate Key Count)

**Định nghĩa:** Số bản ghi vượt quá một bản ghi duy nhất theo khóa và grain đã xác định.

**Công thức:** COUNT(rows) - COUNT(DISTINCT business_key) hoặc số dòng bị đánh dấu duplicate theo khóa/grain.

**Phạm vi:** Kiểm tra RAW hiện tại (một snapshot): Listings dùng id; Calendar dùng (listing_id,date); Reviews dùng (listing_id,id) sau xác minh; Neighbourhoods dùng khóa ghép (neighbourhood_group,neighbourhood). Khi tích hợp nhiều snapshot trong Warehouse, Calendar sử dụng (listing_id,date,snapshot_date).

**Đơn vị:** Bản ghi trùng

**Grain:** Theo khóa/grain của từng nguồn/lớp

**Diễn giải:** Giá trị 0 nghĩa là không phát hiện bản ghi trùng theo khóa kiểm tra.

**Lưu ý:** Không mặc định Reviews.id riêng là duy nhất; phải nêu rõ khóa và quy tắc giữ/xử lý bản ghi trùng.

### TQ-03 – Tỷ lệ toàn vẹn tham chiếu (Referential Integrity Rate)

**Định nghĩa:** Tỷ lệ bản ghi con có khóa tham chiếu tồn tại trong bảng cha tương ứng.

**Công thức:** Số bản ghi con có khóa cha hợp lệ / tổng bản ghi con có khóa cần liên kết × 100%.

**Phạm vi:** Calendar.listing_id và Reviews.listing_id tham chiếu Listings.id; Listings sử dụng cặp (neighbourhood_group_cleansed, neighbourhood_cleansed) để tham chiếu cặp (neighbourhood_group, neighbourhood) trong Neighbourhoods.

**Đơn vị:** %

**Grain:** Bản ghi cần liên kết của từng quan hệ

**Diễn giải:** Tỷ lệ càng cao cho thấy liên kết giữa các nguồn càng đầy đủ.

**Lưu ý:** Báo cáo riêng số khóa NULL và số khóa mồ côi; không gộp hai loại thành cùng một lỗi.

### TQ-04 – Tỷ lệ bản ghi hợp lệ (Valid Record Rate)

**Định nghĩa:** Tỷ lệ bản ghi đáp ứng toàn bộ quy tắc chất lượng bắt buộc đã được phê duyệt.

**Công thức:** Số bản ghi đạt tất cả kiểm tra bắt buộc / tổng số bản ghi được kiểm tra × 100%.

**Phạm vi:** Kiểm tra kiểu dữ liệu, miền giá trị, trường bắt buộc, khóa/grain, ngày và quy tắc nghiệp vụ tại từng lớp raw/staging/Silver/Gold.

**Đơn vị:** %

**Grain:** Một bản ghi tại từng nguồn/lớp

**Diễn giải:** Đo tỷ lệ dữ liệu đáp ứng tiêu chí sử dụng sau kiểm tra.

**Lưu ý:** Công bố rõ rule và số dòng bị loại/sửa; không làm tỷ lệ tăng giả tạo bằng cách âm thầm xóa bản ghi.

### TQ-05 – Tính nhất quán khi chạy lại pipeline (Pipeline Re-run Consistency)

**Định nghĩa:** Mức độ giống nhau của số lượng bản ghi và KPI đầu ra khi chạy lại pipeline với cùng dữ liệu nguồn, cấu hình và snapshot.

**Công thức:** So sánh row count và KPI sau lần chạy lại với lần chạy chuẩn; PASS khi các giá trị bằng nhau trong sai số/độ chính xác đã quy định và không phát sinh bản ghi trùng.

**Phạm vi:** Thực hiện tối thiểu hai lần chạy cùng snapshot; đối chiếu raw→staging→Silver→Gold, log và kết quả KPI.

**Đơn vị:** PASS/FAIL và chênh lệch bản ghi/KPI

**Grain:** Một lần chạy pipeline cho một snapshot

**Diễn giải:** PASS chứng minh pipeline có thể tái hiện kết quả với cùng đầu vào.

**Lưu ý:** Không thể tính từ file raw đơn lẻ; phải chạy pipeline ETL thực tế ít nhất hai lần và lưu log/đối chiếu.
