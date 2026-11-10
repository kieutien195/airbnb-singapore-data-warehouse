"""
build_etl_slides.py
-------------------
Tạo file slide PowerPoint (.pptx) chuẩn 16:9 chất lượng cao cho Task 5.4
(Slide quy trình ETL/ELT và Kiểm thử chất lượng dữ liệu).
Phụ trách: Thái (Data Engineer / ETL)
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SLIDES_DIR = PROJECT_ROOT / "slides"
SLIDES_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = SLIDES_DIR / "assets"
OUTPUT_PPTX = SLIDES_DIR / "5.4_slide_etl_pipeline_and_tests.pptx"

# Bảng màu chủ đạo (Corporate Modern Palette)
C_NAVY_DARK = RGBColor(15, 23, 42)      # #0F172A (Tiêu đề chính / Header)
C_NAVY_MED  = RGBColor(30, 41, 59)      # #1E293B (Thân chữ chính)
C_CYAN_ACC  = RGBColor(2, 132, 199)     # #0284C7 (Điểm nhấn Cyan)
C_EMERALD   = RGBColor(5, 150, 105)     # #059669 (Success / Đạt chuẩn)
C_AMBER     = RGBColor(217, 119, 6)     # #D97706 (Warning / Chú ý)
C_PURPLE    = RGBColor(124, 58, 237)    # #7C3AED (Accent chiều/fact)
C_BG_LIGHT  = RGBColor(248, 250, 252)   # #F8FAFC (Nền slide)
C_WHITE     = RGBColor(255, 255, 255)   # #FFFFFF (Nền Card)
C_BORDER    = RGBColor(203, 213, 225)   # #CBD5E1 (Viền mỏng)
C_SLATE_MUT = RGBColor(100, 116, 139)   # #64748B (Muted text / Chú thích)


def apply_background(slide):
    """Đặt nền màu sáng trang nhã cho slide"""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = C_BG_LIGHT


def add_slide_header(slide, title_text: str, subtitle_text: str, category_tag: str = "PHÂN HỆ ETL / ELT & TEST"):
    """Thêm Header đồng bộ cho từng slide"""
    # Tag danh mục nhỏ phía trên
    tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
    tf_tag = tag_box.text_frame
    tf_tag.word_wrap = True
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = category_tag.upper()
    p_tag.font.name = "Arial"
    p_tag.font.size = Pt(10)
    p_tag.font.bold = True
    p_tag.font.color.rgb = C_CYAN_ACC

    # Tiêu đề slide
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.68), Inches(11.7), Inches(0.6))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.name = "Arial"
    p_title.font.size = Pt(20)
    p_title.font.bold = True
    p_title.font.color.rgb = C_NAVY_DARK

    # Phụ đề slide
    sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.22), Inches(11.7), Inches(0.4))
    tf_sub = sub_box.text_frame
    tf_sub.word_wrap = True
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = subtitle_text
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = C_SLATE_MUT


def add_slide_footer(slide, current_page: int, total_pages: int = 6):
    """Thêm Footer thông tin nguồn, snapshot và số trang"""
    # Đường kẻ phân cách footer
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.9), Inches(11.733), Inches(0.015))
    line.fill.solid()
    line.fill.fore_color.rgb = C_BORDER
    line.line.color.rgb = C_BORDER

    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.95), Inches(10.0), Inches(0.35))
    tf_f = footer_box.text_frame
    p_f = tf_f.paragraphs[0]
    p_f.text = "Nhà kho dữ liệu Airbnb Singapore 2026 | Snapshot: 2026-09-23 | Phụ trách: Thái (Data Engineer)"
    p_f.font.name = "Arial"
    p_f.font.size = Pt(9)
    p_f.font.color.rgb = C_SLATE_MUT

    page_box = slide.shapes.add_textbox(Inches(11.5), Inches(6.95), Inches(1.0), Inches(0.35))
    tf_p = page_box.text_frame
    p_p = tf_p.paragraphs[0]
    p_p.text = f"{current_page} / {total_pages}"
    p_p.alignment = PP_ALIGN.RIGHT
    p_p.font.name = "Arial"
    p_p.font.size = Pt(9)
    p_p.font.bold = True
    p_p.font.color.rgb = C_CYAN_ACC


def add_card(slide, left, top, width, height, bg_color=C_WHITE, border_color=C_BORDER):
    """Thêm một container dạng Card hiện đại"""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1)
    return card


# ==============================================================================
# XÂY DỰNG CÁC SLIDE
# ==============================================================================

def build_presentation():
    prs = Presentation()
    # Tỉ lệ màn hình 16:9 Widescreen tiêu chuẩn
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # --------------------------------------------------------------------------
    # SLIDE 1: TIÊU ĐỀ PHÂN HỆ (TITLE / SECTION COVER)
    # --------------------------------------------------------------------------
    slide1 = prs.slides.add_slide(blank_layout)
    apply_background(slide1)

    # Nền khối trang trí phía sau
    hero_card = add_card(slide1, Inches(0.8), Inches(0.8), Inches(11.733), Inches(5.9), bg_color=C_WHITE, border_color=C_CYAN_ACC)

    # Badge đề tài
    badge = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.3), Inches(1.3), Inches(3.6), Inches(0.42))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(224, 242, 254)
    badge.line.color.rgb = C_CYAN_ACC
    tf_b = badge.text_frame
    p_b = tf_b.paragraphs[0]
    p_b.text = "TASK 5.4 · BÁO CÁO KỸ THUẬT CHUYÊN SÂU"
    p_b.font.name = "Arial"
    p_b.font.size = Pt(10)
    p_b.font.bold = True
    p_b.font.color.rgb = C_CYAN_ACC
    p_b.alignment = PP_ALIGN.CENTER

    # Tiêu đề lớn
    title_box = slide1.shapes.add_textbox(Inches(1.3), Inches(1.85), Inches(10.7), Inches(1.5))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Quy trình ETL/ELT Tích hợp Dữ liệu &"
    p.font.name = "Arial"
    p.font.size = Pt(30)
    p.font.bold = True
    p.font.color.rgb = C_NAVY_DARK

    p2 = tf.add_paragraph()
    p2.text = "Kiểm thử Chất lượng Dữ liệu Đa tầng"
    p2.font.name = "Arial"
    p2.font.size = Pt(30)
    p2.font.bold = True
    p2.font.color.rgb = C_CYAN_ACC

    # Mô tả tóm tắt
    desc_box = slide1.shapes.add_textbox(Inches(1.3), Inches(3.45), Inches(10.5), Inches(1.2))
    tf_desc = desc_box.text_frame
    tf_desc.word_wrap = True
    p_desc = tf_desc.paragraphs[0]
    p_desc.text = (
        "Hiện thực hóa pipeline tự động hóa từ 4 tệp nguồn nén Inside Airbnb Singapore (1.17M dòng) "
        "đến Kho dữ liệu Star Schema MySQL. Bảo đảm 100% tính khả lặp (Idempotency TQ-05), "
        "chuẩn hóa tiền tệ SGD, giữ trọn vẹn dữ liệu nghiệp vụ và triệt tiêu hoàn toàn lỗi liên kết (0 Orphan Key)."
    )
    p_desc.font.name = "Arial"
    p_desc.font.size = Pt(13)
    p_desc.font.color.rgb = C_NAVY_MED

    # 3 Khối thông số kỹ thuật then chốt dưới cùng
    stats = [
        ("1.170.950", "Dòng Calendar xử lý vector hóa trong 42s", C_CYAN_ACC),
        ("100.0%", "Khớp khóa ngoại (0 Orphan Key trên 4 quan hệ)", C_EMERALD),
        ("321 / 321", "Test cases QA Pass tuyệt đối (0 FAIL)", C_PURPLE)
    ]
    for i, (val, label, col) in enumerate(stats):
        bx = Inches(1.3 + i * 3.65)
        card_stat = add_card(slide1, bx, Inches(4.7), Inches(3.4), Inches(1.5), bg_color=RGBColor(241, 245, 249), border_color=C_BORDER)
        tb_s = slide1.shapes.add_textbox(bx + Inches(0.15), Inches(4.8), Inches(3.1), Inches(1.3))
        tfs = tb_s.text_frame
        ps1 = tfs.paragraphs[0]
        ps1.text = val
        ps1.font.name = "Arial"
        ps1.font.size = Pt(22)
        ps1.font.bold = True
        ps1.font.color.rgb = col
        ps2 = tfs.add_paragraph()
        ps2.text = label
        ps2.font.name = "Arial"
        ps2.font.size = Pt(10)
        ps2.font.color.rgb = C_NAVY_MED

    # Footer
    add_slide_footer(slide1, 1, 6)

    # --------------------------------------------------------------------------
    # SLIDE 2: LUỒNG PIPELINE TOÀN TRÌNH (KHỚP TRANG 12 ĐỒ ÁN)
    # --------------------------------------------------------------------------
    slide2 = prs.slides.add_slide(blank_layout)
    apply_background(slide2)
    add_slide_header(
        slide2,
        "Luồng Dữ liệu ETL/ELT Toàn trình (End-to-End Pipeline Architecture)",
        "Năm chặng tích hợp khép kín: Raw (CSV.GZ) -> Staging -> Silver -> Gold (Star Schema) -> MySQL Warehouse"
    )

    # Thêm sơ đồ trực quan (etl_pipeline_flow.png)
    flow_img_path = ASSETS_DIR / "etl_pipeline_flow.png"
    if flow_img_path.exists():
        slide2.shapes.add_picture(str(flow_img_path), Inches(0.8), Inches(1.7), width=Inches(8.2))

    # Cột tóm tắt kỹ thuật bên phải (3 Cards)
    side_cards = [
        {
            "title": "Cơ chế Khả lặp (Idempotency - TQ-05)",
            "text": "Xóa partition cũ theo snapshot_date (2026-09-23) trong một transaction an toàn trước khi nạp lại. Chạy lại nhiều lần không bao giờ phát sinh trùng dòng.",
            "color": C_CYAN_ACC
        },
        {
            "title": "Hiệu năng Xử lý Chunking & Vector hóa",
            "text": "Calendar (1.17M dòng) nạp theo chunk 100k dòng. Toàn bộ thao tác ép kiểu và regex được vector hóa bằng NumPy/Pandas, hoàn thành toàn trình trong 42.67s.",
            "color": C_EMERALD
        },
        {
            "title": "Quy tắc Kiểm soát Fan-Out (Tránh lỗi nhân dòng)",
            "text": "Tuyệt đối không JOIN trực tiếp Calendar x Reviews (đều là 1-N với Listings). Các Fact được tổng hợp độc lập về grain tương ứng trước khi đưa lên BI.",
            "color": C_AMBER
        }
    ]

    for i, c in enumerate(side_cards):
        cy = Inches(1.7 + i * 1.65)
        add_card(slide2, Inches(9.2), cy, Inches(3.333), Inches(1.5), bg_color=C_WHITE, border_color=c["color"])
        tb = slide2.shapes.add_textbox(Inches(9.35), cy + Inches(0.1), Inches(3.05), Inches(1.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = c["title"]
        p1.font.name = "Arial"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = c["color"]

        p2 = tf.add_paragraph()
        p2.text = c["text"]
        p2.font.name = "Arial"
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_NAVY_MED

    add_slide_footer(slide2, 2, 6)

    # --------------------------------------------------------------------------
    # SLIDE 3: QUY TẮC LÀM SẠCH & MA TRẬN XỬ LÝ LỖI (KHỚP TRANG 09 ĐỒ ÁN)
    # --------------------------------------------------------------------------
    slide3 = prs.slides.add_slide(blank_layout)
    apply_background(slide3)
    add_slide_header(
        slide3,
        "Quy tắc Làm sạch & Bốn Phép Biến đổi Dữ liệu Cốt lõi (Task 3.3)",
        "Chuẩn hóa kiểu dữ liệu, xác minh đơn vị đo và bảo toàn trọn vẹn sự thật nghiệp vụ (Business Facts)"
    )

    # Thêm sơ đồ 4 phép biến đổi (transformations_rules.png)
    trans_img_path = ASSETS_DIR / "transformations_rules.png"
    if trans_img_path.exists():
        slide3.shapes.add_picture(str(trans_img_path), Inches(0.8), Inches(1.7), width=Inches(8.2))

    # Cột tóm tắt đối soát bên phải
    right_card = add_card(slide3, Inches(9.2), Inches(1.7), Inches(3.333), Inches(4.95), bg_color=C_WHITE, border_color=C_PURPLE)
    tb_r = slide3.shapes.add_textbox(Inches(9.35), Inches(1.85), Inches(3.05), Inches(4.65))
    tfr = tb_r.text_frame
    tfr.word_wrap = True

    pr1 = tfr.paragraphs[0]
    pr1.text = "BẢNG ĐỐI SOÁT TRƯỚC - SAU"
    pr1.font.name = "Arial"
    pr1.font.size = Pt(12)
    pr1.font.bold = True
    pr1.font.color.rgb = C_PURPLE

    rules_summary = [
        ("Listings (3.208 dòng)", "• 2.725 giá SGD hợp lệ\n• 483 giá NULL giữ nguyên\n• 1.369 rating NULL giữ nguyên\n• 134 IQR outliers được bảo toàn"),
        ("Calendar (1.170.950 dòng)", "• 900.960 đêm available (76.94%)\n• 269.990 đêm unavailable\n• Ép boolean 't'/'f' -> 1/0\n• 0 dòng bị loại ngoài ý muốn"),
        ("Reviews (46.000 dòng)", "• Khử trùng theo (listing_id, review_id, snapshot_date)\n• 100% khớp ngày review"),
        ("Neighbourhoods (55 dòng)", "• 5 vùng quy hoạch lớn\n• 55 khu vực chuẩn URA")
    ]

    for title, desc in rules_summary:
        pt = tfr.add_paragraph()
        pt.text = f"\n{title}"
        pt.font.name = "Arial"
        pt.font.size = Pt(10)
        pt.font.bold = True
        pt.font.color.rgb = C_NAVY_DARK

        pd = tfr.add_paragraph()
        pd.text = desc
        pd.font.name = "Arial"
        pd.font.size = Pt(9)
        pd.font.color.rgb = C_NAVY_MED

    add_slide_footer(slide3, 3, 6)

    # --------------------------------------------------------------------------
    # SLIDE 4: XÁC MINH TIỀN TỆ SGD & BẢO TOÀN DỮ LIỆU (KHỚP TRANG 10 ĐỒ ÁN)
    # --------------------------------------------------------------------------
    slide4 = prs.slides.add_slide(blank_layout)
    apply_background(slide4)
    add_slide_header(
        slide4,
        "Kiểm định Tiền tệ SGD & Phân giải Giá Niêm yết (Price Disambiguation)",
        "Cơ chế 2 lớp xác minh mã tiền tệ từ JSON raw, bảo toàn giá trị thiếu và tôn trọng phân phối thực tế"
    )

    # 2 Cột so sánh chi tiết: Cột Trái là Logic Kiểm định, Cột Phải là Bằng chứng đối chiếu
    col_w = Inches(5.65)

    # Khối 1: Cơ chế kiểm định 2 lớp (Trái)
    add_card(slide4, Inches(0.8), Inches(1.7), col_w, Inches(4.95), bg_color=C_WHITE, border_color=C_CYAN_ACC)
    tb_c1 = slide4.shapes.add_textbox(Inches(1.0), Inches(1.85), col_w - Inches(0.4), Inches(4.65))
    tf1 = tb_c1.text_frame
    tf1.word_wrap = True

    p = tf1.paragraphs[0]
    p.text = "CƠ CHẾ KIỂM ĐỊNH GIÁ 2 LỚP CHẶT CHẼ"
    p.font.name = "Arial"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = C_CYAN_ACC

    points1 = [
        ("Lớp 1: Bóc tách chuỗi giá niêm yết (Raw Price)",
         "• Chuỗi gốc: '$1,250.00' -> loại bỏ '$', dấu phẩy, khoảng trắng.\n• Ép kiểu thành số thực DECIMAL(10,2) chính xác."),
        ("Lớp 2: Đối chiếu mã tiền tệ từ JSON raw (Currency Verification)",
         "• Cột 'price_quote_raw' chứa JSON cấu trúc: {'currency': 'SGD', ...}.\n• Gán cờ is_price_sgd_verified = 1 khi mã là 'SGD'.\n• 2.725 / 3.208 tin đăng được xác minh chuẩn SGD."),
        ("Bảo toàn giá trị thiếu (Preserve Valid NULLs)",
         "• 483 tin đăng có giá NULL được GIỮ NGUYÊN NULL.\n• Tuyệt đối KHÔNG gán bằng 0 (vì gán 0 sẽ kéo tụt trung vị sai lệch nghiêm trọng)."),
        ("Tôn trọng phân phối Outlier (134 bản ghi ngoài IQR)",
         "• Giữ nguyên toàn bộ giá trị cực đoan (biệt thự, penthouse cao cấp).\n• Tuân thủ nghiêm ngặt nguyên tắc: EDA phát hiện outlier để ghi nhận, không tự tiện xóa bỏ dữ liệu nghiệp vụ.")
    ]
    for h, b in points1:
        ph = tf1.add_paragraph()
        ph.text = f"\n{h}"
        ph.font.name = "Arial"
        ph.font.size = Pt(10.5)
        ph.font.bold = True
        ph.font.color.rgb = C_NAVY_DARK

        pb = tf1.add_paragraph()
        pb.text = b
        pb.font.name = "Arial"
        pb.font.size = Pt(9.5)
        pb.font.color.rgb = C_NAVY_MED

    # Khối 2: Kết quả đối soát số liệu (Phải)
    add_card(slide4, Inches(6.88), Inches(1.7), col_w, Inches(4.95), bg_color=C_WHITE, border_color=C_EMERALD)
    tb_c2 = slide4.shapes.add_textbox(Inches(7.08), Inches(1.85), col_w - Inches(0.4), Inches(4.65))
    tf2 = tb_c2.text_frame
    tf2.word_wrap = True

    p = tf2.paragraphs[0]
    p.text = "KẾT QUẢ ĐỐI SOÁT VỚI CHUẨN BASELINE KPI-02"
    p.font.name = "Arial"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD

    points2 = [
        ("Chỉ tiêu Trung vị Giá niêm yết (Median Price)",
         "• Kết quả tính toán từ Silver / Gold: 202.83 SGD\n• Chuẩn baseline KPI-02: 202.83 SGD\n-> Chênh lệch tuyệt đối: 0.00 SGD (Khớp chuẩn 100.0%)"),
        ("Mẫu số tin đăng có giá hợp lệ (Valid Sample Size)",
         "• Tổng số tin đăng có giá SGD hợp lệ: 2.725 / 3.208 tin (84.94%)\n• Số tin đăng thiếu giá (NULL): 483 tin (15.06%)\n-> Khớp chính xác với báo cáo khảo sát Data Quality Baseline"),
        ("Kiểm định kiểu dữ liệu 'accommodates' (Số khách)",
         "• Lưu trữ kiểu INT UNSIGNED (phạm vi từ 1 đến 16 người).\n• Khắc phục hoàn toàn lỗi parse nhầm sang kiểu DATE trong các bản nháp trước."),
        ("Quy chuẩn làm tròn & Decimal Precision",
         "• Số đêm bình quân minimum_nights_avg_ntm giữ nguyên phần thập phân.\n• Giá tiền lưu trữ kiểu DECIMAL(10,2) trong MySQL, bảo toàn từng xu.")
    ]
    for h, b in points2:
        ph = tf2.add_paragraph()
        ph.text = f"\n{h}"
        ph.font.name = "Arial"
        ph.font.size = Pt(10.5)
        ph.font.bold = True
        ph.font.color.rgb = C_NAVY_DARK

        pb = tf2.add_paragraph()
        pb.text = b
        pb.font.name = "Arial"
        pb.font.size = Pt(9.5)
        pb.font.color.rgb = C_NAVY_MED

    add_slide_footer(slide4, 4, 6)

    # --------------------------------------------------------------------------
    # SLIDE 5: MAPPING STAR SCHEMA & KIỂM TRA QUAN HỆ ĐA BẢNG (TASK 3.4)
    # --------------------------------------------------------------------------
    slide5 = prs.slides.add_slide(blank_layout)
    apply_background(slide5)
    add_slide_header(
        slide5,
        "Ánh xạ Star Schema & Kiểm tra Quan hệ Đa bảng (Zero Orphan Key)",
        "Chuẩn hóa mô hình đa chiều Fact Constellation và bảo đảm toàn vẹn tham chiếu 100% (Task 3.4)"
    )

    # Thêm biểu đồ đối soát và kiểm tra quan hệ (join_coverage_audit.png)
    cov_img_path = ASSETS_DIR / "join_coverage_audit.png"
    if cov_img_path.exists():
        slide5.shapes.add_picture(str(cov_img_path), Inches(0.8), Inches(1.7), width=Inches(8.2))

    # Cột tóm tắt 4 quan hệ tham chiếu bên phải
    card_rel = add_card(slide5, Inches(9.2), Inches(1.7), Inches(3.333), Inches(4.95), bg_color=C_WHITE, border_color=C_EMERALD)
    tb_rel = slide5.shapes.add_textbox(Inches(9.35), Inches(1.85), Inches(3.05), Inches(4.65))
    tf_rel = tb_rel.text_frame
    tf_rel.word_wrap = True

    pr = tf_rel.paragraphs[0]
    pr.text = "KẾT QUẢ KIỂM TRA ORPHAN KEYS"
    pr.font.name = "Arial"
    pr.font.size = Pt(12)
    pr.font.bold = True
    pr.font.color.rgb = C_EMERALD

    rels = [
        ("REL-01: Calendar -> Listings (1-N)", "1.170.950 / 1.170.950 bản ghi khớp\nOrphan: 0 (Match: 100.0% -> PASS)"),
        ("REL-02: Reviews -> Listings (1-N)", "46.000 / 46.000 bản ghi khớp\nOrphan: 0 (Match: 100.0% -> PASS)"),
        ("REL-03: Listings -> Neighbourhoods", "3.208 / 3.208 bản ghi khớp URA\nOrphan: 0 (Match: 100.0% -> PASS)"),
        ("REL-04: Event Dates -> dim_date", "2.437.108 lượt tham chiếu ngày khớp\nOrphan: 0 (Match: 100.0% -> PASS)")
    ]

    for title, desc in rels:
        pt = tf_rel.add_paragraph()
        pt.text = f"\n{title}"
        pt.font.name = "Arial"
        pt.font.size = Pt(10)
        pt.font.bold = True
        pt.font.color.rgb = C_NAVY_DARK

        pd = tf_rel.add_paragraph()
        pd.text = desc
        pd.font.name = "Arial"
        pd.font.size = Pt(9)
        pd.font.color.rgb = C_EMERALD

    add_slide_footer(slide5, 5, 6)

    # --------------------------------------------------------------------------
    # SLIDE 6: MINH CHỨNG THỰC NGHIỆM & HƯỚNG DẪN DEMO (KHỚP PHỤ LỤC B)
    # --------------------------------------------------------------------------
    slide6 = prs.slides.add_slide(blank_layout)
    apply_background(slide6)
    add_slide_header(
        slide6,
        "Minh chứng Thực nghiệm, Kiểm thử Tự động & Hướng dẫn Tái lập (Task 5.4)",
        "Bằng chứng chạy thật terminal, kết quả bộ test tự động và kịch bản demo 1-2 phút phục vụ vấn đáp"
    )

    # Thêm ảnh Terminal chạy thật (terminal_execution_proof.png)
    term_img_path = ASSETS_DIR / "terminal_execution_proof.png"
    if term_img_path.exists():
        slide6.shapes.add_picture(str(term_img_path), Inches(0.8), Inches(1.7), width=Inches(7.2))

    # Cột hướng dẫn tái lập & Kịch bản demo (Bên phải)
    card_demo = add_card(slide6, Inches(8.2), Inches(1.7), Inches(4.333), Inches(4.95), bg_color=C_WHITE, border_color=C_CYAN_ACC)
    tb_demo = slide6.shapes.add_textbox(Inches(8.4), Inches(1.85), Inches(3.95), Inches(4.65))
    tf_demo = tb_demo.text_frame
    tf_demo.word_wrap = True

    pd0 = tf_demo.paragraphs[0]
    pd0.text = "HƯỚNG DẪN TÁI LẬP & DEMO TẠI CHỖ"
    pd0.font.name = "Arial"
    pd0.font.size = Pt(12)
    pd0.font.bold = True
    pd0.font.color.rgb = C_CYAN_ACC

    demo_steps = [
        ("1. Chạy Demo Nhanh (Sample Mode - 2 giây)",
         "Lệnh: python scripts/demo_etl_pipeline.py --sample 500\n-> Đọc mẫu 500 dòng/nguồn, thực thi toàn bộ 3 chặng Ingest -> Clean -> Transform và in bảng đối soát."),
        ("2. Chạy Toàn bộ Dữ liệu Thật (Full Mode - 42 giây)",
         "Lệnh: python scripts/demo_etl_pipeline.py --full\n-> Xử lý toàn bộ 1.17M dòng, nạp Gold và đối soát 0 orphan."),
        ("3. Chạy Bộ Kiểm thử Hồi quy (Automated QA Test)",
         "Lệnh: python -m unittest tests/test_etl_regressions.py\n-> 5 test cases chuyên sâu về Idempotency, grain và rollback pass 100% trong 0.65s."),
        ("4. Kịch bản Thuyết trình 1-2 Phút (Elevator Pitch)",
         "• 'Thưa thầy cô, em phụ trách phân hệ ETL/ELT chuyển đổi 1.17M bản ghi thô thành Star Schema sạch.'\n• '3 điểm nhấn kỹ thuật: (1) Idempotency xóa partition cũ theo snapshot tránh nhân đôi; (2) Chuẩn hóa SGD và bảo toàn trọn vẹn 483 NULL giá; (3) Khớp 100% khóa ngoại (0 orphan key) và kiểm soát hoàn toàn fan-out.'")
    ]

    for title, desc in demo_steps:
        pt = tf_demo.add_paragraph()
        pt.text = f"\n{title}"
        pt.font.name = "Arial"
        pt.font.size = Pt(10)
        pt.font.bold = True
        pt.font.color.rgb = C_NAVY_DARK

        pdesc = tf_demo.add_paragraph()
        pdesc.text = desc
        pdesc.font.name = "Arial"
        pdesc.font.size = Pt(8.8)
        pdesc.font.color.rgb = C_NAVY_MED

    add_slide_footer(slide6, 6, 6)

    # Lưu file PPTX
    prs.save(OUTPUT_PPTX)
    print(f"[OK] PowerPoint presentation created successfully at: {OUTPUT_PPTX}")


if __name__ == "__main__":
    build_presentation()
