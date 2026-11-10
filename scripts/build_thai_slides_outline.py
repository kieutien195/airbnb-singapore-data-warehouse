"""
build_thai_slides_outline.py
----------------------------
Tạo tệp PowerPoint (.pptx) chuẩn 16:9 cho 4 trang slide thuộc trách nhiệm của THÁI:
- Trang 09: Nhóm giữ, chuẩn hóa hoặc cách ly dữ liệu theo từng quy tắc
- Trang 10: Kiểm tra đơn vị tiền SGD & phân giải giá niêm yết
- Trang 12: Một lần chạy ETL tạo ra các đầu ra truy vết được
- Trang 32: Phụ lục B · Tái lập và kiểm thử

Tuân thủ nghiêm ngặt yêu cầu:
1) Đặt kết luận ngay ở tiêu đề.
2) Dùng đối chiếu hoặc số lớn để giải thích câu hỏi trên mỗi trang.
3) Bảng và sơ đồ đối soát đọc được làm bằng chứng; không dán code dài.
4) Dải điều hướng dùng chung và dòng chân trang chuẩn.
5) Tuyệt đối kiểm soát bounding box, KHÔNG BỊ ĐÈ CHỮ.
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
OUTPUT_PPTX_THAI = SLIDES_DIR / "thai_slides_09_10_12_32.pptx"
OUTPUT_PPTX_MAIN = SLIDES_DIR / "5.4_slide_etl_pipeline_and_tests.pptx"

# Bảng màu thiết kế chuẩn Corporate
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
C_TH_BG     = RGBColor(224, 242, 254)   # #E0F2FE (Nền Header Bảng - Light Cyan)


def set_slide_background(slide):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = C_BG_SLATE


def add_common_nav_header(slide, page_str: str, nav_section: str, title_text: str, subtitle_text: str):
    """Dải điều hướng dùng chung & Tiêu đề chứa kết luận lớn"""
    # 1. Dải điều hướng (Breadcrumb)
    tb_nav = slide.shapes.add_textbox(Inches(0.8), Inches(0.32), Inches(11.733), Inches(0.24))
    tf_nav = tb_nav.text_frame
    tf_nav.word_wrap = True
    tf_nav.margin_left = tf_nav.margin_top = tf_nav.margin_right = tf_nav.margin_bottom = 0
    p_nav = tf_nav.paragraphs[0]
    p_nav.text = f"{nav_section.upper()} · {page_str.upper()} | PHỤ TRÁCH: THÁI (DATA ENGINEER / ETL)"
    p_nav.font.name = "Arial"
    p_nav.font.size = Pt(9)
    p_nav.font.bold = True
    p_nav.font.color.rgb = C_CYAN_ACC

    # 2. Tiêu đề kết luận lớn
    tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.56), Inches(11.733), Inches(0.44))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.name = "Arial"
    p_title.font.size = Pt(17.5)
    p_title.font.bold = True
    p_title.font.color.rgb = C_NAVY_DARK

    # 3. Phụ đề tóm tắt bối cảnh
    tb_sub = slide.shapes.add_textbox(Inches(0.8), Inches(1.02), Inches(11.733), Inches(0.26))
    tf_sub = tb_sub.text_frame
    tf_sub.word_wrap = True
    tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = subtitle_text
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(9.5)
    p_sub.font.color.rgb = C_SLATE_MUT

    # Đường kẻ ngăn cách dải điều hướng
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.32), Inches(11.733), Inches(0.012))
    line.fill.solid()
    line.fill.fore_color.rgb = C_BORDER
    line.line.color.rgb = C_BORDER


def add_common_footer(slide, page_num_str: str, source_str: str):
    """Chân trang dùng chung ghi nguồn, snapshot, commit và số trang"""
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.92), Inches(11.733), Inches(0.012))
    line.fill.solid()
    line.fill.fore_color.rgb = C_BORDER
    line.line.color.rgb = C_BORDER

    tb_f = slide.shapes.add_textbox(Inches(0.8), Inches(6.96), Inches(10.2), Inches(0.3))
    tf_f = tb_f.text_frame
    tf_f.margin_left = tf_f.margin_top = tf_f.margin_right = tf_f.margin_bottom = 0
    p_f = tf_f.paragraphs[0]
    p_f.text = f"{source_str} | Snapshot: 2026-09-23 | Đồ án Nhà kho dữ liệu Airbnb Singapore 2026"
    p_f.font.name = "Arial"
    p_f.font.size = Pt(8.5)
    p_f.font.color.rgb = C_SLATE_MUT

    tb_p = slide.shapes.add_textbox(Inches(11.0), Inches(6.96), Inches(1.533), Inches(0.3))
    tf_p = tb_p.text_frame
    tf_p.margin_left = tf_p.margin_right = tf_p.margin_top = tf_p.margin_bottom = 0
    p_p = tf_p.paragraphs[0]
    p_p.text = f"Trang {page_num_str}"
    p_p.alignment = PP_ALIGN.RIGHT
    p_p.font.name = "Arial"
    p_p.font.size = Pt(8.5)
    p_p.font.bold = True
    p_p.font.color.rgb = C_CYAN_ACC


def add_rounded_card(slide, left, top, width, height, bg_color=C_WHITE, border_color=C_BORDER, border_pt=1):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(border_pt)
    return card


def add_stat_card(slide, left, top, width, height, main_stat: str, sub_label: str, col=C_CYAN_ACC):
    add_rounded_card(slide, left, top, width, height, bg_color=C_WHITE, border_color=col, border_pt=1.2)
    tb = slide.shapes.add_textbox(left + Inches(0.12), top + Inches(0.08), width - Inches(0.24), height - Inches(0.16))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p1 = tf.paragraphs[0]
    p1.text = main_stat
    p1.font.name = "Arial"
    p1.font.size = Pt(17)
    p1.font.bold = True
    p1.font.color.rgb = col
    p2 = tf.add_paragraph()
    p2.text = sub_label
    p2.font.name = "Arial"
    p2.font.size = Pt(8.5)
    p2.font.color.rgb = C_NAVY_BODY


# ==============================================================================
# 1. TRANG 09: MA TRẬN QUY TẮC LÀM SẠCH & XỬ LÝ LỖI DỮ LIỆU
# ==============================================================================
def create_page_09(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)

    add_common_nav_header(
        slide,
        page_str="Trang 09 / 33",
        nav_section="B. Dữ liệu và tiền xử lý",
        title_text="BẢO TOÀN 100% FACT: KHÔNG LOẠI BẢN GHI NGOÀI Ý MUỐN, CHUẨN HÓA 4 NHÓM QUY TẮC",
        subtitle_text="Ma trận lỗi -> Quy tắc xử lý -> Dữ liệu đầu ra -> Số dòng tác động và phân biệt rõ số dòng bị loại"
    )

    # 3 Thẻ thống kê nhanh trên cùng
    add_stat_card(slide, Inches(0.8), Inches(1.42), Inches(3.7), Inches(0.72), "3.208 / 3.208", "Listings sạch (2.725 giá SGD, giữ 483 NULL)", C_CYAN_ACC)
    add_stat_card(slide, Inches(4.8), Inches(1.42), Inches(3.7), Inches(0.72), "1.170.950", "Calendar sạch (76.94% ngày mở lịch, 0 loại)", C_EMERALD)
    add_stat_card(slide, Inches(8.8), Inches(1.42), Inches(3.733), Inches(0.72), "0 DÒNG BỊ LOẠI", "Không xóa oan bản ghi; 100% facts được bảo toàn", C_PURPLE)

    # Bảng Ma trận đối soát tiền xử lý
    table_shape = slide.shapes.add_table(6, 5, Inches(0.8), Inches(2.26), Inches(11.733), Inches(3.40))
    table = table_shape.table
    table.columns[0].width = Inches(2.10)
    table.columns[1].width = Inches(3.90)
    table.columns[2].width = Inches(2.20)
    table.columns[3].width = Inches(1.80)
    table.columns[4].width = Inches(1.733)

    headers = ["Nhóm lỗi / Dữ liệu", "Quy tắc tiền xử lý & Chuẩn hóa", "Dữ liệu đầu ra", "Số dòng tác động", "Bản ghi bị loại"]
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY_DARK
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.name = "Arial"
        p.font.size = Pt(8.5)
        p.font.bold = True
        p.font.color.rgb = C_WHITE
        p.alignment = PP_ALIGN.CENTER

    matrix_data = [
        ("Giá tiền & Tiền tệ\n(listings.price)", "Regex bóc tách '$', ',' -> ép DECIMAL(10,2).\nXác minh currency='SGD' từ JSON raw quote.", "Giá SGD chuẩn\n(2.725 dòng hợp lệ)", "2.725 dòng cập nhật\n(Median 202.83 SGD)", "0 dòng\n(483 NULL giữ nguyên)"),
        ("Mốc thời gian\n(Calendar, Reviews)", "Ép kiểu DATE chuẩn ISO 8601 (YYYY-MM-DD).\nSinh surrogate key date_sk (YYYYMMDD).", "Trục ngày chuẩn\n(Liên kết dim_date)", "1.170.950 (Calendar)\n46.000 (Reviews)", "0 dòng\n(100% hợp lệ ISO)"),
        ("Trạng thái lịch\n(calendar.available)", "Vectorized mapping 't'/'f' -> 1/0 (TINYINT).\nĐo trạng thái lịch quan sát, không suy ra booking.", "is_available\n(TINYINT)", "900.960 mở (76.94%)\n269.990 đóng", "0 dòng\n(Khớp baseline KPI-04)"),
        ("Khóa trùng lặp (Grain)\n(Listings, Reviews)", "Khử trùng theo đúng grain từng bảng: Listings (id),\nReviews (listing_id, review_id, snapshot_date).", "Grain đơn nhất\n(Không xóa nhầm)", "3.208 listings\n46.000 reviews", "0 trùng phát sinh\n(Không mất dữ liệu)"),
        ("Khóa ngoại tham chiếu\n(Calendar/Rev -> List)", "Kiểm tra listing_id trong Calendar & Reviews\ntham chiếu đến dim_listing (Snapshot 2026-09-23).", "Quan hệ toàn vẹn\n(0 Orphan Key)", "1.170.950 (Cal)\n46.000 (Rev)", "0 orphan\n(100.0% độ phủ khớp)")
    ]

    for i, row in enumerate(matrix_data):
        bg_row = C_WHITE if i % 2 == 0 else RGBColor(241, 245, 249)
        for j, text in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg_row
            cell.text_frame.word_wrap = True
            cell.text_frame.margin_left = cell.text_frame.margin_right = Inches(0.06)
            cell.text_frame.margin_top = cell.text_frame.margin_bottom = Inches(0.04)
            p = cell.text_frame.paragraphs[0]
            p.text = text
            p.font.name = "Arial"
            p.font.size = Pt(8.0)
            p.font.color.rgb = C_NAVY_BODY
            if j >= 3:
                p.alignment = PP_ALIGN.CENTER
                p.font.bold = True
                if j == 4:
                    p.font.color.rgb = C_EMERALD

    # Hộp ghi chú kỹ thuật ở đáy
    callout = add_rounded_card(slide, Inches(0.8), Inches(5.82), Inches(11.733), Inches(0.96), bg_color=RGBColor(224, 242, 254), border_color=C_CYAN_ACC, border_pt=1)
    tb_co = slide.shapes.add_textbox(Inches(0.95), Inches(5.88), Inches(11.433), Inches(0.84))
    tf_co = tb_co.text_frame
    tf_co.word_wrap = True
    tf_co.margin_left = tf_co.margin_right = tf_co.margin_top = tf_co.margin_bottom = 0
    p_co1 = tf_co.paragraphs[0]
    p_co1.text = "NGUYÊN TẮC BẢO TOÀN DỮ LIỆU NGHIỆP VỤ (BUSINESS INTEGRITY):"
    p_co1.font.name = "Arial"
    p_co1.font.size = Pt(8.5)
    p_co1.font.bold = True
    p_co1.font.color.rgb = C_CYAN_ACC

    p_co2 = tf_co.add_paragraph()
    p_co2.text = (
        "• 483 tin thiếu giá và 1.369 tin thiếu điểm đánh giá được GIỮ NGUYÊN NULL, tuyệt đối không thế bằng 0 (tránh kéo tụt trung vị và làm sai lệch phân phối).\n"
        "• 134 quan sát giá ngoài ngưỡng IQR được BẢO TOÀN 100% vì phản ánh thực tế phân khúc cao cấp (biệt thự/penthouse). Pipeline ghi log rõ lý do, không tự ý loại bỏ."
    )
    p_co2.font.name = "Arial"
    p_co2.font.size = Pt(8.0)
    p_co2.font.color.rgb = C_NAVY_BODY
    p_co2.line_spacing = 1.15

    add_common_footer(slide, "09", "Nguồn: data/raw/ | Audit log: outputs/cleaning_audit_summary.csv")


# ==============================================================================
# 2. TRANG 10: XÁC MINH TIỀN TỆ SGD & PHÂN GIẢI GIÁ NIÊM YẾT
# ==============================================================================
def create_page_10(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)

    add_common_nav_header(
        slide,
        page_str="Trang 10 / 33",
        nav_section="B. Dữ liệu và tiền xử lý",
        title_text="KIỂM ĐỊNH 2 LỚP XÁC MINH 2.725 GIÁ SGD HỢP LỆ; TRUNG VỊ ĐẠT CHUẨN 202,83 SGD",
        subtitle_text="Bóc tách chuỗi giá, đối chiếu mã tiền tệ từ JSON thô, bảo toàn 483 NULL và giữ nguyên 134 ngoại lai IQR"
    )

    # 3 Thẻ số lớn trên cùng
    add_stat_card(slide, Inches(0.8), Inches(1.42), Inches(3.7), Inches(0.72), "2.725 (84,94%)", "Tin có giá SGD hợp lệ (Đủ điều kiện tính KPI-02)", C_CYAN_ACC)
    add_stat_card(slide, Inches(4.8), Inches(1.42), Inches(3.7), Inches(0.72), "202,83 SGD", "Trung vị giá niêm yết (Khớp 100% baseline KPI-02)", C_EMERALD)
    add_stat_card(slide, Inches(8.8), Inches(1.42), Inches(3.733), Inches(0.72), "483 (15,06%)", "Tin thiếu giá (Giữ NULL, không gán bừa = 0)", C_AMBER)

    # 2 Cột so sánh chi tiết
    col_w = Inches(5.72)
    box_y = Inches(2.26)
    box_h = Inches(4.52)

    # CỘT TRÁI: CƠ CHẾ KIỂM ĐỊNH 2 LỚP & VÍ DỤ MINH HỌA CỤ THỂ
    add_rounded_card(slide, Inches(0.8), box_y, col_w, box_h, bg_color=C_WHITE, border_color=C_CYAN_ACC, border_pt=1.5)
    tb_l = slide.shapes.add_textbox(Inches(0.96), box_y + Inches(0.12), col_w - Inches(0.32), box_h - Inches(0.24))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True
    tf_l.margin_left = tf_l.margin_right = tf_l.margin_top = tf_l.margin_bottom = 0

    p = tf_l.paragraphs[0]
    p.text = "CƠ CHẾ KIỂM ĐỊNH TIỀN TỆ 2 LỚP & VÍ DỤ CỤ THỂ"
    p.font.name = "Arial"
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = C_CYAN_ACC
    p.space_after = Pt(4)

    left_points = [
        ("LỚP 1 · BÓC TÁCH CHUỖI GIÁ NIÊM YẾT (RAW STRING)",
         "• Chuỗi gốc: '$1,250.00' -> loại bỏ regex ký tự '$', dấu phẩy, khoảng trắng.\n• Ép kiểu thành số thực hữu hạn DECIMAL(10,2) chính xác."),
        ("LỚP 2 · ĐỐI CHIẾU MÃ TIỀN TỆ TỪ JSON THÔ (PRICE QUOTE)",
         "• Cột 'price_quote_raw' chứa cấu trúc: {'currency': 'SGD', ...}.\n• Xác lập cờ is_price_sgd_verified = 1 khi mã tiền đúng 'SGD'."),
        ("VÍ DỤ ĐẠT CHUẨN (HỢP LỆ VÀO KPI-02)",
         "• Listing ID: 71609 | Giá thô: '$150.00' -> Giá parse: 150.00\n• JSON currency: 'SGD' -> is_price_sgd_verified = 1 -> TÍNH VÀO KPI."),
        ("VÍ DỤ BỊ LOẠI KHỎI KPI (BẢO TOÀN NULL)",
         "• Listing ID: 27534720 | Giá thô: NULL -> Giá parse: NaN\n• JSON currency: NULL -> is_price_sgd_verified = 0 -> GIỮ NGUYÊN NULL.\n• Ý nghĩa: Tránh gán giá 0 làm sai lệch nghiêm trọng phân vị giá.")
    ]

    for h, b in left_points:
        ph = tf_l.add_paragraph()
        ph.text = h
        ph.font.name = "Arial"
        ph.font.size = Pt(8.5)
        ph.font.bold = True
        ph.font.color.rgb = C_NAVY_DARK
        ph.space_before = Pt(4)

        pb = tf_l.add_paragraph()
        pb.text = b
        pb.font.name = "Arial"
        pb.font.size = Pt(7.8)
        pb.font.color.rgb = C_NAVY_BODY
        pb.line_spacing = 1.15

    # CỘT PHẢI: BẢNG PHÂN BỐ & QUY TẮC BẢO TOÀN OUTLIERS
    add_rounded_card(slide, Inches(6.81), box_y, col_w, box_h, bg_color=C_WHITE, border_color=C_EMERALD, border_pt=1.5)
    tb_r = slide.shapes.add_textbox(Inches(6.97), box_y + Inches(0.12), col_w - Inches(0.32), box_h - Inches(0.24))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    tf_r.margin_left = tf_r.margin_right = tf_r.margin_top = tf_r.margin_bottom = 0

    p = tf_r.paragraphs[0]
    p.text = "ĐỐI SOÁT PHÂN PHỐI GIÁ & BẢO TOÀN NGOẠI LAI (OUTLIERS)"
    p.font.name = "Arial"
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p.space_after = Pt(4)

    right_points = [
        ("ĐỐI SOÁT CHẶT CHẼ VỚI BASELINE KPI-02",
         "• Trung vị tính toán: 202.83 SGD | Chuẩn Baseline: 202.83 SGD (Khớp 100%).\n• Mẫu số tính toán: Đúng 2.725 tin có giá SGD hợp lệ (loại trừ 483 NULL)."),
        ("TÔN TRỌNG PHÂN PHỐI 134 QUAN SÁT NGOÀI NGƯỠNG IQR",
         "• 134 tin đăng có giá cực cao (> Q3 + 1.5*IQR) được BẢO TOÀN 100%.\n• Không xóa outlier vì đây là tin đăng biệt thự, penthouse cao cấp thực tế.\n• Dùng trung vị thay vì trung bình để tránh ảnh hưởng méo mó từ outlier."),
        ("SỬA LỖI KIỂU DỮ LIỆU 'ACCOMMODATES' (SỨC CHỨA)",
         "• Lưu trữ kiểu INT UNSIGNED (phạm vi từ 1 đến 16 người).\n• Khắc phục hoàn toàn lỗi parse nhầm sang DATE trong các bản nháp trước."),
        ("ĐỘ CHÍNH XÁC SỐ HỌC (DECIMAL PRECISION)",
         "• Số đêm minimum_nights_avg_ntm giữ nguyên phần thập phân.\n• Toàn bộ giá tiền lưu trữ kiểu DECIMAL(10,2) trong MySQL, bảo toàn từng xu.")
    ]

    for h, b in right_points:
        ph = tf_r.add_paragraph()
        ph.text = h
        ph.font.name = "Arial"
        ph.font.size = Pt(8.5)
        ph.font.bold = True
        ph.font.color.rgb = C_NAVY_DARK
        ph.space_before = Pt(4)

        pb = tf_r.add_paragraph()
        pb.text = b
        pb.font.name = "Arial"
        pb.font.size = Pt(7.8)
        pb.font.color.rgb = C_NAVY_BODY
        pb.line_spacing = 1.15

    add_common_footer(slide, "10", "Nguồn: listings.csv.gz | Baseline: docs/kpi_definitions.md (KPI-02)")


# ==============================================================================
# 3. TRANG 12: QUY TRÌNH ETL TOÀN TRÌNH & ĐẦU RA TRUY VẾT
# ==============================================================================
def create_page_12(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)

    add_common_nav_header(
        slide,
        page_str="Trang 12 / 33",
        nav_section="D. Triển khai và kiểm chứng",
        title_text="MỘT LẦN CHẠY ETL TẠO ĐẦU RA TRUY VẾT 100%, HOÀN TẤT TOÀN BỘ 3 TẦNG TRONG 42,67 GIÂY",
        subtitle_text="Bảng stage, script thực thi, đầu vào, đầu ra, thời gian chạy và cơ chế khả lặp (Idempotency TQ-05)"
    )

    # 4 Thẻ số thời gian chạy thực tế
    add_stat_card(slide, Inches(0.8), Inches(1.42), Inches(2.75), Inches(0.72), "8,29 giây", "Ingestion (Chunking 100k)", C_CYAN_ACC)
    add_stat_card(slide, Inches(3.78), Inches(1.42), Inches(2.75), Inches(0.72), "14,20 giây", "Cleaning (Vectorized Silver)", C_EMERALD)
    add_stat_card(slide, Inches(6.76), Inches(1.42), Inches(2.75), Inches(0.72), "20,18 giây", "Transformation (Star Schema)", C_PURPLE)
    add_stat_card(slide, Inches(9.74), Inches(1.42), Inches(2.793), Inches(0.72), "42,67 giây", "Tổng thời gian toàn trình (1.17M dòng)", C_AMBER)

    # Khung chính chia 2 phần: Bảng truy vết (Trái) & Đoạn Log thật (Phải)
    box_y = Inches(2.26)
    box_h = Inches(4.52)

    # TRÁI: BẢNG TRUY VẾT CÔNG ĐOẠN (w = 6.80)
    add_rounded_card(slide, Inches(0.8), box_y, Inches(6.80), box_h, bg_color=C_WHITE, border_color=C_CYAN_ACC, border_pt=1.5)
    tb_title = slide.shapes.add_textbox(Inches(0.95), box_y + Inches(0.10), Inches(6.50), Inches(0.30))
    tf_t = tb_title.text_frame
    p = tf_t.paragraphs[0]
    p.text = "BẢNG TRUY VẾT QUY TRÌNH ETL (STAGE TRACEABILITY)"
    p.font.name = "Arial"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = C_CYAN_ACC

    # Bảng 4 dòng
    t_shape = slide.shapes.add_table(5, 4, Inches(0.95), box_y + Inches(0.44), Inches(6.50), Inches(2.55))
    t = t_shape.table
    t.columns[0].width = Inches(1.10)
    t.columns[1].width = Inches(1.40)
    t.columns[2].width = Inches(1.90)
    t.columns[3].width = Inches(2.10)

    t_headers = ["Chặng", "Script", "Đầu vào (Input)", "Đầu ra (Output)"]
    for j, h in enumerate(t_headers):
        cell = t.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY_DARK
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.name = "Arial"
        p.font.size = Pt(8.0)
        p.font.bold = True
        p.font.color.rgb = C_WHITE
        p.alignment = PP_ALIGN.CENTER

    t_rows = [
        ("1. Ingest", "etl/ingest.py", "4 file data/raw/*.csv.gz\n(1.17M dòng)", "stg_*.csv & MySQL Staging\nLog: logs/ingest.log"),
        ("2. Clean", "etl/clean.py", "data/processed/staging/\n(Raw text fields)", "silver_*.csv (Chuẩn kiểu)\nAudit: cleaning_audit_summary"),
        ("3. Trans", "etl/transform.py", "data/processed/silver/\n(Dữ liệu sạch)", "gold/*.csv (Star Schema)\nCoverage: join_coverage.csv"),
        ("Toàn trình", "etl/run_pipeline.py", "Tự động hóa 3 chặng", "100% đầu ra sẵn sàng nạp\nThời gian: 42.67 giây")
    ]
    for i, r in enumerate(t_rows):
        bg_col = C_WHITE if i % 2 == 0 else RGBColor(241, 245, 249)
        for j, text in enumerate(r):
            cell = t.cell(i + 1, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg_col
            cell.text_frame.word_wrap = True
            cell.text_frame.margin_left = cell.text_frame.margin_right = Inches(0.05)
            cell.text_frame.margin_top = cell.text_frame.margin_bottom = Inches(0.04)
            p = cell.text_frame.paragraphs[0]
            p.text = text
            p.font.name = "Arial"
            p.font.size = Pt(7.5)
            p.font.color.rgb = C_NAVY_BODY

    # Dưới bảng: Cơ sở lý thuyết môn học
    tb_theory = slide.shapes.add_textbox(Inches(0.95), box_y + Inches(3.08), Inches(6.50), Inches(1.30))
    tf_th = tb_theory.text_frame
    tf_th.word_wrap = True
    tf_th.margin_left = tf_th.margin_right = tf_th.margin_top = tf_th.margin_bottom = 0
    pth1 = tf_th.paragraphs[0]
    pth1.text = "CƠ SỞ LÝ THUYẾT & NGUYÊN TẮC VẬN DỤNG (CHƯƠNG 3 & 4):"
    pth1.font.name = "Arial"
    pth1.font.size = Pt(8.5)
    pth1.font.bold = True
    pth1.font.color.rgb = C_NAVY_DARK

    pth2 = tf_th.add_paragraph()
    pth2.text = (
        "• Vận dụng Chương 3 (Tích hợp dữ liệu): Thiết lập cơ chế Idempotency (TQ-05) - xóa partition theo snapshot_date trước khi nạp lại trong một transaction; chạy lại lần 2 không bao giờ nhân đôi bản ghi.\n"
        "• Vận dụng Chương 4 (Tiền xử lý): Vector hóa hoàn toàn thao tác biến đổi trên 1.17M dòng; tuyệt đối không dùng vòng lặp chậm; nghiêm cấm JOIN trực tiếp Calendar x Reviews để loại trừ rủi ro fan-out."
    )
    pth2.font.name = "Arial"
    pth2.font.size = Pt(7.8)
    pth2.font.color.rgb = C_NAVY_BODY
    pth2.line_spacing = 1.15

    # PHẢI: ĐOẠN LOG THỰC THI THẬT (TERMINAL CODE SNIPPET) (w = 4.65)
    add_rounded_card(slide, Inches(7.88), box_y, Inches(4.653), box_h, bg_color=C_NAVY_DARK, border_color=C_CYAN_ACC, border_pt=1.5)
    tb_log = slide.shapes.add_textbox(Inches(8.05), box_y + Inches(0.12), Inches(4.313), box_h - Inches(0.24))
    tf_log = tb_log.text_frame
    tf_log.word_wrap = True
    tf_log.margin_left = tf_log.margin_right = tf_log.margin_top = tf_log.margin_bottom = 0

    plog_title = tf_log.paragraphs[0]
    plog_title.text = "TRÍCH XUẤT LOG CHẠY THẬT (LOGS/INGEST.LOG)"
    plog_title.font.name = "Consolas"
    plog_title.font.size = Pt(8.5)
    plog_title.font.bold = True
    plog_title.font.color.rgb = RGBColor(56, 189, 248)
    plog_title.space_after = Pt(4)

    terminal_lines = [
        "[INFO] Snapshot Date: 2026-09-23",
        "[INFO] Idempotency: Partition cleaned successfully",
        "[INFO] Ingest listings     -> 3,208 rows   (0.24s)",
        "[INFO] Ingest calendar     -> 1,170,950    (7.41s)",
        "[INFO] Ingest reviews      -> 46,000 rows  (0.62s)",
        "[INFO] Ingest neighbours   -> 55 rows      (0.02s)",
        "[INFO] Ingestion Completed: 100% SUCCESS (8.29s)",
        "--------------------------------------------------",
        "[INFO] Clean Listings: 2,725 SGD valid | 483 NULLs",
        "[INFO] Clean Calendar: 76.94% available ratio",
        "[INFO] Clean Reviews : Grain verified (0 dup)",
        "[INFO] Cleaning Completed: 0 REJECTED (14.20s)",
        "--------------------------------------------------",
        "[INFO] Transform Star Schema: 3 Dim + 3 Fact",
        "[INFO] REL-01 Calendar->List: 100.0% [0 ORPHAN]",
        "[INFO] REL-02 Reviews ->List: 100.0% [0 ORPHAN]",
        "[INFO] REL-03 List ->Neighb : 100.0% [0 ORPHAN]",
        "[INFO] REL-04 Dates->dim_date: 100.0% [0 ORPHAN]",
        "[SUCCESS] PIPELINE FINISHED IN 42.67 SECONDS!"
    ]
    for tl in terminal_lines:
        p_line = tf_log.add_paragraph()
        p_line.text = tl
        p_line.font.name = "Consolas"
        p_line.font.size = Pt(7.2)
        if "SUCCESS" in tl or "[0 ORPHAN]" in tl:
            p_line.font.color.rgb = RGBColor(74, 222, 128)
            p_line.font.bold = True
        elif "---" in tl:
            p_line.font.color.rgb = RGBColor(148, 163, 184)
        else:
            p_line.font.color.rgb = RGBColor(226, 232, 240)
        p_line.line_spacing = 1.15

    add_common_footer(slide, "12", "Mã nguồn: etl/ | Log thực tế: logs/ingest.log & outputs/join_coverage.csv")


# ==============================================================================
# 4. TRANG 32: PHỤ LỤC B · TÁI LẬP VÀ KIỂM THỬ
# ==============================================================================
def create_page_32(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide)

    add_common_nav_header(
        slide,
        page_str="Trang 32 / 33",
        nav_section="F. Phụ lục và trang cuối",
        title_text="PHỤ LỤC B: MÔI TRƯỜNG TÁI LẬP ĐỘC LẬP & BỘ TEST TỰ ĐỘNG ĐẠT 172/172 PASS",
        subtitle_text="Đặc tả môi trường, commit Git, đường dẫn log/kết quả kiểm toán và kịch bản demo 1–2 phút tại chỗ"
    )

    box_y = Inches(1.42)
    box_h = Inches(5.36)
    col_w = Inches(3.70)
    gap_w = Inches(0.316)

    # CỘT 1: ĐẶC TẢ MÔI TRƯỜNG & PHIÊN BẢN HỆ THỐNG
    add_rounded_card(slide, Inches(0.8), box_y, col_w, box_h, bg_color=C_WHITE, border_color=C_CYAN_ACC, border_pt=1.5)
    tb1 = slide.shapes.add_textbox(Inches(0.95), box_y + Inches(0.12), col_w - Inches(0.30), box_h - Inches(0.24))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_right = tf1.margin_top = tf1.margin_bottom = 0

    p = tf1.paragraphs[0]
    p.text = "1. MÔI TRƯỜNG & PHIÊN BẢN HỆ THỐNG"
    p.font.name = "Arial"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = C_CYAN_ACC
    p.space_after = Pt(4)

    env_items = [
        ("PHIÊN BẢN PHẦN MỀM",
         "• Python: 3.12 (Virtualenv cô lập tại .venv).\n• Pandas 2.2, NumPy 1.26, SQLAlchemy 2.0, PyMySQL 1.1, python-dotenv 1.0.\n• MySQL Server 8.0 (charset: utf8mb4)."),
        ("QUẢN LÝ MÃ NGUỒN GIT",
         "• Branch: feat/task-5.4-slide-etl-pipeline-and-tests\n• Author: thaiyaa <thainak24406h@st.uel.edu.vn>\n• Repo: github.com/kieutien195/airbnb-singapore-data-warehouse"),
        ("BẢO MẬT CREDENTIALS",
         "• Toàn bộ tài khoản/mật khẩu nạp qua file .env.\n• File .env.example mẫu cho nhóm tái lập.\n• Tuyệt đối KHÔNG commit mật khẩu lên Git."),
        ("TÀI NGUYÊN KIỂM TOÁN LƯU TRỮ",
         "• Báo cáo làm sạch: outputs/cleaning_audit_summary.csv\n• Báo cáo khớp khóa: outputs/join_coverage.csv\n• Log chi tiết: logs/ingest.log, logs/clean.log")
    ]
    for h, b in env_items:
        ph = tf1.add_paragraph()
        ph.text = h
        ph.font.name = "Arial"
        ph.font.size = Pt(8.2)
        ph.font.bold = True
        ph.font.color.rgb = C_NAVY_DARK
        ph.space_before = Pt(3)

        pb = tf1.add_paragraph()
        pb.text = b
        pb.font.name = "Arial"
        pb.font.size = Pt(7.4)
        pb.font.color.rgb = C_NAVY_BODY
        pb.line_spacing = 1.15

    # CỘT 2: BỘ TEST TỰ ĐỘNG & ĐỐI SOÁT KHÓA (0 ORPHAN)
    c2_x = Inches(0.8) + col_w + gap_w
    add_rounded_card(slide, c2_x, box_y, col_w, box_h, bg_color=C_WHITE, border_color=C_EMERALD, border_pt=1.5)
    tb2 = slide.shapes.add_textbox(c2_x + Inches(0.15), box_y + Inches(0.12), col_w - Inches(0.30), box_h - Inches(0.24))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_right = tf2.margin_top = tf2.margin_bottom = 0

    p = tf2.paragraphs[0]
    p.text = "2. KIỂM THỬ HỒI QUY & CHẤT LƯỢNG (QA)"
    p.font.name = "Arial"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = C_EMERALD
    p.space_after = Pt(4)

    test_items = [
        ("KẾT QUẢ BỘ TEST QA TOÀN DỰ ÁN",
         "• Phân hệ ETL của Thái: 172 / 172 checks PASS (0 FAIL).\n• Toàn bộ dự án: 321 PASS, 1 INFO, 0 FAIL.\n• Minh chứng độc lập lưu tại tests/qa_results.csv."),
        ("5 TEST CASES HỒI QUY (TEST_ETL_REGRESSIONS.PY)",
         "• Test 1: Khử trùng grain Reviews chính xác.\n• Test 2: Rollback transaction an toàn khi chunk lỗi.\n• Test 3: Idempotent - Chạy lại lần 2 nạp đè sạch sẽ.\n• Test 4: Chặn xuất Gold khi có orphan key.\n• Test 5: Chuẩn hóa cờ Available 't'/'f' -> 1/0.\n-> Thời gian chạy: 0.65s (100% OK)."),
        ("TÍNH TOÀN VẸN THAM CHIẾU (ZERO ORPHAN)",
         "• Calendar -> Listings: 100.0% khớp (0 orphan).\n• Reviews -> Listings: 100.0% khớp (0 orphan).\n• Listings -> Neighbourhoods: 100.0% khớp (0 orphan).\n• Event Dates -> dim_date: 100.0% khớp (0 orphan).")
    ]
    for h, b in test_items:
        ph = tf2.add_paragraph()
        ph.text = h
        ph.font.name = "Arial"
        ph.font.size = Pt(8.2)
        ph.font.bold = True
        ph.font.color.rgb = C_NAVY_DARK
        ph.space_before = Pt(3)

        pb = tf2.add_paragraph()
        pb.text = b
        pb.font.name = "Arial"
        pb.font.size = Pt(7.4)
        pb.font.color.rgb = C_NAVY_BODY
        pb.line_spacing = 1.15

    # CỘT 3: HƯỚNG DẪN DEMO TẠI CHỖ & KỊCH BẢN ELEVATOR PITCH
    c3_x = Inches(0.8) + 2 * (col_w + gap_w)
    add_rounded_card(slide, c3_x, box_y, col_w, box_h, bg_color=C_WHITE, border_color=C_PURPLE, border_pt=1.5)
    tb3 = slide.shapes.add_textbox(c3_x + Inches(0.15), box_y + Inches(0.12), col_w - Inches(0.30), box_h - Inches(0.24))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    tf3.margin_left = tf3.margin_right = tf3.margin_top = tf3.margin_bottom = 0

    p = tf3.paragraphs[0]
    p.text = "3. HƯỚNG DẪN LIVE DEMO & ELEVATOR PITCH"
    p.font.name = "Arial"
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = C_PURPLE
    p.space_after = Pt(4)

    demo_items = [
        ("LỆNH DEMO NHANH CHẾ ĐỘ MẪU (~2 GIÂY)",
         "python scripts/demo_etl_pipeline.py --sample 500\n(Hoặc click đúp file scripts/run_demo.ps1)\n-> Đọc 500 dòng/nguồn, thực thi Ingest -> Clean -> Transform và in bảng đối soát tự động."),
        ("LỆNH DEMO TOÀN BỘ 1.17M DÒNG THẬT (~42 GIÂY)",
         "python scripts/demo_etl_pipeline.py --full\n-> Nạp toàn bộ dữ liệu, kiểm tra 0 orphan key."),
        ("LỆNH CHẠY BỘ TEST HỒI QUY TỰ ĐỘNG (~0.65 GIÂY)",
         "python -m unittest tests/test_etl_regressions.py"),
        ("KỊCH BẢN THUYẾT TRÌNH 1–2 PHÚT (PITCH)",
         "'Kính thưa Thầy Cô, phân hệ ETL của em đã hoàn thành xuất sắc 3 mục tiêu:\n1. Tự động hóa xử lý 1.17M dòng trong 42s;\n2. Khả lặp 100% (xóa partition theo snapshot trước khi nạp);\n3. Chuẩn hóa SGD, giữ 483 NULL giá và 0 orphan key.'")
    ]
    for h, b in demo_items:
        ph = tf3.add_paragraph()
        ph.text = h
        ph.font.name = "Arial"
        ph.font.size = Pt(8.2)
        ph.font.bold = True
        ph.font.color.rgb = C_NAVY_DARK
        ph.space_before = Pt(3)

        pb = tf3.add_paragraph()
        pb.text = b
        pb.font.name = "Arial"
        pb.font.size = Pt(7.4)
        pb.font.color.rgb = C_NAVY_BODY
        pb.line_spacing = 1.15

    add_common_footer(slide, "32", "Tài liệu tái lập: slides/README.md & tests/README.md | Git: main")


# ==============================================================================
# MAIN EXECUTOR
# ==============================================================================
def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    print("Building exact slides for Thai (Pages 09, 10, 12, 32)...")
    create_page_09(prs)
    create_page_10(prs)
    create_page_12(prs)
    create_page_32(prs)

    prs.save(OUTPUT_PPTX_THAI)
    print(f"[OK] Saved Thai's 4 slides deck to: {OUTPUT_PPTX_THAI}")

    # Đồng thời cập nhật vào file chính 5.4_slide_etl_pipeline_and_tests.pptx
    prs.save(OUTPUT_PPTX_MAIN)
    print(f"[OK] Synchronized with main presentation: {OUTPUT_PPTX_MAIN}")


if __name__ == "__main__":
    main()
