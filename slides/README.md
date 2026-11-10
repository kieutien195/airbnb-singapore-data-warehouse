# Phân hệ Slide Thuyết trình ETL/ELT & Kiểm thử Chất lượng Dữ liệu (Task 5.4)

- **Phụ trách:** Thái (Data Engineer / ETL)
- **Tệp trình chiếu chính:** [`5.4_slide_etl_pipeline_and_tests.pptx`](5.4_slide_etl_pipeline_and_tests.pptx)
- **Mã nguồn assets:** [`../scripts/generate_slide_assets.py`](../scripts/generate_slide_assets.py) & [`../scripts/build_etl_slides.py`](../scripts/build_etl_slides.py)
- **Script chạy demo tại chỗ:** [`../scripts/demo_etl_pipeline.py`](../scripts/demo_etl_pipeline.py) hoặc [`../scripts/run_demo.ps1`](../scripts/run_demo.ps1)
- **Snapshot chuẩn:** `2026-09-23` | Inside Airbnb Singapore

---

## 1. Cấu trúc Slide Bàn giao & Ánh xạ với Deck Tổng thể

Bộ slide được thiết kế theo tỷ lệ **16:9 Widescreen**, tuân thủ phong cách giao diện hiện đại (Corporate Navy/Cyan/Emerald Palette), sử dụng biểu đồ trực quan độ phân giải cao (300 DPI), cấu trúc thẻ thông tin (Cards/Badges) súc tích và **tuyệt đối không dán code dài lên slide**.

| Trang PPTX | Mã trang đồ án | Tiêu đề nội dung | Vai trò & Minh chứng kỹ thuật |
| :---: | :---: | :--- | :--- |
| **Slide 1** | **Bìa phân hệ** | **Quy trình ETL/ELT Tích hợp Dữ liệu & Kiểm thử Đa tầng** | Tổng quan vai trò của Thái (Data Engineer), quy mô 1.17M dòng, 100% khớp khóa ngoại, 321 test cases QA pass. |
| **Slide 2** | **Trang 12** | **Luồng Dữ liệu ETL/ELT Toàn trình (End-to-End Pipeline)** | Sơ đồ 5 chặng: Raw (CSV.GZ) $\rightarrow$ Staging $\rightarrow$ Silver $\rightarrow$ Gold (Star Schema) $\rightarrow$ MySQL Warehouse. Làm rõ tính khả lặp (Idempotency TQ-05), chunking 100k dòng và cấm JOIN chéo Calendar $\times$ Reviews. |
| **Slide 3** | **Trang 09** | **Quy tắc Làm sạch & 4 Phép Biến đổi Dữ liệu Cốt lõi** | Ma trận xử lý lỗi: (1) Price & tiền tệ; (2) Date ISO & date_sk; (3) Available 1/0; (4) Khử trùng ID theo grain. Thống kê trước-sau bảo toàn 100% số bản ghi. |
| **Slide 4** | **Trang 10** | **Kiểm định Tiền tệ SGD & Phân giải Giá Niêm yết** | Cơ chế 2 lớp kiểm tra mã tiền từ JSON raw; 2.725 tin SGD hợp lệ (Trung vị: **202.83 SGD**, khớp 100% baseline KPI-02); bảo toàn 483 NULL giá và 134 IQR outliers. |
| **Slide 5** | **Trang 13-18** | **Ánh xạ Star Schema & Kiểm tra Quan hệ Đa bảng (Orphan Keys)** | Kết quả kiểm tra toàn vẹn tham chiếu trên 4 mối quan hệ (REL-01 đến REL-04): **100.0% Match Rate, 0 Orphan Key**. |
| **Slide 6** | **Trang 32 (Phụ lục B)** | **Minh chứng Thực nghiệm, Kiểm thử Tự động & Hướng dẫn Tái lập** | Log chạy thật terminal (toàn trình 42.67s), kết quả 172 test cases QA Pass của Thái, hướng dẫn lệnh demo 1-2 phút phục vụ vấn đáp. |

---

