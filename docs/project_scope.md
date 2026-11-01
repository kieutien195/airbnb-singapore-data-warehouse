# PROJECT SCOPE

## 1. Tên đề tài

Tiếng Việt: Xây dựng hệ thống tích hợp và kho dữ liệu phục vụ phân tích thị trường tin đăng Airbnb tại Singapore năm 2026.

Tiếng Anh: Building an Integrated Data Warehouse for Airbnb Listing Market Analytics in Singapore (2026).

Đề tài tập trung xây dựng hệ thống dữ liệu và khai thác thông tin từ một snapshot Inside Airbnb năm 2026, không nghiên cứu toàn bộ giao dịch Airbnb phát sinh trong năm.

## 2. Bối cảnh và vấn đề nghiên cứu

### 2.1. Bối cảnh

Các nền tảng lưu trú trực tuyến như Airbnb công bố nhiều thông tin liên quan đến đặc điểm tin đăng, giá niêm yết, khu vực địa lý, tình trạng sẵn có trên lịch và đánh giá của người dùng.

Inside Airbnb cung cấp các tập dữ liệu công khai phục vụ nghiên cứu, trong đó dữ liệu được tổ chức thành nhiều bảng có mức độ chi tiết khác nhau.

Việc khai thác những thông tin này có thể hỗ trợ phân tích cơ cấu tin đăng, sự khác biệt về giá giữa các nhóm và những đặc điểm đáng chú ý trong dữ liệu thị trường.

Tuy nhiên, các tập dữ liệu riêng lẻ chưa hình thành một hệ thống lưu trữ và phân tích thống nhất.

### 2.2. Vấn đề nghiên cứu

Quá trình sử dụng dữ liệu Inside Airbnb đặt ra các thách thức:

- Dữ liệu phân tán: Listings, Calendar, Reviews và Neighbourhoods được cung cấp riêng biệt, cần xác định quan hệ và tích hợp.

- Không đồng nhất về grain: Listings đại diện cho tin đăng; Calendar cho tin đăng theo ngày; Reviews cho từng đánh giá. Việc JOIN không phù hợp có thể gây nhân bản và sai lệch KPI.

- Chất lượng dữ liệu: Dữ liệu có thể tồn tại giá trị thiếu, sai định dạng, khóa không khớp hoặc giá trị bất thường cần khảo sát và xử lý.

- Thiếu mô hình phân tích thống nhất: Việc tính toán chỉ tiêu từ nhiều bảng rời rạc dễ dẫn đến cách định nghĩa và kết quả không nhất quán.

- Giới hạn dữ liệu: Trạng thái lịch không phản ánh trực tiếp giao dịch đặt phòng, trong khi dữ liệu đánh giá và giá niêm yết chỉ phản ánh một phần đặc điểm thị trường.

### 2.3. Vì sao cần Data Warehouse?

Sử dụng Pandas có thể đáp ứng việc xử lý và phân tích dữ liệu ban đầu. Tuy nhiên, nhóm lựa chọn xây dựng Data Warehouse nhằm:

- Thiết lập cấu trúc dữ liệu thống nhất, có thể tái sử dụng.

- Tổ chức Fact và Dimension theo các quy trình phân tích và grain rõ ràng.

- Chuẩn hóa định nghĩa KPI, hạn chế sai lệch do JOIN nhiều bảng.

- Tách biệt dữ liệu nguồn, dữ liệu đã xử lý và dữ liệu phục vụ phân tích.

- Hỗ trợ truy vấn SQL và kết nối Power BI với nguồn dữ liệu nhất quán.

- Tăng khả năng truy vết, kiểm thử và chạy lại quy trình tích hợp.

Data Warehouse là thành phần kỹ thuật trọng tâm của đồ án, còn Dashboard là phương tiện khai thác và trình bày kết quả.

### 2.4. Phát biểu bài toán

Làm thế nào để thiết kế và triển khai một hệ thống tích hợp các tập dữ liệu Listings, Calendar, Reviews và Neighbourhoods của Inside Airbnb thành kho dữ liệu đa chiều trên MySQL, bảo đảm chất lượng và tính nhất quán của dữ liệu, từ đó hỗ trợ phân tích đặc điểm tin đăng Airbnb tại Singapore theo khu vực, loại phòng, giá niêm yết, tình trạng sẵn có và đánh giá?

## 3. Mục tiêu nghiên cứu

### 3.1. Mục tiêu tổng quát

Thiết kế và triển khai hệ thống tích hợp dữ liệu Inside Airbnb tại Singapore, sử dụng Python và MySQL để xây dựng kho dữ liệu đa chiều, kết hợp SQL và Power BI để phân tích, trực quan hóa và hỗ trợ rút ra các nhận định dựa trên dữ liệu.

### 3.2. Mục tiêu cụ thể

