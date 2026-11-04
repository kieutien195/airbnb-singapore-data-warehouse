"""Khảo sát task 2.1 từ raw; không sửa dữ liệu nguồn."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILES = {"Listings": "listings.csv.gz", "Calendar": "calendar.csv.gz",
         "Reviews": "reviews.csv.gz", "Neighbourhoods": "neighbourhoods.csv"}
DATE_COLUMNS = {"last_scraped", "calendar_last_scraped", "host_since",
                "first_review", "last_review", "date",
                "price_quote_checkin_date", "price_quote_checkout_date"}
GRAINS = {"Listings": "listing/snapshot", "Calendar": "listing/ngày/snapshot",
          "Reviews": "bản ghi review (khóa ứng viên listing_id + id)",
          "Neighbourhoods": "khu vực"}
# Không đưa tên người, nội dung review hoặc mô tả dài vào output khảo sát.
SAMPLE_REDACTED = {"host_name", "host_about", "description", "reviewer_name", "comments"}


def survey():
    data = {name: pd.read_csv(ROOT / "data" / "raw" / file,
                             encoding="utf-8-sig", low_memory=False)
            for name, file in FILES.items()}
    rows = []
    for name, df in data.items():
        for col in df.columns:
            values = df[col].dropna().astype(str).drop_duplicates().head(3)
            sample = "[Không xuất văn bản cá nhân/mô tả dài]" if col in SAMPLE_REDACTED else " | ".join(v[:120] for v in values)
            dmin = dmax = ""
            if col in DATE_COLUMNS:
                dates = pd.to_datetime(df[col], errors="coerce").dropna()
                if len(dates):
                    dmin, dmax = dates.min().date().isoformat(), dates.max().date().isoformat()
            rows.append({"source": name, "file_name": FILES[name], "column": col,
                         "dtype_initial": str(df[col].dtype), "rows_in_source": len(df),
                         "columns_in_source": len(df.columns), "null_count": int(df[col].isna().sum()),
                         "null_pct": round(df[col].isna().mean() * 100, 4),
                         "unique_non_null": int(df[col].nunique()), "sample_values": sample,
                         "date_min": dmin, "date_max": dmax})
    summary = pd.DataFrame(rows)
    listing, calendar, reviews, areas = (data[k] for k in FILES)
    listing_ids = set(listing.id)
    keys = {"Listings": ["id"], "Calendar": ["listing_id", "date"],
            "Reviews": ["listing_id", "id"],
            "Neighbourhoods": ["neighbourhood_group", "neighbourhood"]}
    key_rows = []
    for name, cols in keys.items():
        df = data[name]
        valid = df[cols].notna().all(axis=1)
        key_rows.append({"source": name, "grain": GRAINS[name], "candidate_key": "+".join(cols),
                         "rows": len(df), "missing_key_rows": int((~valid).sum()),
                         "duplicate_excess_rows": int(df.loc[valid].duplicated(cols).sum())})
    key_checks = pd.DataFrame(key_rows)
    links = []
    for name, df in [("Calendar", calendar), ("Reviews", reviews)]:
        present = df.listing_id.notna()
        links.append({"relationship": f"{name}.listing_id -> Listings.id",
                      "missing_key_rows": int((~present).sum()),
                      "orphan_rows": int((present & ~df.listing_id.isin(listing_ids)).sum())})
    parent_pairs = set(zip(areas.neighbourhood_group, areas.neighbourhood))
    pairs = pd.Series(list(zip(listing.neighbourhood_group_cleansed, listing.neighbourhood_cleansed)))
    present = listing[["neighbourhood_group_cleansed", "neighbourhood_cleansed"]].notna().all(axis=1)
    links.append({"relationship": "Listings.(group_cleansed, neighbourhood_cleansed) -> Neighbourhoods.(group, neighbourhood)",
                  "missing_key_rows": int((~present).sum()),
                  "orphan_rows": int((present & ~pairs.isin(parent_pairs)).sum())})
    link_checks = pd.DataFrame(links)
    findings = [
        f"Reviews.id: {reviews.id.nunique():,} mã khác nhau / {len(reviews):,} dòng; "
        f"{reviews.duplicated(['id']).sum():,} dòng lặp ID sau lần đầu. "
        f"Khóa (listing_id,id) có {reviews.duplicated(['listing_id', 'id']).sum()} dòng trùng dư trong snapshot này; cần xác minh ngữ nghĩa nguồn trước DDL.",
        f"Listings.neighbourhood có {listing.neighbourhood.isna().sum():,} NULL; dùng cặp neighbourhood_group_cleansed/neighbourhood_cleansed để nối khu vực.",
        f"Danh mục có {len(set(areas.neighbourhood) - set(listing.neighbourhood_cleansed))} khu vực không có listing; không tự coi là lỗi.",
        "Listings.price và price_quote_price_per_night gần nghĩa nhưng không mặc định thay thế nhau; kiểm tra currency và chênh lệch trước ETL.",
        "Calendar hiện không có cột price. Reviews không có điểm rating; review_scores_rating lấy từ Listings.",
        "Các cột toàn NULL cần ghi nhận và quyết định phạm vi sử dụng, không suy kiểu nghiệp vụ từ float64.",
        "Không JOIN Calendar và Reviews ở mức chi tiết để tính KPI vì hai bảng đều nhiều dòng trên một listing.",
        "snapshot_date lấy từ docs/source_inventory.csv; không đồng nhất với last_scraped hoặc ngày phát sinh review."
    ]
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    summary.to_csv(docs / "source_schema_summary.csv", index=False, encoding="utf-8-sig")
    (docs / "schema_survey_findings.md").write_text(
        "# Task 2.1 – Kết luận khảo sát nguồn\n\n" + "\n\n".join("- " + x for x in findings), encoding="utf-8")
    return summary, key_checks, link_checks, findings


if __name__ == "__main__":
    summary, keys, links, findings = survey()
    print(f"Đã khảo sát {len(summary)} trường từ {len(FILES)} nguồn.")
    print(keys.to_string(index=False))
    print(links.to_string(index=False))
    for finding in findings:
        print(finding)
