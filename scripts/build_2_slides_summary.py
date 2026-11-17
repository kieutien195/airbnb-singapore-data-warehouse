"""
build_2_slides_summary.py
-------------------------
Tạo tệp PowerPoint (.pptx) chuẩn 16:9 tinh gọn đúng 2 SLIDES ĐẦY ĐỦ NHẤT:
- Slide 1: Quy trình ETL/ELT Toàn trình & 4 Phép Biến đổi Dữ liệu Cốt lõi
- Slide 2: Kiểm thử Chất lượng Đa tầng, Đối soát Raw-Gold & Minh chứng Live Demo

Đặc biệt kiểm soát tọa độ chính xác, phân bổ padding và cỡ chữ hợp lý,
bảo đảm TUYỆT ĐỐI KHÔNG BỊ ĐÈ CHỮ, KHÔNG TRÀN KHUNG trên mọi thiết bị.
Tác giả: Thái (Data Engineer / ETL)
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
OUTPUT_PPTX_2SLIDES = SLIDES_DIR / "5.4_slide_etl_summary_2slides.pptx"
OUTPUT_PPTX_MAIN = SLIDES_DIR / "5.4_slide_etl_pipeline_and_tests.pptx"

# Bảng màu thiết kế chuyên nghiệp (Corporate Palette)
C_NAVY_DARK = RGBColor(15, 23, 42)      # #0F172A (Tiêu đề chính)
C_NAVY_BODY = RGBColor(30, 41, 59)      # #1E293B (Thân chữ)
C_CYAN_ACC  = RGBColor(2, 132, 199)     # #0284C7 (Cyan điểm nhấn)
C_EMERALD   = RGBColor(5, 150, 105)     # #059669 (Xanh lá - Success / Data Quality)
C_AMBER     = RGBColor(217, 119, 6)     # #D97706 (Cam - Warning / Highlight)
C_PURPLE    = RGBColor(124, 58, 237)    # #7C3AED (Tím - Architecture / Model)
C_BG_SLATE  = RGBColor(248, 250, 252)   # #F8FAFC (Nền slide sáng)
C_WHITE     = RGBColor(255, 255, 255)   # #FFFFFF (Nền Card)
C_BORDER    = RGBColor(203, 213, 225)   # #CBD5E1 (Viền card)
C_SLATE_MUT = RGBColor(100, 116, 139)   # #64748B (Chú thích nhỏ)
C_CODE_BG   = RGBColor(241, 245, 249)   # #F1F5F9 (Nền code snippet)


def set_slide_background(slide):
    """Thiết lập nền sáng hiện đại"""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = C_BG_SLATE


def add_header(slide, title_text: str, subtitle_text: str, tag_text: str):
    """Header chuẩn, tọa độ tính toán kỹ để không chiếm quá 1.35 inch"""
    # 1. Tag danh mục
    tb_tag = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(11.733), Inches(0.25))
    tf_tag = tb_tag.text_frame
    tf_tag.word_wrap = True
    tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = tag_text.upper()
    p_tag.font.name = "Arial"
    p_tag.font.size = Pt(9.5)
    p_tag.font.bold = True
    p_tag.font.color.rgb = C_CYAN_ACC

    # 2. Tiêu đề slide
    tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.58), Inches(11.733), Inches(0.42))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.name = "Arial"
    p_title.font.size = Pt(19)
    p_title.font.bold = True
    p_title.font.color.rgb = C_NAVY_DARK

    # 3. Phụ đề tóm tắt giá trị
    tb_sub = slide.shapes.add_textbox(Inches(0.8), Inches(1.02), Inches(11.733), Inches(0.28))
    tf_sub = tb_sub.text_frame
    tf_sub.word_wrap = True
    tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = subtitle_text
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = C_SLATE_MUT


def add_footer(slide, current_page: int, total_pages: int = 2):
    """Footer thanh mảnh, ghi rõ nguồn, snapshot và số trang"""
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.92), Inches(11.733), Inches(0.012))
    line.fill.solid()
    line.fill.fore_color.rgb = C_BORDER
    line.line.color.rgb = C_BORDER

    tb_f = slide.shapes.add_textbox(Inches(0.8), Inches(6.96), Inches(10.0), Inches(0.3))
    tf_f = tb_f.text_frame
    tf_f.margin_left = tf_f.margin_top = tf_f.margin_right = tf_f.margin_bottom = 0
    p_f = tf_f.paragraphs[0]
    p_f.text = "Đồ án Nhà kho dữ liệu Airbnb Singapore 2026 | Snapshot: 2026-09-23 | Thành viên phụ trách: Thái (Data Engineer)"
    p_f.font.name = "Arial"
    p_f.font.size = Pt(8.5)
    p_f.font.color.rgb = C_SLATE_MUT

    tb_p = slide.shapes.add_textbox(Inches(11.5), Inches(6.96), Inches(1.033), Inches(0.3))
    tf_p = tb_p.text_frame
    tf_p.margin_left = tf_p.margin_top = tf_p.margin_right = tf_p.margin_bottom = 0
    p_p = tf_p.paragraphs[0]
    p_p.text = f"Trang {current_page} / {total_pages}"
    p_p.alignment = PP_ALIGN.RIGHT
    p_p.font.name = "Arial"
    p_p.font.size = Pt(8.5)
    p_p.font.bold = True
    p_p.font.color.rgb = C_CYAN_ACC


def add_rounded_card(slide, left, top, width, height, bg_color=C_WHITE, border_color=C_BORDER, border_pt=1):
    """Tạo Card nền với bo góc trang nhã"""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(border_pt)
    return card


# ==============================================================================
# XÂY DỰNG SLIDE 1: KIẾN TRÚC LUỒNG ETL & 4 PHÉP BIẾN ĐỔI CỐT LÕI
# ==============================================================================
def create_slide_1(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(
        slide,
        title_text="Kiến trúc Luồng ETL/ELT Toàn trình & Bốn Phép Biến đổi Dữ liệu Cốt lõi",
        subtitle_text="Năm chặng tích hợp khép kín chuyển hóa 1.17M dòng dữ liệu thô sang Star Schema; bảo đảm khả lặp và bảo toàn facts",
        tag_text="PHÂN HỆ TÍCH HỢP DỮ LIỆU (ETL / ELT) · THÁI (DATA ENGINEER)"
    )

    # --------------------------------------------------------------------------
    # KHỐI TRÊN: 5 CHẶNG LUỒNG DỮ LIỆU (TOP ROW: y = 1.38, h = 1.55)
    # --------------------------------------------------------------------------
    stages = [
        {
            "step": "CHẶNG 1",
            "name": "RAW DATA (GZ)",
            "bullets": [
                "4 tệp nén Inside Airbnb",
                "Listings (3.2k), Calendar (1.17M)",
                "Reviews (46k), Neighbours (55)",
                "Snapshot: 2026-09-23"
            ],
            "accent": C_NAVY_DARK
        },
        {
            "step": "CHẶNG 2",
            "name": "STAGING (BRONZE)",
            "bullets": [
                "Chunking 100k dòng (Calendar)",
                "Metadata: snapshot, file, time",
                "Idempotent: xóa partition cũ",
                "Transaction an toàn (Rollback)"
            ],
            "accent": C_CYAN_ACC
        },
        {
            "step": "CHẶNG 3",
            "name": "SILVER (CLEANED)",
            "bullets": [
                "Vectorized Regex & Ép kiểu",
                "Kiểm định mã tiền tệ SGD",
                "Khử trùng grain từng bảng",
                "Bảo toàn trọn vẹn NULL & Outlier"
            ],
            "accent": C_EMERALD
        },
        {
            "step": "CHẶNG 4",
            "name": "GOLD STAR SCHEMA",
            "bullets": [
                "3 Dim: date, neighbour, listing",
                "3 Fact độc lập (Constellation)",
                "Sinh Surrogate Key số nguyên",
                "Tuyệt đối CẤM join chéo Fan-out"
            ],
            "accent": C_PURPLE
        },
        {
            "step": "CHẶNG 5",
            "name": "WAREHOUSE & BI",
            "bullets": [
                "Nạp MySQL Dim trước Fact sau",
                "0 Orphan Key (100% khớp)",
                "Chuẩn hóa KPI Views (Minh)",
                "Kết nối Direct/Import Power BI"
            ],
            "accent": C_AMBER
        }
    ]

    card_w = Inches(2.18)
    gap_w = Inches(0.208)
    top_y = Inches(1.38)
    top_h = Inches(1.58)

    for i, st in enumerate(stages):
        x = Inches(0.8) + i * (card_w + gap_w)

        # Hộp nền
        add_rounded_card(slide, x, top_y, card_w, top_h, bg_color=C_WHITE, border_color=st["accent"], border_pt=1.5)

        # Thanh header màu nhỏ phía trên của thẻ
        bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, top_y, card_w, Inches(0.38))
        bar.fill.solid()
        bar.fill.fore_color.rgb = st["accent"]
        bar.line.color.rgb = st["accent"]
        tf_bar = bar.text_frame
        tf_bar.word_wrap = True
        tf_bar.margin_left = tf_bar.margin_right = tf_bar.margin_top = tf_bar.margin_bottom = 0
        p_bar = tf_bar.paragraphs[0]
        p_bar.text = f"{st['step']} · {st['name']}"
        p_bar.font.name = "Arial"
        p_bar.font.size = Pt(8.5)
        p_bar.font.bold = True
        p_bar.font.color.rgb = C_WHITE
        p_bar.alignment = PP_ALIGN.CENTER

        # Nội dung bullets
        tb_c = slide.shapes.add_textbox(x + Inches(0.08), top_y + Inches(0.42), card_w - Inches(0.16), top_h - Inches(0.46))
        tf_c = tb_c.text_frame
        tf_c.word_wrap = True
        tf_c.margin_left = tf_c.margin_right = tf_c.margin_top = tf_c.margin_bottom = 0

        for b_idx, b_text in enumerate(st["bullets"]):
            p = tf_c.paragraphs[0] if b_idx == 0 else tf_c.add_paragraph()
            p.text = f"• {b_text}"
            p.font.name = "Arial"
            p.font.size = Pt(7.8)
            p.font.color.rgb = C_NAVY_BODY
            p.space_after = Pt(2)

        # Mũi tên liên kết sang bước kế tiếp
        if i < len(stages) - 1:
            arr_box = slide.shapes.add_textbox(x + card_w, top_y + Inches(0.65), gap_w, Inches(0.3))
            tf_a = arr_box.text_frame
            tf_a.margin_left = tf_a.margin_right = tf_a.margin_top = tf_a.margin_bottom = 0
            pa = tf_a.paragraphs[0]
            pa.text = "➔"
            pa.alignment = PP_ALIGN.CENTER
            pa.font.name = "Arial"
            pa.font.size = Pt(13)
            pa.font.bold = True
            pa.font.color.rgb = C_CYAN_ACC

    # --------------------------------------------------------------------------
    # KHỐI DƯỚI: 4 PHÉP BIẾN ĐỔI DỮ LIỆU CỐT LÕI (BOTTOM ROW: y = 3.08, h = 3.70)
    # --------------------------------------------------------------------------
    bot_y = Inches(3.08)
    bot_h = Inches(3.70)
    col_w = Inches(2.78)
    col_gap = Inches(0.204)

    rules_cards = [
        {
            "idx": "1",
            "title": "GIÁ (PRICE) & TIỀN TỆ (SGD)",
            "accent": C_CYAN_ACC,
            "sections": [
                ("VẤN ĐỀ NGUỒN", "Chuỗi ký tự '$1,250.00' hoặc NULL; nguy cơ lẫn mã tiền ngoại tệ."),
                ("QUY TẮC XỬ LÝ (2 LỚP)", "• Bóc tách regex '$', dấu phẩy -> ép DECIMAL(10,2).\n• Đối chiếu JSON thô: is_price_sgd_verified = 1 khi currency là SGD (2.725 tin hợp lệ)."),
                ("BẢO TOÀN NGHIỆP VỤ", "• 483 NULL giữ nguyên NULL (tuyệt đối KHÔNG gán 0 làm méo mó trung vị).\n• 134 IQR outliers được bảo toàn 100%."),
                ("KẾT QUẢ ĐẦU RA", "Trung vị chuẩn 202.83 SGD (Khớp 100% KPI-02).")
            ]
        },
        {
            "idx": "2",
            "title": "CHUẨN HÓA MỐC THỜI GIAN",
            "accent": C_EMERALD,
            "sections": [
                ("VẤN ĐỀ NGUỒN", "Nhiều định dạng ngày: '2026-09-25', last_scraped, ngày review từ 2011."),
                ("QUY TẮC XỬ LÝ", "• Ép kiểu DATE chuẩn ISO 8601 (YYYY-MM-DD).\n• Sinh surrogate key số nguyên date_sk (YYYYMMDD) liên kết với dim_date (6.209 ngày).\n• Khắc phục triệt để lỗi parse nhầm accommodates thành date (giữ INT 1..16)."),
                ("TÍNH TOÀN VẸN", "2.437.108 lượt tham chiếu ngày đều khớp 100% vào dim_date (không sót ngày)."),
                ("KẾT QUẢ ĐẦU RA", "Đồng bộ trục thời gian xuyên suốt từ 2011–2027.")
            ]
        },
        {
            "idx": "3",
            "title": "TRẠNG THÁI SẴN CÓ (AVAILABLE)",
            "accent": C_AMBER,
            "sections": [
                ("VẤN ĐỀ NGUỒN", "Cột available là ký tự 't' / 'f' trên 1.170.950 dòng lịch quan sát."),
                ("QUY TẮC XỬ LÝ", "• Vectorized mapping: 't' -> 1, 'f' -> 0 (TINYINT).\n• Tỷ lệ đêm mở lịch: 900.960 đêm available (76.94%) và 269.990 đêm unavailable (23.06%)."),
                ("GIỚI HẠN NGHIỆP VỤ", "• 'f' chỉ đo ngày lịch ĐÓNG, KHÔNG đồng nghĩa là đã đặt phòng (booked) hay công suất thuê.\n• Ngăn suy diễn sai doanh thu thực tế."),
                ("KẾT QUẢ ĐẦU RA", "Khớp 100% baseline KPI-04 (Available 76.94%).")
            ]
        },
        {
            "idx": "4",
            "title": "KHỬ TRÙNG & KIỂM SOÁT FAN-OUT",
            "accent": C_PURPLE,
            "sections": [
                ("VẤN ĐỀ NGUỒN", "Khác biệt grain sâu sắc; nguy cơ bùng nổ dữ liệu khi JOIN đa bảng."),
                ("QUY TẮC XỬ LÝ", "• Khử trùng theo đúng grain nghiệp vụ: Listings (id), Reviews (listing_id, review_id, snapshot_date).\n• Sinh Surrogate Key tăng dần cho Star Schema."),
                ("NGĂN CHẶN FAN-OUT", "• CẤM TUYỆT ĐỐI JOIN trực tiếp Calendar x Reviews (tránh nhân dòng thành 53 tỷ bản ghi).\n• Tổng hợp độc lập từng Fact trước khi đưa lên BI."),
                ("KẾT QUẢ ĐẦU RA", "Bảo toàn đúng 3.208 listings và 46.000 reviews.")
            ]
        }
    ]

    for i, rc in enumerate(rules_cards):
        x = Inches(0.8) + i * (col_w + col_gap)

        # Nền card
        add_rounded_card(slide, x, bot_y, col_w, bot_h, bg_color=C_WHITE, border_color=rc["accent"], border_pt=1.5)

        # Tiêu đề Card
        header_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, bot_y, col_w, Inches(0.38))
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = rc["accent"]
        header_shape.line.color.rgb = rc["accent"]
        tf_h = header_shape.text_frame
        tf_h.word_wrap = True
        tf_h.margin_left = tf_h.margin_right = tf_h.margin_top = tf_h.margin_bottom = 0
        p_h = tf_h.paragraphs[0]
        p_h.text = f"{rc['idx']}. {rc['title']}"
        p_h.font.name = "Arial"
        p_h.font.size = Pt(8.5)
        p_h.font.bold = True
        p_h.font.color.rgb = C_WHITE
        p_h.alignment = PP_ALIGN.CENTER

        # Hộp chứa văn bản chi tiết bên trong
        tb_body = slide.shapes.add_textbox(x + Inches(0.12), bot_y + Inches(0.44), col_w - Inches(0.24), bot_h - Inches(0.52))
        tf_body = tb_body.text_frame
        tf_body.word_wrap = True
        tf_body.margin_left = tf_body.margin_right = tf_body.margin_top = tf_body.margin_bottom = 0

        first_sec = True
        for sec_title, sec_text in rc["sections"]:
            p_st = tf_body.paragraphs[0] if first_sec else tf_body.add_paragraph()
            first_sec = False
            p_st.text = sec_title
            p_st.font.name = "Arial"
            p_st.font.size = Pt(7.8)
            p_st.font.bold = True
            p_st.font.color.rgb = rc["accent"]
            p_st.space_before = Pt(3) if not first_sec else Pt(0)
            p_st.space_after = Pt(1)

            p_ctx = tf_body.add_paragraph()
            p_ctx.text = sec_text
            p_ctx.font.name = "Arial"
            p_ctx.font.size = Pt(7.3)
            p_ctx.font.color.rgb = C_NAVY_BODY
            p_ctx.line_spacing = 1.15
            p_ctx.space_after = Pt(3)

    add_footer(slide, 1, 2)


# ==============================================================================
# XÂY DỰNG SLIDE 2: KIỂM THỬ ĐA TẦNG, ĐỐI SOÁT & MINH CHỨNG THỰC NGHIỆM
# ==============================================================================
def create_slide_2(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)
    add_header(
        slide,
        title_text="Kiểm thử Toàn vẹn Đa tầng, Đối soát Raw–Gold & Minh chứng Live Demo",
        subtitle_text="Đạt 100.0% tỷ lệ khớp khóa ngoại (0 orphan key), 321/321 test QA Pass và sẵn sàng tái chạy demo trong 2 giây",
        tag_text="KIỂM THỬ CHẤT LƯỢNG (QA) & MINH CHỨNG THỰC NGHIỆM · THÁI (DATA ENGINEER)"
    )

    card_y = Inches(1.38)
    card_h = Inches(5.40)

    # --------------------------------------------------------------------------
    # CỘT 1: ĐỐI SOÁT SỐ LƯỢNG BẢN GHI QUA CÁC TẦNG (w = 3.70)
    # --------------------------------------------------------------------------
    c1_x = Inches(0.8)
    c1_w = Inches(3.70)
    add_rounded_card(slide, c1_x, card_y, c1_w, card_h, bg_color=C_WHITE, border_color=C_CYAN_ACC, border_pt=1.5)

    # Header Cột 1
    h1 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c1_x, card_y, c1_w, Inches(0.40))
    h1.fill.solid()
    h1.fill.fore_color.rgb = C_CYAN_ACC
    h1.line.color.rgb = C_CYAN_ACC
    p1 = h1.text_frame.paragraphs[0]
    p1.text = "1. ĐỐI SOÁT DỮ LIỆU QUA CÁC TẦNG (RAW -> GOLD)"
    p1.font.name = "Arial"
    p1.font.size = Pt(8.8)
    p1.font.bold = True
    p1.font.color.rgb = C_WHITE
    p1.alignment = PP_ALIGN.CENTER

    tb1 = slide.shapes.add_textbox(c1_x + Inches(0.14), card_y + Inches(0.48), c1_w - Inches(0.28), card_h - Inches(0.56))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_right = tf1.margin_top = tf1.margin_bottom = 0

    c1_contents = [
        ("BẢO TOÀN 100% SỐ LƯỢNG BẢN GHI (0 DÒNG BỊ LOẠI)", [
            "• Listings: 3.208 nguồn -> 3.208 Staging -> 3.208 Silver -> 3.208 Gold (Diff = 0).",
            "• Calendar: 1.170.950 nguồn -> 1.170.950 Staging -> 1.170.950 Gold (Diff = 0).",
            "• Reviews: 46.000 nguồn -> 46.000 Staging -> 46.000 Gold (Diff = 0).",
            "• Neighbourhoods: 55 nguồn -> 55 Staging -> 55 Gold (Diff = 0).",
            "• dim_date (Tạo mới): 6.209 ngày (Bao phủ trọn vẹn từ 2011 đến 2027)."
        ]),
        ("Ý NGHĨA KỸ THUẬT QUAN TRỌNG", [
            "• Không có bản ghi nào bị drop tùy tiện; toàn bộ dữ liệu nghiệp vụ được bảo tồn nguyên trạng.",
            "• Chế độ Re-run (TQ-05): Tái chạy lần 2 trên cùng snapshot không sinh thêm bất kỳ bản ghi trùng nào."
        ]),
        ("PHÂN CHIA TRÁCH NHIỆM BÀN GIAO", [
            "• Bàn giao Gold cho Minh (Task 3.5 & 3.6): Schema DDL khớp 100% tên cột và kiểu dữ liệu MySQL.",
            "• Bàn giao cho Hồng (Task 3.7 & 4.2): Báo cáo cleaning_audit_summary.csv và join_coverage.csv phục vụ nghiệm thu."
        ])
    ]

    is_first = True
    for sec_h, bullets in c1_contents:
        p_sh = tf1.paragraphs[0] if is_first else tf1.add_paragraph()
        is_first = False
        p_sh.text = sec_h
        p_sh.font.name = "Arial"
        p_sh.font.size = Pt(8.2)
        p_sh.font.bold = True
        p_sh.font.color.rgb = C_CYAN_ACC
        p_sh.space_before = Pt(4) if not is_first else Pt(0)
        p_sh.space_after = Pt(2)

        for b in bullets:
            pb = tf1.add_paragraph()
            pb.text = b
            pb.font.name = "Arial"
            pb.font.size = Pt(7.4)
            pb.font.color.rgb = C_NAVY_BODY
            pb.line_spacing = 1.15
            pb.space_after = Pt(2)

    # --------------------------------------------------------------------------
    # CỘT 2: KIỂM TRA QUAN HỆ ĐA BẢNG & ĐỐI SOÁT KPI (w = 3.80)
    # --------------------------------------------------------------------------
    c2_x = Inches(4.76)
    c2_w = Inches(3.80)
    add_rounded_card(slide, c2_x, card_y, c2_w, card_h, bg_color=C_WHITE, border_color=C_EMERALD, border_pt=1.5)

    h2 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c2_x, card_y, c2_w, Inches(0.40))
    h2.fill.solid()
    h2.fill.fore_color.rgb = C_EMERALD
    h2.line.color.rgb = C_EMERALD
    p2 = h2.text_frame.paragraphs[0]
    p2.text = "2. TÍNH TOÀN VẸN THAM CHIẾU (ZERO ORPHAN KEY) & KPI"
    p2.font.name = "Arial"
    p2.font.size = Pt(8.8)
    p2.font.bold = True
    p2.font.color.rgb = C_WHITE
    p2.alignment = PP_ALIGN.CENTER

    tb2 = slide.shapes.add_textbox(c2_x + Inches(0.14), card_y + Inches(0.48), c2_w - Inches(0.28), card_h - Inches(0.56))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_right = tf2.margin_top = tf2.margin_bottom = 0

    c2_contents = [
        ("KIỂM TRA KHÓA NGOẠI MỒ CÔI (ORPHAN KEY CHECK)", [
            "• REL-01 (Calendar -> Listings): 1.170.950 / 1.170.950 dòng khớp -> Match: 100.0% | Orphan: 0 (PASS).",
            "• REL-02 (Reviews -> Listings): 46.000 / 46.000 dòng khớp -> Match: 100.0% | Orphan: 0 (PASS).",
            "• REL-03 (Listings -> Neighbourhoods): 3.208 / 3.208 dòng khớp -> Match: 100.0% | Orphan: 0 (PASS).",
            "• REL-04 (Event Dates -> dim_date): 2.437.108 / 2.437.108 lượt khớp -> Match: 100.0% | Orphan: 0 (PASS)."
        ]),
        ("ĐỐI SOÁT CHỈ TIÊU VỚI CHUẨN BASELINE (100% PARITY)", [
            "• KPI-01: Tổng số Listing duy nhất = 3.208 tin (Chênh lệch: 0).",
            "• KPI-02: Trung vị giá niêm yết SGD = 202.83 SGD (Khớp chuẩn 100%).",
            "• KPI-03: Cơ cấu loại phòng = Private room 56.95% (1.827), Entire home 38.40% (1.232), Hotel 2.59% (83), Shared 2.06% (66).",
            "• KPI-04: Tỷ lệ ngày sẵn có = 76.94% (900.960 đêm) (Chênh lệch: 0).",
            "• KPI-05: Điểm đánh giá bình quân = 4.5394 (Chênh lệch: 0)."
        ]),
        ("KẾT LUẬN KIỂM ĐỊNH", [
            "Toàn bộ quan hệ cha - con đạt tính toàn vẹn tuyệt đối; sẵn sàng cấp nguồn tin cậy cho kho dữ liệu và dashboard Power BI."
        ])
    ]

    is_first = True
    for sec_h, bullets in c2_contents:
        p_sh = tf2.paragraphs[0] if is_first else tf2.add_paragraph()
        is_first = False
        p_sh.text = sec_h
        p_sh.font.name = "Arial"
        p_sh.font.size = Pt(8.2)
        p_sh.font.bold = True
        p_sh.font.color.rgb = C_EMERALD
        p_sh.space_before = Pt(4) if not is_first else Pt(0)
        p_sh.space_after = Pt(2)

        for b in bullets:
            pb = tf2.add_paragraph()
            pb.text = b
            pb.font.name = "Arial"
            pb.font.size = Pt(7.4)
            pb.font.color.rgb = C_NAVY_BODY
            pb.line_spacing = 1.15
            pb.space_after = Pt(2)

    # --------------------------------------------------------------------------
    # CỘT 3: MINH CHỨNG CHẠY THẬT & HƯỚNG DẪN LIVE DEMO (w = 3.733)
    # --------------------------------------------------------------------------
    c3_x = Inches(8.80)
    c3_w = Inches(3.733)
    add_rounded_card(slide, c3_x, card_y, c3_w, card_h, bg_color=C_WHITE, border_color=C_PURPLE, border_pt=1.5)

    h3 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c3_x, card_y, c3_w, Inches(0.40))
    h3.fill.solid()
    h3.fill.fore_color.rgb = C_PURPLE
    h3.line.color.rgb = C_PURPLE
    p3 = h3.text_frame.paragraphs[0]
    p3.text = "3. MINH CHỨNG THỰC NGHIỆM & HƯỚNG DẪN LIVE DEMO"
    p3.font.name = "Arial"
    p3.font.size = Pt(8.8)
    p3.font.bold = True
    p3.font.color.rgb = C_WHITE
    p3.alignment = PP_ALIGN.CENTER

    tb3 = slide.shapes.add_textbox(c3_x + Inches(0.14), card_y + Inches(0.48), c3_w - Inches(0.28), card_h - Inches(0.56))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    tf3.margin_left = tf3.margin_right = tf3.margin_top = tf3.margin_bottom = 0

    c3_contents = [
        ("HIỆU NĂNG THỰC TẾ TRÊN 1.17M DÒNG (42.67 GIÂY)", [
            "• Ingest vào Staging: 8.29s (Chunking 100k dòng an toàn).",
            "• Làm sạch Silver: 14.20s (Vectorized NumPy/Pandas).",
            "• Ánh xạ Gold & Kiểm tra: 20.18s (Tạo Star Schema & Orphan check).",
            "-> Tổng thời gian toàn trình: 42.67 giây (Rất nhanh và ổn định)."
        ]),
        ("KẾT QUẢ BỘ KIỂM THỬ TỰ ĐỘNG (QA TEST SUITE)", [
            "• Phân hệ ETL của Thái: 172 / 172 checks PASS (0 FAIL, 0 ERROR).",
            "• Tổng thể dự án: 321 checks PASS, 1 INFO, 0 FAIL.",
            "• 5 Test Cases hồi quy chuyên sâu trong test_etl_regressions.py: PASS 100% trong 0.65 giây."
        ]),
        ("HƯỚNG DẪN CHẠY DEMO TẠI CHỖ (KHI VẤN ĐÁP)", [
            "1. Chạy Demo mẫu nhanh (2 giây, 500 dòng/nguồn):\n   python scripts/demo_etl_pipeline.py --sample 500\n   (Hoặc click đúp file scripts/run_demo.ps1)",
            "2. Chạy Demo toàn bộ 1.17M dòng thật (~42 giây):\n   python scripts/demo_etl_pipeline.py --full",
            "3. Chạy bộ kiểm thử hồi quy tự động (~0.65 giây):\n   python -m unittest tests/test_etl_regressions.py"
        ])
    ]

    is_first = True
    for sec_h, bullets in c3_contents:
        p_sh = tf3.paragraphs[0] if is_first else tf3.add_paragraph()
        is_first = False
        p_sh.text = sec_h
        p_sh.font.name = "Arial"
        p_sh.font.size = Pt(8.2)
        p_sh.font.bold = True
        p_sh.font.color.rgb = C_PURPLE
        p_sh.space_before = Pt(4) if not is_first else Pt(0)
        p_sh.space_after = Pt(2)

        for b in bullets:
            pb = tf3.add_paragraph()
            pb.text = b
            pb.font.name = "Arial"
            pb.font.size = Pt(7.4)
            pb.font.color.rgb = C_NAVY_BODY
            pb.line_spacing = 1.15
            pb.space_after = Pt(2)

    add_footer(slide, 2, 2)


# ==============================================================================
# HÀM CHÍNH
# ==============================================================================
def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    print("Building 2-slide summary presentation...")
    create_slide_1(prs)
    create_slide_2(prs)

    # Lưu cả vào file chuyên biệt và file chính của task 5.4
    prs.save(OUTPUT_PPTX_2SLIDES)
    print(f"[OK] Saved 2-slide deck to: {OUTPUT_PPTX_2SLIDES}")

    prs.save(OUTPUT_PPTX_MAIN)
    print(f"[OK] Overwrote main presentation: {OUTPUT_PPTX_MAIN}")


if __name__ == "__main__":
    main()