#### MT1 – Khảo sát và đánh giá dữ liệu

- Thu thập bốn tập dữ liệu được lựa chọn.

- Xác định cấu trúc, kiểu dữ liệu, ý nghĩa các trường và quan hệ giữa các bảng.

- Thực hiện EDA và đo lường chất lượng dữ liệu nguồn.

#### MT2 – Thiết kế và triển khai quy trình tích hợp

- Xây dựng pipeline xử lý dữ liệu theo lô bằng Python và SQL.

- Làm sạch, chuẩn hóa, biến đổi và tích hợp dữ liệu.

- Ghi nhận số lượng bản ghi, lỗi xử lý và các bước biến đổi.

- Đảm bảo khả năng chạy lại pipeline mà không sinh bản ghi trùng ngoài dự kiến.

#### MT3 – Thiết kế và xây dựng Data Warehouse

- Áp dụng phương pháp Kimball để xác định các quy trình phân tích, grain, Dimension và Fact.

- Thiết kế mô hình dữ liệu đa chiều phù hợp.

- Triển khai các bảng trên MySQL với khóa và ràng buộc cần thiết.

- Cung cấp dữ liệu nhất quán phục vụ truy vấn phân tích.

#### MT4 – Đánh giá chất lượng dữ liệu sau tích hợp

- Đánh giá tính đầy đủ, hợp lệ, duy nhất và toàn vẹn liên kết.

- So sánh chất lượng dữ liệu trước và sau xử lý.

- Đối chiếu số lượng bản ghi và giải thích chênh lệch.

- Kiểm tra tính chính xác của KPI giữa các lớp xử lý.

#### MT5 – Phân tích và trực quan hóa

- Xây dựng KPI về cơ cấu tin đăng, giá niêm yết, trạng thái lịch và đánh giá.

- Sử dụng SQL để truy vấn dữ liệu từ kho.

- Xây dựng Dashboard Power BI hỗ trợ so sánh theo nhiều chiều.

- Phân tích kết quả và đưa ra khuyến nghị có căn cứ.

## 4. Câu hỏi nghiên cứu

#### RQ1 – Cơ cấu tin đăng

Các tin đăng Airbnb được ghi nhận tại Singapore phân bố như thế nào theo khu vực địa lý và loại phòng?

#### RQ2 – Giá niêm yết

Giá niêm yết trung vị khác biệt như thế nào giữa các khu vực và loại phòng? Những nhóm nào có giá tương đối cao hoặc thấp?

#### RQ3 – Trạng thái sẵn có trên lịch

Tỷ lệ đêm được đánh dấu còn sẵn có khác nhau như thế nào giữa các khu vực và loại phòng trong cùng khoảng thời gian quan sát?

#### RQ4 – Đặc điểm đánh giá

Điểm đánh giá và số lượng đánh giá phân bố như thế nào giữa các nhóm tin đăng? Có những khác biệt mô tả nào đáng chú ý khi phân nhóm theo khu vực hoặc loại phòng?

#### RQ5 – Hiệu quả xử lý và tích hợp dữ liệu

Quy trình tiền xử lý và tích hợp đã cải thiện tính đầy đủ, hợp lệ, duy nhất và nhất quán của dữ liệu như thế nào so với dữ liệu nguồn ban đầu?

#### RQ1–RQ4 tập trung vào giá trị phân tích kinh doanh; RQ5 đánh giá giá trị kỹ thuật của hệ thống.

Nghiên cứu tập trung vào phân tích mô tả và khám phá, không nhằm chứng minh quan hệ nhân quả.

## 5. Phạm vi nghiên cứu

### 5.1. Phạm vi không gian

Singapore, trong giới hạn các tin đăng xuất hiện trong bộ dữ liệu Inside Airbnb.

Kết quả không đại diện cho toàn bộ thị trường lưu trú hoặc bất động sản Singapore.

### 5.2. Phạm vi thời gian

- Snapshot chính dự kiến: 23/09/2026.

- Ngày snapshot và các tệp thực tế phải được xác nhận khi tải tại Task 1.2.

- Listings được phân tích tại thời điểm snapshot.

- Calendar được phân tích theo khoảng ngày thực sự xuất hiện trong file.

- Reviews là dữ liệu đánh giá lịch sử được ghi nhận trong bộ dữ liệu đã tải.

Không mặc định toàn bộ bản ghi trong các bảng đều phát sinh vào năm 2026.

Dự án chỉ sử dụng một snapshot chính để kiểm soát phạm vi triển khai. Việc so sánh nhiều snapshot là hướng mở rộng nếu còn thời gian.

### 5.3. Phạm vi dữ liệu

Nguồn: Inside Airbnb – Singapore.

