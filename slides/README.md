# Phân hệ Slide Thuyết trình ETL/ELT & Kiểm thử Chất lượng Dữ liệu (Task 5.4)

- **Thành viên phụ trách:** Thái (Data Engineer / ETL)
- **Tệp trình chiếu chuẩn Outline (4 Trang: 09, 10, 12, 32):** [`thai_slides_09_10_12_32.pptx`](thai_slides_09_10_12_32.pptx) & [`5.4_slide_etl_pipeline_and_tests.pptx`](5.4_slide_etl_pipeline_and_tests.pptx)
- **Tệp trình chiếu rút gọn (2 Trang tổng hợp cao độ):** [`5.4_slide_etl_summary_2slides.pptx`](5.4_slide_etl_summary_2slides.pptx)
- **Mã nguồn sinh slide tự động:** [`../scripts/build_thai_slides_outline.py`](../scripts/build_thai_slides_outline.py) & [`../scripts/build_2_slides_summary.py`](../scripts/build_2_slides_summary.py)
- **Script chạy demo tại chỗ:** [`../scripts/demo_etl_pipeline.py`](../scripts/demo_etl_pipeline.py) hoặc [`../scripts/run_demo.ps1`](../scripts/run_demo.ps1)
- **Snapshot chuẩn:** `2026-09-23` | Inside Airbnb Singapore

---

## 1. Cấu trúc 4 Trang Slide của Thái theo Đúng Slide Outline Dự án

Tuân thủ nghiêm ngặt quy tắc trình bày của nhóm:
1. **Đặt kết luận ngay ở tiêu đề**, dùng số lớn hoặc ma trận đối soát giải thích câu hỏi.
2. **Hình / Bảng đọc được làm bằng chứng**, tuyệt đối không dán code dài lên slide.
3. **Dải điều hướng dùng chung** (Breadcrumb) và **dòng chân trang chuẩn** (nguồn, snapshot, commit, số trang).
4. **Kiểm soát tọa độ và padding chặt chẽ**, bảo đảm **100% không bị đè chữ / không tràn khung** trên mọi màn hình chiếu.

| Trang Outline | Tiêu đề Kết luận trên Slide | Bố cục & Bằng chứng Kỹ thuật |
| :---: | :--- | :--- |
| **Trang 09**<br>*(B. Dữ liệu & tiền xử lý)* | **BẢO TOÀN 100% FACT: KHÔNG LOẠI BẢN GHI NGOÀI Ý MUỐN, CHUẨN HÓA 4 NHÓM QUY TẮC** | • Bảng ma trận đối soát: Vấn đề $\rightarrow$ Quy tắc $\rightarrow$ Đầu ra $\rightarrow$ Số dòng tác động $\rightarrow$ Số dòng bị loại.<br>• Thống kê 3.208 listings, 1.17M calendar, 46k reviews sạch.<br>• Ghi rõ: Giữ nguyên 483 NULL giá và 134 IQR outliers. |
| **Trang 10**<br>*(B. Dữ liệu & tiền xử lý)* | **KIỂM ĐỊNH 2 LỚP XÁC MINH 2.725 GIÁ SGD HỢP LỆ; TRUNG VỊ ĐẠT CHUẨN 202,83 SGD** | • Sơ đồ 2 lớp kiểm định: Bóc tách chuỗi giá + Đối chiếu mã tiền SGD từ JSON raw.<br>• Đối chiếu 2 ví dụ cụ thể: Ví dụ ĐẠT (ID 71609 - $150) vs Ví dụ LOẠI (ID 27534720 - NULL).<br>• Khớp chuẩn 100% baseline KPI-02 (202.83 SGD) và sửa lỗi accommodates kiểu INT. |
| **Trang 12**<br>*(D. Triển khai & kiểm chứng)* | **MỘT LẦN CHẠY ETL TẠO ĐẦU RA TRUY VẾT 100%, HOÀN TẤT TOÀN BỘ 3 TẦNG TRONG 42,67 GIÂY** | • Bảng truy vết Stage $\rightarrow$ Script $\rightarrow$ Input $\rightarrow$ Output $\rightarrow$ Log.<br>• Trích xuất log chạy thật terminal với timestamp và snapshot 2026-09-23.<br>• Vận dụng lý thuyết Chương 3 (Idempotency TQ-05) và Chương 4 (Vector hóa & chặn Fan-out). |
| **Trang 32**<br>*(F. Phụ lục & trang cuối)* | **PHỤ LỤC B: MÔI TRƯỜNG TÁI LẬP ĐỘC LẬP & BỘ TEST TỰ ĐỘNG ĐẠT 172/172 PASS** | • Thông số môi trường: Python 3.12, virtualenv, Git branch, bảo mật credentials qua .env.<br>• Bộ test tự động: 172/172 QA checks PASS, 5/5 regression tests OK, 0 orphan key.<br>• Hướng dẫn lệnh chạy live demo 2 giây phục vụ giảng viên vấn đáp tại chỗ. |

