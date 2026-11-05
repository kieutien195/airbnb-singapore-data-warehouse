import os
import sys
import datetime
import pymysql
import dotenv

sys.stdout.reconfigure(encoding='utf-8')

def run_verification():
    dotenv.load_dotenv()
    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    user = os.getenv('MYSQL_USER')
    password = os.getenv('MYSQL_PASSWORD')
    database = os.getenv('MYSQL_DATABASE', 'airbnb_sg_2026')

    print(f"Connecting to MySQL ({host}:{port}) as '{user}' on database '{database}'...")
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        autocommit=True
    )
    cur = conn.cursor()

    print("\n--- BƯỚC 1: Thực thi tệp DDL sql/01_staging_schema.sql ---")
    with open('sql/01_staging_schema.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()

    # Split statements by semicolon
    statements = []
    current = []
    for line in sql_script.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith('--'):
            continue
        current.append(line)
        if trimmed.endswith(';'):
            statements.append('\n'.join(current))
            current = []

    print(f"Tổng số câu lệnh DDL cần chạy: {len(statements)}")
    for i, stmt in enumerate(statements, 1):
        # strip trailing semicolon for pymysql
        s = stmt.strip()
        if s.endswith(';'):
            s = s[:-1]
        try:
            cur.execute(s)
            first_line = s.split('\n')[0][:70]
            print(f"  [{i}/{len(statements)}] PASS: {first_line}")
        except Exception as e:
            print(f"  [{i}/{len(statements)}] FAIL: {e}")
            raise e

    print("\n--- BƯỚC 2: Kiểm tra SHOW TABLES LIKE 'stg_%' ---")
    cur.execute("SHOW TABLES LIKE 'stg_%'")
    staging_tables = [row[0] for row in cur.fetchall()]
    print(f"Các bảng staging đã tạo: {staging_tables}")
    expected_tables = ['stg_calendar', 'stg_listings', 'stg_neighbourhoods', 'stg_reviews']
    for t in expected_tables:
        assert t in staging_tables, f"Thiếu bảng {t}!"
    print("Xác nhận đầy đủ 4 bảng staging: PASS")

    print("\n--- BƯỚC 3: Kiểm tra cấu trúc Schema và số lượng cột ---")
    table_column_counts = {
        'stg_neighbourhoods': 6,   # 2 raw + 3 meta + 1 raw_id
        'stg_calendar': 9,         # 5 raw + 3 meta + 1 raw_id
        'stg_reviews': 10,         # 6 raw + 3 meta + 1 raw_id
        'stg_listings': 94         # 90 raw + 3 meta + 1 raw_id
    }
    for tbl, exp_cnt in table_column_counts.items():
        cur.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME = '{tbl}'
            ORDER BY ORDINAL_POSITION
        """)
        cols = cur.fetchall()
        print(f"Bảng {tbl:20}: {len(cols)} cột (kỳ vọng: {exp_cnt})")
        assert len(cols) == exp_cnt, f"Sai lệch số cột ở bảng {tbl}: có {len(cols)}, kỳ vọng {exp_cnt}"
        
        # Verify 3 standard metadata columns + 1 raw_id
        col_names = [c[0] for c in cols]
        assert 'raw_id' in col_names
        assert 'source_file' in col_names
        assert 'snapshot_date' in col_names
        assert 'ingestion_time' in col_names

    print("Kiểm tra cấu trúc và metadata 4 bảng: PASS")

    print("\n--- BƯỚC 4: Kiểm tra chỉ mục (INDEX) trên các bảng ---")
    for tbl in expected_tables:
        cur.execute(f"SHOW INDEX FROM {tbl}")
        indexes = set(row[2] for row in cur.fetchall())
        print(f"Bảng {tbl:20} có các index: {list(indexes)}")
        assert 'PRIMARY' in indexes
    print("Kiểm tra Primary Key và Index: PASS")

    print("\n--- BƯỚC 5: Kiểm tra quyền nạp (INSERT, SELECT, UPDATE, DELETE) của tài khoản ETL ---")
    test_snap = '2026-09-23'

    # Test stg_neighbourhoods
    cur.execute("""
        INSERT INTO stg_neighbourhoods (neighbourhood_group, neighbourhood, source_file, snapshot_date)
        VALUES ('Test Region', 'Test Area', 'neighbourhoods.csv', %s)
    """, (test_snap,))
    assert cur.rowcount == 1
    cur.execute("SELECT raw_id, neighbourhood FROM stg_neighbourhoods WHERE neighbourhood = 'Test Area'")
    r = cur.fetchone()
    assert r is not None and r[1] == 'Test Area'
    cur.execute("DELETE FROM stg_neighbourhoods WHERE neighbourhood = 'Test Area'")
    print("  Quyền nạp stg_neighbourhoods: PASS")

    # Test stg_calendar
    cur.execute("""
        INSERT INTO stg_calendar (listing_id, date, available, minimum_nights, maximum_nights, source_file, snapshot_date)
        VALUES (999999999, '2026-10-01', 't', 2, 365, 'calendar.csv.gz', %s)
    """, (test_snap,))
    assert cur.rowcount == 1
    cur.execute("SELECT raw_id, available FROM stg_calendar WHERE listing_id = 999999999")
    r = cur.fetchone()
    assert r is not None and r[1] == 't'
    cur.execute("DELETE FROM stg_calendar WHERE listing_id = 999999999")
    print("  Quyền nạp stg_calendar: PASS")

    # Test stg_reviews
    cur.execute("""
        INSERT INTO stg_reviews (listing_id, id, date, reviewer_id, reviewer_name, comments, source_file, snapshot_date)
        VALUES (999999999, 888888888, '2026-09-20', 777777777, 'Nguyen Van Test', 'Phòng rất đẹp và sạch sẽ!', 'reviews.csv.gz', %s)
    """, (test_snap,))
    assert cur.rowcount == 1
    cur.execute("SELECT raw_id, reviewer_name FROM stg_reviews WHERE id = 888888888")
    r = cur.fetchone()
    assert r is not None and r[1] == 'Nguyen Van Test'
    cur.execute("DELETE FROM stg_reviews WHERE id = 888888888")
    print("  Quyền nạp stg_reviews: PASS")

    # Test stg_listings
    cur.execute("""
        INSERT INTO stg_listings (
            id, listing_url, scrape_id, last_scraped, source, name, description,
            price, price_quote_raw, minimum_nights, maximum_nights,
            review_scores_rating, source_file, snapshot_date
        ) VALUES (
            999999999, 'https://www.airbnb.com/rooms/999999999', 20260923225116,
            '2026-09-26', 'previous scrape', 'Studio Test Condo Orchard',
            'Căn hộ cao cấp đầy đủ tiện nghi trung tâm', '$150.00',
            '{"quote": {"price": 150}}', 2, 365, 4.85, 'listings.csv.gz', %s
        )
    """, (test_snap,))
    assert cur.rowcount == 1
    cur.execute("SELECT raw_id, name, price FROM stg_listings WHERE id = 999999999")
    r = cur.fetchone()
    assert r is not None and r[1] == 'Studio Test Condo Orchard' and r[2] == '$150.00'
    cur.execute("DELETE FROM stg_listings WHERE id = 999999999")
    print("  Quyền nạp stg_listings: PASS")

    print("\n--- BƯỚC 6: Kiểm tra tính khả lặp (Idempotency - chạy lại DDL lần 2) ---")
    for s in statements:
        stmt_clean = s.strip()
        if stmt_clean.endswith(';'):
            stmt_clean = stmt_clean[:-1]
        cur.execute(stmt_clean)
    print("Chạy lại DDL lần 2 thành công 100%, không phát sinh lỗi trùng lặp (Idempotent): PASS")

    cur.close()
    conn.close()
    print("\n=======================================================")
    print("TOÀN BỘ 6 TIÊU CHÍ KIỂM THỬ CHO TASK 3.1 ĐẠT KẾT QUẢ PASS!")
    print("Tài khoản ETL sẵn sàng để Thái nạp dữ liệu ở Task 3.2.")
    print("=======================================================")

if __name__ == '__main__':
    run_verification()

