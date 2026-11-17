"""
build_slide_21_pptx.py
----------------------
Tạo tệp slide PowerPoint chuẩn 16:9 cho Slide 21:
"Chạy lại cùng snapshot có tạo dòng trùng hay đổi KPI? (TQ-05 / TC-20)"
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
OUTPUT_PPTX_21 = SLIDES_DIR / "slide_21_tq05_rerun_evidence.pptx"
IMAGE_PATH = PROJECT_ROOT / "outputs" / "tq05_rerun_idempotency_evidence.png"

# Palette
C_NAVY_DARK = RGBColor(15, 23, 42)      # #0F172A
C_NAVY_BODY = RGBColor(30, 41, 59)      # #1E293B
C_CYAN_ACC  = RGBColor(2, 132, 199)     # #0284C7
C_EMERALD   = RGBColor(5, 150, 105)     # #059669
C_BG_SLATE  = RGBColor(248, 250, 252)   # #F8FAFC
C_WHITE     = RGBColor(255, 255, 255)   # #FFFFFF
C_BORDER    = RGBColor(203, 213, 225)   # #CBD5E1
C_SLATE_MUT = RGBColor(100, 116, 139)   # #64748B


def create_slide_21():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Nền
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = C_BG_SLATE

    # Dải điều hướng
    tb_nav = slide.shapes.add_textbox(Inches(0.8), Inches(0.30), Inches(11.733), Inches(0.24))
    tf_nav = tb_nav.text_frame
    tf_nav.word_wrap = True
    tf_nav.margin_left = tf_nav.margin_top = tf_nav.margin_right = tf_nav.margin_bottom = 0
    p_nav = tf_nav.paragraphs[0]
    p_nav.text = "D. TRIỂN KHAI VÀ KIỂM CHỨNG · SLIDE 21 / 33 | PHỤ TRÁCH: THÁI (DATA ENGINEER)"
    p_nav.font.name = "Arial"
    p_nav.font.size = Pt(9)
    p_nav.font.bold = True
    p_nav.font.color.rgb = C_CYAN_ACC

    # Tiêu đề kết luận lớn
    tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.54), Inches(11.733), Inches(0.44))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = "CHẠY LẠI CÙNG SNAPSHOT: 0 DÒNG TRÙNG, KHÔNG ĐỔI KPI, ĐẠT CHUẨN TQ-05 (PASS)"
    p_title.font.name = "Arial"
    p_title.font.size = Pt(17.5)
    p_title.font.bold = True
    p_title.font.color.rgb = C_NAVY_DARK

    # Phụ đề
    tb_sub = slide.shapes.add_textbox(Inches(0.8), Inches(1.00), Inches(11.733), Inches(0.26))
    tf_sub = tb_sub.text_frame
    tf_sub.word_wrap = True
    tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = "Đối soát 2 lần chạy liên tiếp (Run 1 vs Run 2) với cùng snapshot 2026-09-23 trên toàn bộ 6 bảng Fact và Dimension"
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(9.5)
    p_sub.font.color.rgb = C_SLATE_MUT

    # Đường kẻ ngăn cách dải điều hướng
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.28), Inches(11.733), Inches(0.012))
    line.fill.solid()
    line.fill.fore_color.rgb = C_BORDER
    line.line.color.rgb = C_BORDER

    # Chèn ảnh Dashboard đối soát TQ-05 cực kỳ sắc nét
    if IMAGE_PATH.exists():
        slide.shapes.add_picture(
            str(IMAGE_PATH),
            Inches(0.8), Inches(1.36),
            width=Inches(11.733), height=Inches(5.48)
        )

    # Footer
    line_f = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.92), Inches(11.733), Inches(0.012))
    line_f.fill.solid()
    line_f.fill.fore_color.rgb = C_BORDER
    line_f.line.color.rgb = C_BORDER

    tb_f = slide.shapes.add_textbox(Inches(0.8), Inches(6.96), Inches(10.2), Inches(0.3))
    tf_f = tb_f.text_frame
    tf_f.margin_left = tf_f.margin_top = tf_f.margin_right = tf_f.margin_bottom = 0
    p_f = tf_f.paragraphs[0]
    p_f.text = "Nguồn: data/raw/ | Audit log: outputs/tq05_rerun_idempotency_evidence.csv | Snapshot: 2026-09-23"
    p_f.font.name = "Arial"
    p_f.font.size = Pt(8.5)
    p_f.font.color.rgb = C_SLATE_MUT

    tb_p = slide.shapes.add_textbox(Inches(11.0), Inches(6.96), Inches(1.533), Inches(0.3))
    tf_p = tb_p.text_frame
    tf_p.margin_left = tf_p.margin_right = tf_p.margin_top = tf_p.margin_bottom = 0
    p_p = tf_p.paragraphs[0]
    p_p.text = "Slide 21 / 33"
    p_p.alignment = PP_ALIGN.RIGHT
    p_p.font.name = "Arial"
    p_p.font.size = Pt(8.5)
    p_p.font.bold = True
    p_p.font.color.rgb = C_CYAN_ACC

    prs.save(OUTPUT_PPTX_21)
    print(f"[OK] Saved Slide 21 PPTX: {OUTPUT_PPTX_21}")


if __name__ == "__main__":
    create_slide_21()