## 2. Kịch bản Thuyết trình 1–2 Phút (Elevator Pitch cho Thái)

Khi đến phần trình bày của Thái trong buổi bảo vệ đồ án, hãy trình bày ngắn gọn, tự tin theo kịch bản sau:

> *"Kính thưa quý Thầy Cô và Hội đồng, em là **Thái**, phụ trách phân hệ **ETL/ELT Pipeline** và **Kiểm thử chất lượng dữ liệu** của dự án.*
>
> *Thách thức lớn nhất của đề tài là dữ liệu nguồn gồm 4 tệp có đơn vị quan sát (grain) hoàn toàn khác nhau, trong đó tệp `calendar.csv.gz` có hơn **1,17 triệu dòng**, tiềm ẩn rủi ro bùng nổ dữ liệu (fan-out) và sai lệch tiền tệ.*
>
> *Để giải quyết triệt để, em đã triển khai pipeline khép kín với 3 điểm nhấn kỹ thuật quan trọng:*
> 1. ***Tính khả lặp tuyệt đối (Idempotency - TQ-05)***: *Khi chạy lại cùng snapshot `2026-09-23`, pipeline tự động xóa sạch partition cũ trước khi nạp mới trong một transaction an toàn, bảo đảm không bao giờ sinh dòng trùng.*
> 2. ***Kiểm định tiền tệ 2 lớp & Bảo toàn dữ liệu nghiệp vụ***: *Em bóc tách chuỗi giá và đối chiếu mã tiền tệ SGD từ trường JSON thô, xác minh được 2.725 tin niêm yết đúng SGD với giá trung vị chuẩn **202.83 SGD** (khớp 100% KPI-02). Đặc biệt, 483 tin thiếu giá được giữ nguyên `NULL` (không gán bừa bằng 0) và 134 ngoại lai IQR được bảo toàn trọn vẹn theo đúng phân phối thực tế.*
> 3. ***Toàn vẹn tham chiếu & Triệt tiêu Fan-Out***: *Kết quả kiểm tra trên cả 4 quan hệ từ Calendar, Reviews đến Listings và dim_date đều đạt **100.0% độ phủ khớp (0 orphan key)**. Đồng thời, thiết kế nghiêm cấm JOIN trực tiếp Calendar với Reviews, giữ vững tính toàn vẹn cho tầng Data Warehouse.*
>
> *Toàn bộ pipeline xử lý 1.17M dòng hoàn tất trong **42 giây**, vượt qua **172/172 bài test QA tự động** và có thể demo tái lập ngay tại chỗ trong 2 giây. Sau đây em xin bàn giao dữ liệu Gold cho bạn Minh tiếp tục phần triển khai MySQL Data Warehouse."*

---

## 3. Hướng dẫn Chạy Demo Trực tiếp (Live Demo Assets)

Nhóm và giảng viên có thể kiểm chứng live pipeline bất kỳ lúc nào:

### 3.1. Chạy Demo Nhanh (Sample Mode - Khuyến nghị khi vấn đáp, ~2 giây):
```bash
# Trong thư mục repo_temp:
.venv\Scripts\python scripts/demo_etl_pipeline.py --sample 500

# Hoặc dùng launcher PowerShell:
.\scripts\run_demo.ps1
```
- **Kết quả hiển thị:** Thực thi tuần tự Ingest $\rightarrow$ Clean $\rightarrow$ Transform trên mẫu 500 dòng/nguồn, in bảng đối soát dữ liệu và tỷ lệ 0 orphan key tức thì.

### 3.2. Chạy Toàn bộ 1.17M Dữ liệu Thật (Full Mode, ~42 giây):
```bash
.venv\Scripts\python scripts/demo_etl_pipeline.py --full
```

### 3.3. Chạy Kiểm thử Hồi quy Tự động (Automated Regression Tests, ~0.65 giây):
```bash
.venv\Scripts\python -m unittest tests/test_etl_regressions.py
```
- Kiểm chứng 5 kịch bản tự động: Idempotency, rollback transaction khi chunk lỗi, khử trùng grain, và chặn xuất Gold khi có orphan key.
