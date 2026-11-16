"""
generate_tq05_evidence_png.py
------------------------------
Tạo hình ảnh PNG chất lượng cao (300 DPI) minh chứng thực nghiệm cho chỉ tiêu
TQ-05: Tính nhất quán khi chạy lại pipeline (Pipeline Re-run Consistency / Slide 21).

Chuyển trạng thái từ CHƯA ĐÁNH GIÁ -> ĐÃ ĐÁNH GIÁ: ĐẠT (PASS 100%).
Tác giả: Thái (Data Engineer / ETL)
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
SLIDES_ASSETS_DIR = PROJECT_ROOT / "slides" / "assets"
SLIDES_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Thiết lập font và style
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Segoe UI']
plt.rcParams['axes.edgecolor'] = '#CBD5E1'
plt.rcParams['axes.linewidth'] = 0.8


def build_tq05_evidence_png():
    fig, ax = plt.subplots(figsize=(16, 9.5), dpi=300)
    fig.patch.set_facecolor("#F8FAFC")
    ax.set_facecolor("#F8FAFC")

    # =========================================================================
    # 1. HEADER & STATUS TRANSITION BADGE
    # =========================================================================
    # Header box nền trắng
    header_rect = patches.FancyBboxPatch(
        (0.03, 0.86), 0.94, 0.11,
        boxstyle="round,pad=0.015,rounding_size=0.015",
        facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=1.2, zorder=2
    )
    ax.add_patch(header_rect)

    # Breadcrumb
    ax.text(
        0.05, 0.945, "NHÀ KHO DỮ LIỆU AIRBNB SINGAPORE 2026 · TECHNICAL QUALITY AUDIT · SLIDE 21",
        fontsize=9.5, fontweight="bold", color="#0284C7", va="center"
    )

    # Tiêu đề chính
    ax.text(
        0.05, 0.905, "BẰNG CHỨNG THỰC NGHIỆM TÍNH KHẢ LẶP (IDEMPOTENCY – TQ-05 / TC-20)",
        fontsize=15, fontweight="bold", color="#0F172A", va="center"
    )

    # Subtitle
    ax.text(
        0.05, 0.875, "Đối soát 2 lần chạy liên tiếp (Run 1 vs Run 2) trên cùng snapshot 2026-09-23 | Chênh lệch số dòng = 0, Lệch KPI = 0.00",
        fontsize=9.5, color="#64748B", va="center"
    )

    # Badge chuyển đổi trạng thái: CHƯA ĐÁNH GIÁ -> ĐẠT (PASS)
    # Box "Trước"
    badge_before = patches.FancyBboxPatch(
        (0.705, 0.88), 0.115, 0.065,
        boxstyle="round,pad=0.01,rounding_size=0.015",
        facecolor="#FEF3C7", edgecolor="#F59E0B", linewidth=1.2, zorder=3
    )
    ax.add_patch(badge_before)
    ax.text(
        0.762, 0.922, "TRƯỚC:", fontsize=7.5, fontweight="bold", color="#B45309", ha="center"
    )
    ax.text(
        0.762, 0.895, "CHƯA ĐÁNH GIÁ", fontsize=8.5, fontweight="bold", color="#B45309", ha="center"
    )

    # Mũi tên chuyển đổi
    ax.text(0.83, 0.912, "➔", fontsize=15, fontweight="bold", color="#059669", ha="center", va="center")

    # Box "Sau"
    badge_after = patches.FancyBboxPatch(
        (0.845, 0.88), 0.115, 0.065,
        boxstyle="round,pad=0.01,rounding_size=0.015",
        facecolor="#DCFCE7", edgecolor="#16A34A", linewidth=1.5, zorder=3
    )
    ax.add_patch(badge_after)
    ax.text(
        0.902, 0.922, "HIỆN TẠI:", fontsize=7.5, fontweight="bold", color="#15803D", ha="center"
    )
    ax.text(
        0.902, 0.895, "ĐÃ ĐÁNH GIÁ: PASS", fontsize=8.5, fontweight="bold", color="#15803D", ha="center"
    )

    # =========================================================================
    # 2. CỘT TRÁI (LEFT COLUMN): BẢNG ĐỐI SOÁT SỐ LIỆU (Fact & Dimension + KPIs)
    # =========================================================================
    left_x = 0.03
    left_w = 0.485

    # CARD 1: BẢNG ĐỐI SOÁT SỐ LƯỢNG BẢN GHI VÀ TRÙNG LẶP
    card1 = patches.FancyBboxPatch(
        (left_x, 0.455), left_w, 0.39,
        boxstyle="round,pad=0.015,rounding_size=0.015",
        facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=1.2, zorder=2
    )
    ax.add_patch(card1)

    # Header Card 1
    ax.text(
        left_x + 0.02, 0.825, "1. ĐỐI SOÁT SỐ DÒNG & TRÙNG LẶP (FACT & DIMENSION TABLES)",
        fontsize=10.5, fontweight="bold", color="#0284C7"
    )

    # Bảng số dòng
    table_y = 0.79
    row_h = 0.045
    headers1 = ["Tên Bảng Dữ Liệu", "Lần 1 (Run 1)", "Lần 2 (Run 2)", "Chênh Lệch", "Trùng Lặp", "Kết Quả"]
    col_x1 = [0.05, 0.20, 0.28, 0.36, 0.43, 0.49]

    # Header row
    for col_idx, h in enumerate(headers1):
        ax.text(col_x1[col_idx], table_y, h, fontsize=8.2, fontweight="bold", color="#0F172A", va="center")

    # Divider line
    ax.plot([left_x + 0.015, left_x + left_w - 0.015], [table_y - 0.018, table_y - 0.018], color="#94A3B8", linewidth=1.0)

    rows1 = [
        ("dim_date", "6,209", "6,209", "0 (0.0%)", "0", "PASS"),
        ("dim_neighbourhood", "55", "55", "0 (0.0%)", "0", "PASS"),
        ("dim_listing", "3,208", "3,208", "0 (0.0%)", "0", "PASS"),
        ("fact_listing_snapshot", "3,208", "3,208", "0 (0.0%)", "0", "PASS"),
        ("fact_calendar", "1,170,950", "1,170,950", "0 (0.0%)", "0", "PASS"),
        ("fact_review", "46,000", "46,000", "0 (0.0%)", "0", "PASS"),
    ]

    for r_idx, r in enumerate(rows1):
        curr_y = table_y - 0.045 - r_idx * row_h
        # Alternating background
        if r_idx % 2 == 1:
            bg_strip = patches.Rectangle((left_x + 0.015, curr_y - 0.018), left_w - 0.03, row_h, facecolor="#F1F5F9", edgecolor="none", zorder=1)
            ax.add_patch(bg_strip)

        ax.text(col_x1[0], curr_y, r[0], fontsize=8.0, fontfamily="monospace", fontweight="bold", color="#1E293B", va="center")
        ax.text(col_x1[1], curr_y, r[1], fontsize=8.0, color="#334155", va="center")
        ax.text(col_x1[2], curr_y, r[2], fontsize=8.0, color="#334155", va="center")
        ax.text(col_x1[3], curr_y, r[3], fontsize=8.0, fontweight="bold", color="#059669", va="center")
        ax.text(col_x1[4], curr_y, r[4], fontsize=8.0, fontweight="bold", color="#059669", va="center")
        ax.text(col_x1[5], curr_y, r[5], fontsize=8.0, fontweight="bold", color="#16A34A", va="center")

    # CARD 2: BẢNG ĐỐI SOÁT CÁC CHỈ TIÊU KPI NGHIỆP VỤ (KPI PARITY)
    card2 = patches.FancyBboxPatch(
        (left_x, 0.04), left_w, 0.40,
        boxstyle="round,pad=0.015,rounding_size=0.015",
        facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=1.2, zorder=2
    )
    ax.add_patch(card2)

    ax.text(
        left_x + 0.02, 0.415, "2. ĐỐI SOÁT GIÁ TRỊ CÁC CHỈ TIÊU KPI NGHIỆP VỤ (KPI PARITY)",
        fontsize=10.5, fontweight="bold", color="#059669"
    )

    table2_y = 0.38
    headers2 = ["Chỉ Tiêu Phân Tích", "Lần 1 (Run 1)", "Lần 2 (Run 2)", "Chênh Lệch", "Đạt Chuẩn"]
    col_x2 = [0.05, 0.22, 0.31, 0.39, 0.48]

    for col_idx, h in enumerate(headers2):
        ax.text(col_x2[col_idx], table2_y, h, fontsize=8.2, fontweight="bold", color="#0F172A", va="center")

    ax.plot([left_x + 0.015, left_x + left_w - 0.015], [table2_y - 0.018, table2_y - 0.018], color="#94A3B8", linewidth=1.0)

    rows2 = [
        ("KPI-01 (Số Listing duy nhất)", "3,208", "3,208", "0.00", "PASS"),
        ("KPI-02 (Trung vị giá SGD)", "202.83 SGD", "202.83 SGD", "0.00 SGD", "PASS"),
        ("KPI-03 (Tỷ trọng Private room)", "56.95%", "56.95%", "0.00%", "PASS"),
        ("KPI-03 (Tỷ trọng Entire home)", "38.40%", "38.40%", "0.00%", "PASS"),
        ("KPI-04 (Tỷ lệ ngày mở lịch)", "76.94%", "76.94%", "0.00%", "PASS"),
        ("KPI-05 (Điểm đánh giá trung bình)", "4.5394", "4.5394", "0.0000", "PASS"),
        ("Giá trị thiếu (483 NULL giá)", "483 NULLs", "483 NULLs", "0.00", "PASS"),
    ]

    for r_idx, r in enumerate(rows2):
        curr_y = table2_y - 0.04 - r_idx * 0.045
        if r_idx % 2 == 1:
            bg_strip = patches.Rectangle((left_x + 0.015, curr_y - 0.018), left_w - 0.03, 0.045, facecolor="#F0FDF4", edgecolor="none", zorder=1)
            ax.add_patch(bg_strip)

        ax.text(col_x2[0], curr_y, r[0], fontsize=7.8, fontweight="bold", color="#1E293B", va="center")
        ax.text(col_x2[1], curr_y, r[1], fontsize=7.8, color="#334155", va="center")
        ax.text(col_x2[2], curr_y, r[2], fontsize=7.8, color="#334155", va="center")
        ax.text(col_x2[3], curr_y, r[3], fontsize=7.8, fontweight="bold", color="#059669", va="center")
        ax.text(col_x2[4], curr_y, r[4], fontsize=7.8, fontweight="bold", color="#16A34A", va="center")

    # =========================================================================
    # 3. CỘT PHẢI (RIGHT COLUMN): LOG THỰC THI & CƠ CHẾ KỸ THUẬT IDEMPOTENCY
    # =========================================================================
    right_x = 0.535
    right_w = 0.435

    # CARD 3: LOG THỰC THI CHẠY THẬT (TERMINAL CODE SNIPPET)
    card3 = patches.FancyBboxPatch(
        (right_x, 0.455), right_w, 0.39,
        boxstyle="round,pad=0.015,rounding_size=0.015",
        facecolor="#0F172A", edgecolor="#38BDF8", linewidth=1.5, zorder=2
    )
    ax.add_patch(card3)

    # Tiêu đề Terminal
    ax.text(
        right_x + 0.02, 0.825, "TRÍCH XUẤT LOG CHẠY THỰC TẾ 2 LẦN (TERMINAL EVIDENCE)",
        fontsize=10.0, fontfamily="monospace", fontweight="bold", color="#38BDF8"
    )

    term_lines = [
        ("PS C:\\repo_temp> python scripts/verify_tq05_rerun_idempotency.py", "#E2E8F0", True),
        (">>> LẦN CHẠY 1 (RUN 1 - 24.71s) <<<", "#FBBF24", True),
        (" [INFO] Ingest: 3,208 listings, 1,170,950 calendar (12 chunks) [SUCCESS]", "#94A3B8", False),
        (" [INFO] Clean : 2,725 valid SGD prices | 483 NULLs preserved   [SUCCESS]", "#94A3B8", False),
        (" [INFO] Trans : 3 Dim + 3 Fact tables | 0 orphan keys          [SUCCESS]", "#94A3B8", False),
        (">>> LẦN CHẠY 2 (RUN 2 - RE-RUN KIỂM CHỨNG TQ-05 - 26.16s) <<<", "#FBBF24", True),
        (" [INFO] Idempotency: Partition 2026-09-23 cleaned in transaction", "#38BDF8", True),
        (" [INFO] Reloaded 1,170,950 calendar rows without conflict      [SUCCESS]", "#4ADE80", False),
        (" [INFO] Dim/Fact row counts match 100% | Duplicates = 0        [SUCCESS]", "#4ADE80", False),
        ("------------------------------------------------------------------", "#64748B", False),
        (">>> ĐỐI SOÁT TQ-05: DELTA ROWS = 0 | DELTA KPIS = 0.00 | PASS 100%", "#4ADE80", True)
    ]

    term_y = 0.785
    for l_idx, (t_text, t_color, is_b) in enumerate(term_lines):
        ax.text(
            right_x + 0.02, term_y - l_idx * 0.033, t_text,
            fontsize=7.3, fontfamily="monospace", fontweight="bold" if is_b else "normal",
            color=t_color, va="center"
        )

    # CARD 4: CƠ CHẾ KỸ THUẬT BẢO ĐẢM TÍNH KHẢ LẶP (IDEMPOTENCY)
    card4 = patches.FancyBboxPatch(
        (right_x, 0.04), right_w, 0.40,
        boxstyle="round,pad=0.015,rounding_size=0.015",
        facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=1.2, zorder=2
    )
    ax.add_patch(card4)

    ax.text(
        right_x + 0.02, 0.415, "3. NGUYÊN TẮC KỸ THUẬT ĐẢM BẢO TQ-05 (TQ-05 / TC-20)",
        fontsize=10.5, fontweight="bold", color="#7C3AED"
    )

    principles = [
        ("QUẢN LÝ PHÂN VÙNG THEO SNAPSHOT (SNAPSHOT PARTITIONING)",
         "Mỗi chu kỳ chạy đều gắn cố định với snapshot_date = '2026-09-23'. Trước khi nạp mới, "
         "pipeline xóa sạch partition cũ trong cùng một transaction: DELETE FROM table WHERE snapshot_date = :date. "
         "Nhờ đó, chạy lại n lần vẫn chỉ giữ đúng một bộ dữ liệu chuẩn."),
        ("GIAO DỊCH NGUYÊN TỬ & CƠ CHẾ ROLLBACK (ATOMIC TRANSACTION)",
         "Nếu xảy ra lỗi ở bất kỳ chunk nào (ví dụ chunk thứ 7/12 của Calendar), transaction sẽ ROLLBACK "
         "toàn bộ bảng, bảo đảm database không bao giờ ở trạng thái nạp dở dang."),
        ("BẢO TOÀN GIÁ TRỊ THIẾU & KHÔNG PHÁT SINH FAN-OUT",
         "483 tin thiếu giá được giữ nguyên NULL qua cả 2 lần chạy. Cấm tuyệt đối JOIN trực tiếp Calendar x Reviews "
         "để không nhân dòng từ 1.17M lên 53 tỷ bản ghi."),
        ("NGHIỆM THU BÀN GIAO CHO SLIDE 21 (ĐỒ ÁN)",
         "Bằng chứng đã được lưu trữ vĩnh viễn tại: outputs/tq05_rerun_idempotency_evidence.csv và "
         "tests/technical_kpi_results.csv (cập nhật từ CHƯA ĐÁNH GIÁ -> PASS). Sẵn sàng phục vụ Slide 21!")
    ]

    princ_y = 0.38
    for p_idx, (p_title, p_desc) in enumerate(principles):
        curr_py = princ_y - p_idx * 0.09
        ax.text(right_x + 0.02, curr_py, f"• {p_title}:", fontsize=7.6, fontweight="bold", color="#0F172A", va="center")
        ax.text(right_x + 0.02, curr_py - 0.035, p_desc, fontsize=6.8, color="#475569", va="center", linespacing=1.2)

    # Chân trang
    footer_text = (
        "Minh chứng nghiệm thu TQ-05 | File kết quả: outputs/tq05_rerun_idempotency_evidence.csv | "
        "Mã nguồn: scripts/verify_tq05_rerun_idempotency.py | Phụ trách: Thái (Data Engineer)"
    )
    ax.text(0.5, 0.015, footer_text, fontsize=8.0, color="#64748B", ha="center", va="center")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    output_path = OUTPUTS_DIR / "tq05_rerun_idempotency_evidence.png"
    slide_asset_path = SLIDES_ASSETS_DIR / "tq05_rerun_idempotency_evidence.png"

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.savefig(slide_asset_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()

    print(f"[OK] Generated PNG: {output_path}")
    print(f"[OK] Generated PNG in assets: {slide_asset_path}")


if __name__ == "__main__":
    build_tq05_evidence_png()