| Tập dữ liệu | Vai trò |
| --- | --- |
| Listings | Đặc điểm tin đăng, loại phòng, khu vực, giá niêm yết và các thông tin đánh giá |
| Calendar | Dữ liệu listing theo ngày: trạng thái sẵn có và số đêm lưu trú tối thiểu/tối đa; file đã tải không có cột giá |
| Reviews | Các đánh giá lịch sử liên quan đến tin đăng |
| Neighbourhoods | Thông tin phân loại khu vực địa lý |

Các khóa, kiểu cột và điều kiện kết hợp sẽ được xác nhận bằng dữ liệu thực tế, không mặc định tất cả các trường đều đầy đủ.

### 5.4. Phạm vi công nghệ

- Python/Pandas: EDA, xử lý và biến đổi dữ liệu.

- SQL: Truy vấn, kiểm tra và nạp dữ liệu.

- MySQL: Staging và Data Warehouse.

- Kimball Dimensional Modeling: Fact/Dimension và các chiều dùng chung.

- Power BI: Dashboard và trực quan hóa kết quả.

- GitHub: Quản lý mã nguồn, lịch sử thay đổi và cộng tác.

### 5.5. Ngoài phạm vi nghiên cứu

Nhóm không triển khai:

- Hệ thống đặt phòng hoặc ứng dụng web.

- Thu thập dữ liệu bằng scraping trực tiếp từ Airbnb.

- Streaming và xử lý dữ liệu thời gian thực.

- Huấn luyện mô hình dự báo Machine Learning.

- Dự đoán doanh thu, occupancy thực tế hoặc số lượt đặt phòng từ Calendar.

- Xác định tính hợp pháp của từng tin đăng.

- Phân tích nhiều quốc gia.

- Báo cáo Word/PDF độc lập.

## 6. Thiết kế kiến trúc hệ thống dự kiến

### 6.1. Quy trình xử lý

#### Bước 1 – Data Source

Thu thập các file CSV/CSV.GZ từ Inside Airbnb. Giữ bản dữ liệu gốc và thông tin về nguồn, ngày snapshot, thời gian tải.

#### Bước 2 – Raw/Staging Layer

Đọc và nạp dữ liệu nguồn vào khu vực raw/staging. Ghi nhận số bản ghi và thông tin nạp dữ liệu.

#### Bước 3 – Cleaning/Transformation Layer

Sử dụng Python và SQL để xử lý giá trị thiếu, chuẩn hóa kiểu dữ liệu, xác định khóa liên kết, xử lý bản ghi trùng và tạo dữ liệu đạt yêu cầu chất lượng.

#### Bước 4 – Data Warehouse Layer

Tổ chức dữ liệu đã xử lý thành các bảng Fact và Dimension trên MySQL, có kiểm tra tính toàn vẹn và tính nhất quán.

#### Bước 5 – Analytics Layer

Tạo SQL views hoặc các bảng tổng hợp phù hợp với KPI, kết nối Power BI và xây dựng Dashboard.

Cách tổ chức này áp dụng tư duy Bronze – Silver – Gold ở mức logic, không đồng nghĩa nhóm đang xây dựng một Cloud Lakehouse.

### 6.2. Định hướng mô hình dữ liệu

Nhóm sử dụng phương pháp Kimball và xác định grain trước khi tạo bảng.

Các thành phần dự kiến:

Dimension:

- dim_listing: Các thuộc tính mô tả tin đăng.

- dim_neighbourhood: Thông tin khu vực.

- dim_date: Thông tin ngày, tháng, năm.

Fact:

- fact_listing_snapshot: Dữ liệu định lượng ở cấp một listing tại một snapshot.

- fact_calendar: Dữ liệu ở cấp một listing – một ngày lịch – một snapshot.

- fact_review: Dữ liệu đánh giá ở cấp bản ghi review, nếu bộ dữ liệu đủ thông tin để xác định khóa và grain.

Do nhiều Fact có thể sử dụng các Dimension chung, mô hình tổng thể được định hướng là Fact Constellation, trong đó từng Fact có cấu trúc phân tích dạng Star Schema.

Thiết kế cuối cùng phải được xác nhận trong Task 2.5 và 2.6.

## 7. Bộ chỉ số đánh giá

### 7.1. Business KPIs

| KPI | Định nghĩa dự kiến | Dữ liệu |
| --- | --- | --- |
| Total Listings | Số lượng listing_id duy nhất thuộc snapshot được chọn | Listings |
| Median Listed Price | Trung vị giá niêm yết hợp lệ ở cấp listing | Listings |
| Room Type Share | Số listing thuộc một loại phòng / tổng số listing hợp lệ có loại phòng được xác định | Listings |
| Available Night Ratio | Số bản ghi lịch có trạng thái available / số bản ghi lịch có trạng thái hợp lệ trong cùng phạm vi | Calendar |
| Average Review Score | Trung bình điểm review hợp lệ ở cấp listing, nếu có trường điểm phù hợp | Listings |

