# -*- coding: utf-8 -*-
"""Task 2.1: generate notebooks/01_schema_survey.ipynb in the Git clone.

Run from repository root: python scripts/schema_survey.py
Reads existing docs/ and data/raw/. Writes only the schema survey notebook.
No outputs/ folder or ZIP. No changes to existing CSVs, raw, PNG or KPI/EDA files.
Dependencies: pandas, IPython and nbformat (provided with JupyterLab).
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


def find_project_dir(given=None):
    candidates = [Path(given).expanduser().resolve()] if given else [
        Path(__file__).resolve().parent, *Path(__file__).resolve().parents,
        Path.cwd(), *Path.cwd().parents,
    ]
    for root in candidates:
        if (root / "data" / "raw").is_dir() and (root / "docs").is_dir() and (root / "notebooks").is_dir():
            return root
    raise FileNotFoundError("Không tìm thấy repo có data/raw, docs và notebooks; dùng --project-dir nếu cần.")


def build_notebook(path: Path, project_dir: Path) -> None:
    import nbformat
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.utils.capture import capture_output
    import os
    specs = [('markdown',
      '# TASK 2.1 – Khảo sát schema và quan hệ Airbnb Singapore\n'
      '\n'
      'Notebook trình bày đầy đủ dữ liệu khảo sát, grain, khóa và quan hệ theo PCCV ô C9.\n'
      'Hồ sơ đã chốt được đọc từ docs/source_schema_summary.csv và\n'
      'docs/source_inventory.csv; sơ đồ hiện có là docs/relationship_diagram.png.\n'
      'Các kết quả kiểm tra quan hệ được hiển thị trong bộ nhớ, không xuất CSV mới.\n'
      'Các kiểm tra bổ sung là bằng chứng khảo sát, không thay thế các quyết định của 2.2/2.3.\n'
      'Không sửa raw, không cleaning, không định nghĩa lại KPI hoặc schema warehouse.\n'
      '\n'
      '## 1. Khởi tạo và nguồn dữ liệu\n'),
     ('code',
      'from pathlib import Path\n'
      'import pandas as pd\n'
      'from IPython.display import display, Markdown\n'
      '\n'
      'pd.set_option("display.max_rows", None)\n'
      'pd.set_option("display.max_columns", None)\n'
      'pd.set_option("display.max_colwidth", None)\n'
      'SURVEY_DIR = Path.cwd()\n'
      'candidates = [Path.cwd(), *Path.cwd().parents]\n'
      'PROJECT_DIR = next((p for p in candidates if (p / "data" / "raw").is_dir()), None)\n'
      'if PROJECT_DIR is None:\n'
      '    raise FileNotFoundError("Không tìm thấy data/raw; chạy notebook trong project nguồn.")\n'
      'RAW_DIR = PROJECT_DIR / "data" / "raw"\n'
      'FILES = {"Listings":"listings.csv.gz", "Calendar":"calendar.csv.gz", "Reviews":"reviews.csv.gz", '
      '"Neighbourhoods":"neighbourhoods.csv"}\n'
      '\n'
      'def read_source(name):\n'
      '    p = RAW_DIR / FILES[name]\n'
      '    try:\n'
      '        return pd.read_csv(p, compression="gzip" if p.suffix == ".gz" else None,\n'
      '                           encoding="utf-8-sig", low_memory=False)\n'
      '    except UnicodeDecodeError:\n'
      '        return pd.read_csv(p, compression="gzip" if p.suffix == ".gz" else None,\n'
      '                           encoding="cp1252", low_memory=False)\n'
      '\n'
      'data = {name: read_source(name) for name in FILES}\n'
      'print("Project:", PROJECT_DIR)\n'
      'display(pd.DataFrame([{"source":name, "file_name":FILES[name], "rows":len(df),\n'
      '                       "columns":len(df.columns)} for name, df in data.items()]))\n'),
     ('markdown',
      '## 2. Hồ sơ nguồn và snapshot đã chốt\n'
      'Snapshot và khoảng ngày thực tế là hai thông tin riêng biệt. Không coi toàn bộ reviews/calendar là dữ '
      'liệu phát sinh trong năm 2026.'),
     ('code',
      'ARTIFACT_DIR = PROJECT_DIR / "docs"\n'
      'inventory_locked = pd.read_csv(ARTIFACT_DIR / "source_inventory.csv", encoding="utf-8-sig", '
      'keep_default_na=False)\n'
      'display(inventory_locked)\n'),
     ('markdown',
      '## 3. Toàn bộ cột, dtype, NULL, tính phân biệt và mẫu dữ liệu đã chốt\n'
      '`dtype_initial` là dtype khi khảo sát, không phải kiểu đích MySQL. Mẫu giới hạn ba giá trị; không in toàn '
      'bộ raw.'),
     ('code',
      'schema_locked = pd.read_csv(ARTIFACT_DIR / "source_schema_summary.csv", encoding="utf-8-sig", '
      'keep_default_na=False)\n'
      'schema_display = schema_locked.copy()\n'
      'review_personal = schema_display["source"].eq("Reviews") & schema_display["column"].isin(["comments", '
      '"reviewer_name", "reviewer_id"])\n'
      'schema_display.loc[review_personal, "sample_values"] = "[Ẩn mẫu cá nhân; giữ nguyên hồ sơ CSV gốc]"\n'
      'print("Số trường đã ghi nhận:", len(schema_locked))\n'
      'for name in FILES:\n'
      '    print("\\nNguồn:", name)\n'
      '    display(schema_display.loc[schema_display["source"].eq(name)])\n'),
     ('markdown',
      '## 4. Khảo sát trực tiếp dữ liệu nguồn\n'
      'Giữ nguyên các phép tính của notebook gốc; bảng sau được tính lại trong bộ nhớ để đối chiếu, không xuất '
      'đè CSV đã chốt.'),
     ('code',
      "date_cols = {'Listings':['last_scraped','calendar_last_scraped','first_review','last_review'], "
      "'Calendar':['date'], 'Reviews':['date'], 'Neighbourhoods':[]}\n"
      'schema_rows = []\n'
      'for name, df in data.items():\n'
      "    print(f'\\n### {name}: {df.shape[0]:,} hàng x {df.shape[1]} cột')\n"
      '    for col in df.columns:\n'
      '        vals = df[col].dropna().astype(str).drop_duplicates().head(3).tolist()\n'
      "        dmin = dmax = ''\n"
      '        if col in date_cols[name]:\n'
      "            d = pd.to_datetime(df[col], errors='coerce')\n"
      '            if d.notna().any(): dmin, dmax = d.min().date().isoformat(), d.max().date().isoformat()\n'
      '        '
      "schema_rows.append({'source':name,'column':col,'dtype_initial':str(df[col].dtype),'rows':len(df),'columns':len(df.columns),'null_count':int(df[col].isna().sum()),'unique_non_null':int(df[col].nunique()),'sample_values':('[Ẩn "
      "mẫu cá nhân]' if name == 'Reviews' and col in {'comments', 'reviewer_name', 'reviewer_id'} else ' | "
      "'.join(vals)),'date_min':dmin,'date_max':dmax})\n"
      '    display(df.drop(columns=["comments", "reviewer_name", "reviewer_id"], errors="ignore").head(3) if '
      'name == "Reviews" else df.head(3))\n'
      'schema_summary = pd.DataFrame(schema_rows)\n'
      'display(schema_summary)'),
     ('markdown', '## 5. Đối chiếu cấu trúc nguồn với hồ sơ đã chốt'),
     ('code',
      'comparison_rows = []\n'
      'for name, df in data.items():\n'
      '    saved_columns = schema_locked.loc[schema_locked["source"].eq(name), "column"].tolist()\n'
      '    comparison_rows.append({\n'
      '        "source":name,\n'
      '        "column_order_matches":list(df.columns) == saved_columns,\n'
      '        "missing_vs_locked":str(sorted(set(saved_columns) - set(df.columns))),\n'
      '        "added_vs_locked":str(sorted(set(df.columns) - set(saved_columns))),\n'
      '        "rows_current":len(df),\n'
      '        "rows_locked":int(schema_locked.loc[schema_locked["source"].eq(name), '
      '"rows_in_source"].iloc[0]),\n'
      '    })\n'
      'display(pd.DataFrame(comparison_rows))\n'
      'print("Dtype phụ thuộc phiên bản Pandas; hồ sơ dtype đã chốt không bị ghi đè.")\n'),
     ('markdown',
      '## 6. Grain và kiểm tra khóa/liên kết gốc\n'
      'Giữ nguyên cách kiểm tra đã dùng tại Task 2.1; không mặc định Reviews.id là PK khi còn trùng.'),
     ('code',
      'listings, calendar, reviews, neighbourhoods = (data[k] for k in '
      "['Listings','Calendar','Reviews','Neighbourhoods'])\n"
      "print('Listings grain: listing tại snapshot; id duy nhất:', listings['id'].is_unique if 'id' in listings "
      "else 'thiếu cột')\n"
      "print('Calendar grain: listing-ngày; duplicate (listing_id,date):', "
      "calendar.duplicated(['listing_id','date']).sum() if {'listing_id','date'} <= set(calendar.columns) else "
      "'thiếu cột')\n"
      "print('Reviews grain: một review; duplicate id:', reviews['id'].duplicated().sum() if 'id' in reviews "
      "else 'thiếu cột')\n"
      "print('Neighbourhoods grain: một khu vực; duplicate neighbourhood:', "
      "neighbourhoods['neighbourhood'].duplicated().sum() if 'neighbourhood' in neighbourhoods else 'thiếu "
      "cột')\n"
      "listing_ids = set(listings['id'].dropna().astype(str))\n"
      "for name, df in [('Calendar',calendar),('Reviews',reviews)]:\n"
      "    ids = set(df['listing_id'].dropna().astype(str))\n"
      "    print(name, 'listing_id không khớp Listings:', len(ids-listing_ids))\n"
      "if 'neighbourhood_cleansed' in listings and 'neighbourhood' in neighbourhoods:\n"
      "    a=set(listings['neighbourhood_cleansed'].dropna().astype(str)); "
      "b=set(neighbourhoods['neighbourhood'].dropna().astype(str))\n"
      "    print('Neighbourhood chưa map:', sorted(a-b))\n"
      "    print('Neighbourhood trong danh mục không xuất hiện ở Listings:', sorted(b-a))\n"
      "print('Listings.neighbourhood NULL:', listings['neighbourhood'].isna().sum() if 'neighbourhood' in "
      "listings else 'thiếu cột')"),
     ('markdown', '## 7. Tái hiện toàn bộ kiểm tra quan hệ gốc'),
     ('code',
      'L, C, R, N = (data[k] for k in ["Listings", "Calendar", "Reviews", "Neighbourhoods"])\n'
      'checks = []\n'
      'def add_check(check, value, note=""):\n'
      '    checks.append({"check": check, "result": value, "note": note})\n'
      '\n'
      'if "id" in L:\n'
      '    add_check("Listings.id duplicate rows", int(L["id"].duplicated().sum()), "Kỳ vọng 0 nếu id là khóa '
      'chính")\n'
      'if {"listing_id", "date"}.issubset(C.columns):\n'
      '    add_check("Calendar duplicate (listing_id,date)", int(C.duplicated(["listing_id", "date"]).sum()), '
      '"Grain kỳ vọng: một listing mỗi ngày")\n'
      'if "id" in R:\n'
      '    add_check("Reviews.id duplicate rows", int(R["id"].duplicated().sum()), "Không kết luận id là PK nếu '
      'còn trùng")\n'
      'if "neighbourhood" in N:\n'
      '    add_check("Neighbourhoods.neighbourhood duplicate rows", int(N["neighbourhood"].duplicated().sum()), '
      '"Danh mục khu vực nên duy nhất theo neighbourhood")\n'
      'if "id" in L:\n'
      '    listing_ids = set(L["id"].dropna().astype(str))\n'
      '    for source, df in [("Calendar", C), ("Reviews", R)]:\n'
      '        if "listing_id" in df:\n'
      '            ids = set(df["listing_id"].dropna().astype(str))\n'
      '            add_check(f"{source}.listing_id orphan distinct IDs", len(ids - listing_ids), "Số listing_id '
      'không tìm thấy trong Listings.id")\n'
      'if {"neighbourhood_cleansed"}.issubset(L.columns) and "neighbourhood" in N.columns:\n'
      '    a = set(L["neighbourhood_cleansed"].dropna().astype(str))\n'
      '    b = set(N["neighbourhood"].dropna().astype(str))\n'
      '    add_check("Listings.neighbourhood_cleansed not in Neighbourhoods", len(a - b), ", ".join(sorted(a - '
      'b))[:1000])\n'
      '    add_check("Neighbourhoods not used by Listings", len(b - a), ", ".join(sorted(b - a))[:1000])\n'
      'if "neighbourhood" in L:\n'
      '    add_check("Listings.neighbourhood NULL rows", int(L["neighbourhood"].isna().sum()), "Đối chiếu với '
      'neighbourhood_cleansed; không JOIN bằng cột này nếu NULL")\n'
      '\n'
      'relationship_current = pd.DataFrame(checks)\n'
      'display(relationship_current)\n'),
     ('markdown',
      '## 8. Bằng chứng bổ sung cho khóa ghép và liên kết\n'
      '\n'
      'Giữ nguyên grain gốc. Phân biệt kiểm tra id riêng lẻ và khóa ghép quan sát được;\n'
      'không tự suy ra khóa nghiệp vụ chỉ từ tính duy nhất. Đối chiếu cặp khu vực bổ sung\n'
      'cho phép đối chiếu neighbourhood gốc, không thay thế quan hệ đã chốt.\n'),
     ('code',
      'key_rows = []\n'
      'for name, keys in [\n'
      '    ("Listings", ["id"]),\n'
      '    ("Calendar", ["listing_id", "date"]),\n'
      '    ("Reviews", ["id"]),\n'
      '    ("Reviews", ["listing_id", "id"]),\n'
      '    ("Neighbourhoods", ["neighbourhood"]),\n'
      '    ("Neighbourhoods", ["neighbourhood_group", "neighbourhood"]),\n'
      ']:\n'
      '    df = data[name]\n'
      '    missing = [k for k in keys if k not in df.columns]\n'
      '    key_rows.append({"source":name, "candidate_key":" + ".join(keys),\n'
      '        "missing_columns":str(missing),\n'
      '        "rows_with_null_key":None if missing else int(df[keys].isna().any(axis=1).sum()),\n'
      '        "duplicate_excess":None if missing else int(df.duplicated(keys).sum())})\n'
      'display(pd.DataFrame(key_rows))\n'
      'listing_ids = set(listings["id"].dropna())\n'
      'link_rows = []\n'
      'for name, df in [("Calendar", calendar), ("Reviews", reviews)]:\n'
      '    child_ids = set(df["listing_id"].dropna())\n'
      '    link_rows.append({"source":name,\n'
      '        "orphan_distinct_listing_ids":len(child_ids - listing_ids),\n'
      '        "orphan_non_null_rows":int((df["listing_id"].notna() & '
      '~df["listing_id"].isin(listing_ids)).sum()),\n'
      '        "null_listing_id_rows":int(df["listing_id"].isna().sum()),\n'
      '        "matched_listing_count":len(child_ids & listing_ids),\n'
      '        "listing_count":len(listing_ids)})\n'
      'display(pd.DataFrame(link_rows))\n'
      'if {"neighbourhood_group_cleansed", "neighbourhood_cleansed"} <= set(listings.columns):\n'
      '    lp = set(listings[["neighbourhood_group_cleansed", '
      '"neighbourhood_cleansed"]].dropna().itertuples(index=False, name=None))\n'
      '    npairs = set(neighbourhoods[["neighbourhood_group", '
      '"neighbourhood"]].dropna().itertuples(index=False, name=None))\n'
      '    print("Cặp khu vực Listings không tìm thấy ở Neighbourhoods:", len(lp - npairs))\n'),
     ('markdown',
      '## 9. Cột trùng tên, gần nghĩa, thiếu hoặc cần rà soát\n'
      '\n'
      'Trùng tên giữa bảng không đồng nghĩa trùng ý nghĩa: `id` của Listings khác `id`\n'
      'của Reviews; `date` của Calendar khác `date` của Reviews. Các cặp cần đối chiếu\n'
      'là ghi chú khảo sát, không phải lệnh đổi tên/xóa cột. Cột 100% NULL được nhận diện\n'
      'để bàn giao, không kết luận tự động rằng cột không dùng.\n'),
     ('code',
      'column_sources = {}\n'
      'for name, df in data.items():\n'
      '    for column in df.columns:\n'
      '        column_sources.setdefault(column, []).append(name)\n'
      'display(pd.DataFrame([{"column":c, "sources":" | ".join(names)}\n'
      '                      for c, names in column_sources.items() if len(names) > 1]))\n'
      'print("Trường 100% NULL theo hồ sơ đã chốt:")\n'
      'mask = pd.to_numeric(schema_locked["null_count"]).eq(pd.to_numeric(schema_locked["rows_in_source"]))\n'
      'display(schema_locked.loc[mask])\n'
      'display(pd.DataFrame([\n'
      '    {"fields":"Listings.neighbourhood / neighbourhood_cleansed", "note":"Không mặc định cùng ý nghĩa; giữ '
      'cột cleansed dùng đối chiếu như hồ sơ gốc."},\n'
      '    {"fields":"Listings.price / price_quote_price_per_night", "note":"Gần nghĩa; giữ quy tắc đối chiếu và '
      'đơn vị đã chốt ở 2.2, không thay KPI."},\n'
      '    {"fields":"Listings.room_type / property_type", "note":"Hai phân loại khác nhau; không gộp."},\n'
      '    {"fields":"Listings.id / Reviews.id", "note":"Khác thực thể; không JOIN bằng hai cột id này."},\n'
      '    {"fields":"Calendar.date / Reviews.date", "note":"Ngày lịch và ngày đánh giá; không coi cùng '
      'grain."},\n'
      ']))\n'),
     ('markdown',
      '## 10. Sơ đồ mối quan hệ sơ bộ\n'
      'Hiển thị PNG hiện có trong docs/ và giữ phần giải thích Mermaid gốc.\n'
      'PK/FK là định hướng khảo sát, không phải ràng buộc MySQL đã triển khai.'),
     ('code',
      'from IPython.display import Image\n'
      'image_path = ARTIFACT_DIR / "relationship_diagram.png"\n'
      'if image_path.exists():\n'
      '    display(Image(filename=str(image_path)))\n'
      'else:\n'
      '    print("Không có PNG tại docs/relationship_diagram.png; xem Mermaid bên dưới.")\n'
      "diagram_text = '# Sơ đồ quan hệ sơ bộ – Airbnb Singapore (Mục 2.1)\\n\\n```mermaid\\nerDiagram\\n    "
      'NEIGHBOURHOODS ||--o{ LISTINGS : "neighbourhood_cleansed = neighbourhood"\\n    LISTINGS ||--o{ CALENDAR '
      ': "id = listing_id"\\n    LISTINGS ||--o{ REVIEWS : "id = listing_id"\\n\\n    NEIGHBOURHOODS {\\n        '
      'string neighbourhood PK\\n        string neighbourhood_group\\n    }\\n    LISTINGS {\\n        int id '
      'PK\\n        string neighbourhood_cleansed FK\\n        string room_type\\n        string '
      'property_type\\n    }\\n    CALENDAR {\\n        int listing_id FK\\n        date date PK_part\\n        '
      'boolean available\\n        float price\\n    }\\n    REVIEWS {\\n        int id "review ID - cần xác '
      'minh duy nhất"\\n        int listing_id FK\\n        date date\\n        string reviewer_name\\n    '
      '}\\n```\\n\\n## Grain\\n- **Listings:** một listing tại snapshot.\\n- **Calendar:** một listing tại một '
      'ngày; khóa ứng viên `(listing_id, date)`.\\n- **Reviews:** một review; `listing_id` liên kết Listings. '
      'Không mặc định `id` là duy nhất nếu kiểm tra phát hiện trùng.\\n- **Neighbourhoods:** một khu vực; '
      '`neighbourhood` là khóa liên kết dự kiến.\\n\\n## Quy tắc liên kết sơ bộ\\n- `Listings.id` → '
      '`Calendar.listing_id`.\\n- `Listings.id` → `Reviews.listing_id`.\\n- `Listings.neighbourhood_cleansed` → '
      '`Neighbourhoods.neighbourhood`.\\n- Không dùng `Listings.neighbourhood` để JOIN nếu cột này thiếu hoặc '
      'NULL.\\n\\nCác kết luận cuối cùng cần căn cứ vào `relationship_checks.csv`; không tự ý loại bỏ dòng trùng '
      "hoặc NULL ở bước khảo sát.\\n'\n"
      'display(Markdown(diagram_text))\n'
      'print("Mermaid nguyên văn để đọc khi trình xem không render:")\n'
      'print(diagram_text)\n'),
     ('markdown',
      '## 11. Đối chiếu PCCV và giới hạn kết luận\n'
      '\n'
      '| PCCV Task 2.1 | Bằng chứng trong notebook |\n'
      '|---|---|\n'
      '| Tên cột, dtype, số hàng/cột, mẫu và phạm vi ngày | Mục 1–5, đủ toàn bộ trường |\n'
      '| Phân biệt grain bốn nguồn | Mục 6–8 và sơ đồ gốc |\n'
      '| Kiểm tra id/listing_id/neighbourhood và liên kết | Mục 6–8 |\n'
      '| Nhận diện trường trùng nghĩa, thiếu/cần rà soát | Mục 9; không tự xóa/gộp |\n'
      '| source_schema_summary.csv và sơ đồ quan hệ sơ bộ | Đọc hồ sơ và sơ đồ hiện có ở mục 3, 10; mục 7 tái '
      'hiện kiểm tra gốc |\n'
      '\n'
      'Không sửa quy tắc cleaning của 2.4, mô hình warehouse, Data Dictionary hoặc KPI 2.2.\n'
      'Calendar không thể được diễn giải trực tiếp thành booking/occupancy thực tế.\n'
      'Reviews.id trùng riêng lẻ được giữ nguyên như phát hiện gốc; khóa ghép chỉ được\n'
      'bổ sung bằng chứng. Notebook không sửa raw hoặc các sản phẩm đã chốt.\n')]
    notebook = nbformat.v4.new_notebook()
    notebook.metadata["kernelspec"] = {"display_name":"Python 3", "language":"python", "name":"python3"}
    notebook.cells = []
    for kind, source in specs:
        factory = nbformat.v4.new_code_cell if kind == "code" else nbformat.v4.new_markdown_cell
        notebook.cells.append(factory(source))
    # Run all cells in one fresh IPython namespace inside this script process.
    # Capture source, execution counts, text and rich table outputs in the ipynb.
    shell = InteractiveShell.instance()
    old_cwd = Path.cwd()
    try:
        os.chdir(project_dir)
        count = 0
        for cell in notebook.cells:
            if cell.cell_type != "code":
                continue
            count += 1
            with shell.builtin_trap, capture_output(stdout=True, stderr=True, display=True) as captured:
                result = shell.run_cell(cell.source, store_history=True)
            if result.error_before_exec or result.error_in_exec:
                raise RuntimeError(
                    f"Notebook cell {count} failed: "
                    f"{result.error_before_exec or result.error_in_exec}"
                )
            cell.execution_count = count
            cell.outputs = []
            if captured.stdout:
                cell.outputs.append(nbformat.v4.new_output("stream", name="stdout", text=captured.stdout))
            if captured.stderr:
                cell.outputs.append(nbformat.v4.new_output("stream", name="stderr", text=captured.stderr))
            for rich in captured.outputs:
                cell.outputs.append(nbformat.v4.new_output(
                    "display_data", data=rich.data, metadata=rich.metadata
                ))
            print(f"[OK] Notebook code cell {count}")
    finally:
        os.chdir(old_cwd)
    nbformat.validate(notebook)
    nbformat.write(notebook, path)



def main():
    parser = argparse.ArgumentParser(description="Task 2.1 – notebook schema trong Git clone")
    parser.add_argument("--project-dir", help="Đường dẫn repo clone; mặc định tự tìm từ scripts/")
    args = parser.parse_args()
    root = find_project_dir(args.project_dir)
    required = [root / "docs" / "source_schema_summary.csv", root / "docs" / "source_inventory.csv"]
    required += [root / "data" / "raw" / f for f in ["listings.csv.gz", "calendar.csv.gz", "reviews.csv.gz", "neighbourhoods.csv"]]
    for source in required:
        if not source.is_file():
            raise FileNotFoundError(f"Thiếu file đã có trong repo: {source}")
    target = root / "notebooks" / "01_schema_survey.ipynb"
    build_notebook(target, root)
    print("Đã lưu notebook có source và kết quả chạy:", target.relative_to(root))
    print("Giữ nguyên docs/, tests/, dữ liệu raw và các notebook 2.2/2.3.")


if __name__ == "__main__":
    main()