---

## 2. Kịch bản Thuyết trình 1–2 Phút (Elevator Pitch cho Thái)

Khi trình bày 4 slide này trước hội đồng, Thái nói tự tin theo mạch:

> *"Kính thưa quý Thầy Cô và Hội đồng, em là **Thái**, phụ trách phân hệ **ETL/ELT Pipeline** và **Kiểm thử chất lượng dữ liệu** (Trang 09, 10, 12 và Phụ lục 32).*
>
> *(Trang 09) Ở tầng tiền xử lý, nhóm em áp dụng nguyên tắc **bảo toàn 100% dữ liệu nghiệp vụ**. Toàn bộ 1,17 triệu dòng được chuẩn hóa theo 4 quy tắc mà **không có bản ghi nào bị loại bỏ ngoài ý muốn**. Các giá trị thiếu như 483 giá NULL hay 1.369 rating NULL đều được giữ nguyên NULL để tránh bóp méo phân phối.*
>
> *(Trang 10) Đặc biệt với giá niêm yết, em xây dựng **cơ chế kiểm định 2 lớp**: vừa bóc tách chuỗi số, vừa đối chiếu mã tiền tệ từ trường JSON thô, qua đó xác minh chuẩn xác **2.725 tin niêm yết đúng SGD** với trung vị **202,83 SGD** khớp tuyệt đối 100% với baseline KPI-02. Đồng thời 134 ngoại lai IQR được bảo toàn trọn vẹn vì phản ánh đúng phân khúc biệt thự/penthouse cao cấp.*
>
> *(Trang 12) Toàn bộ luồng ETL từ Ingest, Clean đến Transform được tự động hóa, hoàn tất xử lý 1,17 triệu dòng chỉ trong **42,67 giây**. Quy trình bảo đảm tính **khả lặp (Idempotency TQ-05)** nhờ xóa partition cũ theo snapshot trong một transaction an toàn, và triệt tiêu hoàn toàn rủi ro fan-out.*
>
> *(Trang 32) Hệ thống đã vượt qua **172/172 bài kiểm thử tự động**, đạt **100% tỷ lệ khớp khóa (0 orphan key)** và sẵn sàng demo tái lập tại chỗ trong 2 giây. Sau đây em xin bàn giao dữ liệu Gold cho bạn Minh trình bày tiếp phần kiến trúc kho dữ liệu MySQL."*

---

## 3. Lệnh Chạy Demo Trực tiếp Khi Vấn đáp (Live Demo)

- **Demo mẫu siêu tốc (~2 giây, khuyến nghị):**
  ```bash
  python scripts/demo_etl_pipeline.py --sample 500
  ```
- **Demo toàn bộ 1.17M dòng thật (~42 giây):**
  ```bash
  python scripts/demo_etl_pipeline.py --full
  ```
- **Chạy bộ kiểm thử hồi quy tự động (~0.65 giây):**
  ```bash
  python -m unittest tests/test_etl_regressions.py
  ```