Quy ước tính toán:

- Mỗi KPI cần có tên, định nghĩa, công thức, đơn vị, nguồn, grain, phạm vi lọc và quy tắc xử lý NULL.

- Median Listed Price sử dụng giá niêm yết từ Listings. Calendar trong bộ dữ liệu đã tải không có cột giá, nên dự án không phân tích giá theo ngày từ Calendar.

- Average Review Score không được suy ra trực tiếp từ số lượng review hoặc nội dung bình luận.

- Không JOIN nhiều Fact ở mức chi tiết rồi tính các KPI chưa được tổng hợp đúng grain.

- Không diễn giải Available Night Ratio thành occupancy rate.

### 7.2. Technical KPIs và Data Quality

| Chỉ số | Phương pháp đánh giá |
| --- | --- |
| Missing Value Rate | Số giá trị thiếu / tổng giá trị thuộc các trường bắt buộc được kiểm tra |
| Duplicate Key Count | Số bản ghi vi phạm tính duy nhất theo khóa và grain |
| Referential Integrity Rate | Số bản ghi có khóa liên kết hợp lệ / tổng bản ghi cần liên kết |
| Valid Record Rate | Số bản ghi đáp ứng các quy tắc chất lượng / tổng bản ghi được kiểm tra |
| Pipeline Re-run Consistency | So sánh số bản ghi và giá trị KPI trước/sau khi chạy lại cùng snapshot |

Các chỉ tiêu được đo tại những lớp phù hợp và so sánh trên cùng phạm vi. Phải ghi nhận bản ghi bị loại để tránh việc tỷ lệ chất lượng tăng lên nhưng dữ liệu hữu ích bị mất đáng kể.

Chưa thiết lập các mục tiêu phần trăm tùy ý khi chưa có kết quả khảo sát dữ liệu thực tế.

## 9. Sản phẩm dự kiến

### 9.1. Sản phẩm kỹ thuật

- Bộ dữ liệu gốc có thông tin xuất xứ.

- EDA Notebook và Data Dictionary.

- Pipeline xử lý và tích hợp Python/SQL.

- Data Warehouse MySQL với mô hình đa chiều.

- Các truy vấn và KPI SQL.

- Kết quả kiểm thử chất lượng dữ liệu.

- Dashboard Power BI.

- Danh sách insight, khuyến nghị và giới hạn nghiên cứu.

### 9.2. Sản phẩm nộp

Slide thuyết trình, dự kiến khoảng 12 slide, thời lượng 10 phút.

Slide trình bày:

- Bài toán và mục tiêu.

- Nguồn dữ liệu và EDA.

- Kiến trúc hệ thống.

- Pipeline tích hợp.

- Mô hình Data Warehouse.

- Kết quả triển khai MySQL.

- Dashboard và các insight.

- Kết luận, giới hạn và hướng phát triển.

Mã nguồn, SQL, Dashboard và dữ liệu được lưu để làm minh chứng hoặc phục vụ demo khi cần.

## 10. Tiêu chí nghiệm thu

### 10.1. Nghiệm thu dữ liệu

- Các nguồn dự kiến đã được khảo sát và ghi nhận xuất xứ.

- Có Data Dictionary và phân tích chất lượng dữ liệu.

- Có thống kê số bản ghi và kết quả xử lý.

- Những trường dữ liệu quan trọng được kiểm tra theo quy tắc đã xác định.

### 10.2. Nghiệm thu hệ thống

- Có pipeline hoàn chỉnh từ dữ liệu nguồn đến MySQL.

- Pipeline có khả năng chạy lại với cùng dữ liệu mà không sinh bản ghi trùng ngoài dự kiến.

- Mô hình Data Warehouse có grain, Fact/Dimension và khóa liên kết rõ ràng.

- Không còn lỗi tính toàn vẹn nghiêm trọng chưa được giải thích.

- Các KPI SQL có thể tính toán và đối chiếu.

### 10.3. Nghiệm thu phân tích

- Có ít nhất năm Business KPIs được định nghĩa và kiểm tra, với các điều chỉnh có giải thích nếu nguồn không đủ dữ liệu.

- Có ít nhất ba nhận định phân tích dựa trên bằng chứng.

- Power BI kết nối được dữ liệu từ MySQL và các biểu đồ hoạt động chính xác.

- Có trình bày giới hạn dữ liệu và cách diễn giải kết quả.

### 10.4. Nghiệm thu thuyết trình

- Slide thể hiện được vấn đề, phương pháp, kỹ thuật, kết quả và đóng góp.

- Có minh chứng thực tế từ pipeline, MySQL và Power BI.

- Nội dung trình bày không vượt quá 10 phút.

- Các thành viên nắm được phần việc của mình và có thể trả lời câu hỏi chuyên môn.

- File slide được nộp đúng yêu cầu và thời hạn.
