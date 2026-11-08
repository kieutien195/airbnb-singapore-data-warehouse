"""Tạo các View KPI trên MySQL, đối chiếu số liệu và xuất kpi_sql_results.csv."""
from pathlib import Path
import os
import sys
import time
import pymysql
import pymysql.cursors
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE", "airbnb_sg_2026"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def split_sql_statements(sql_text: str):
    statements = []
    current = []
    in_comment = False
    for line in sql_text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("--"):
            continue
        current.append(line)
        if trimmed.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt.endswith(";"):
                stmt = stmt[:-1].strip()
            if stmt:
                statements.append(stmt)
            current = []
    if current:
        stmt = "\n".join(current).strip()
        if stmt:
            statements.append(stmt)
    return statements


def deploy_views(conn):
    sql_path = PROJECT_ROOT / "sql" / "04_kpi_views.sql"
    if not sql_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {sql_path}")
    
    with open(sql_path, "r", encoding="utf-8") as f:
        content = f.read()

    statements = split_sql_statements(content)
    print(f"Đang thực thi {len(statements)} câu lệnh DDL trong sql/04_kpi_views.sql...")
    
    with conn.cursor() as cur:
        for idx, stmt in enumerate(statements, 1):
            cur.execute(stmt)
    print("-> Triển khai toàn bộ các View thành công!")


def regional_raw_metrics(raw_dir):
    listings = pd.read_csv(raw_dir / "listings.csv.gz", dtype={"id": str}, low_memory=False)
    listings = listings.rename(columns={"neighbourhood_group_cleansed": "region"})
    listings["region"] = listings["region"].str.strip()
    listings["room_type"] = listings["room_type"].str.strip()
    rooms = listings.groupby(["region", "room_type"]).size()
    totals = rooms.groupby(level="region").sum()

    calendar = pd.read_csv(raw_dir / "calendar.csv.gz", dtype={"listing_id": str})
    calendar = calendar.loc[calendar["date"].between("2026-09-25", "2027-09-25")].copy()
    calendar["available"] = calendar["available"].str.strip().str.lower().map({
        "t": 1, "true": 1, "1": 1, "f": 0, "false": 0, "0": 0,
    })
    calendar = calendar.dropna(subset=["available"]).merge(
        listings[["id", "region"]], left_on="listing_id", right_on="id", validate="many_to_one"
    )
    nights = calendar.groupby("region")["available"].agg(["sum", "size"])
    ratings = listings.loc[listings["review_scores_rating"].between(1, 5)]
    ratings = ratings.groupby("region")["review_scores_rating"].agg(["sum", "size"])

    return {
        "room": {key: (count, totals[key[0]], count * 100 / totals[key[0]])
                 for key, count in rooms.items()},
        "calendar": {region: (available, count, available * 100 / count)
                     for region, available, count in nights.itertuples()},
        "rating": {region: (total, count, total / count)
                   for region, total, count in ratings.itertuples()},
    }


def reconcile_regional(rows, expected, keys, numerator, denominator, value):
    observed = {}
    for row in rows:
        key = tuple(row[column] for column in keys)
        key = key[0] if len(key) == 1 else key
        if key in observed:
            raise ValueError(f"Duplicate regional KPI group: {key}")
        observed[key] = row
    if observed.keys() != expected.keys():
        raise ValueError(f"Regional groups differ: missing={sorted(expected.keys() - observed.keys())}; "
                         f"unexpected={sorted(observed.keys() - expected.keys())}")
    for key, row in observed.items():
        num, den, raw_value = expected[key]
        variance = abs(float(row[value]) - raw_value)
        matches = (abs(float(row[numerator]) - num) < 0.00001
                   and row[denominator] == den and variance <= 0.00500001)
        yield row, {
            "expected_raw_value": round(raw_value, 4),
            "variance": round(variance, 4),
            "reconciliation_status": "PASS" if matches else "FAIL",
        }


def run_benchmark_and_collect_results(conn):
    results = []
    raw = regional_raw_metrics(PROJECT_ROOT / "data/raw")

    # Danh sách các câu truy vấn KPI và View
    benchmarks = [
        {
            "kpi_id": "KPI-01",
            "kpi_name": "Active Listings Count",
            "section": "1. Overall Core KPIs",
            "dimension": "All Singapore",
            "grain": "One listing at snapshot",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "snapshot_date = '2026-09-23' AND listing_id IS NOT NULL",
            "numerator": "COUNT(DISTINCT listing_id)",
            "denominator": "N/A",
            "unit": "Listings",
            "expected_raw": 3208.0,
            "query": "SELECT active_listings_count AS metric_value, total_snapshot_records FROM vw_kpi01_active_listings;"
        },
        {
            "kpi_id": "KPI-02",
            "kpi_name": "Median Listed Price per Night (SGD)",
            "section": "1. Overall Core KPIs",
            "dimension": "All Singapore",
            "grain": "One listing at snapshot",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "quote_currency = 'SGD' AND is_price_sgd_verified = 1 AND listed_price_sgd > 0",
            "numerator": "MEDIAN(listed_price_sgd) via CTE Window Function",
            "denominator": "N/A (Coverage: 2,725 / 3,208 listings = 84.94%)",
            "unit": "SGD/night",
            "expected_raw": 202.83,
            "query": "SELECT median_price_sgd AS metric_value, verified_listings_count FROM vw_kpi02_median_price_sgd;"
        },
        {
            "kpi_id": "KPI-03",
            "kpi_name": "Room Type Share - Entire home/apt",
            "section": "1. Overall Core KPIs",
            "dimension": "Entire home/apt",
            "grain": "One room type at snapshot",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "room_type = 'Entire home/apt'",
            "numerator": "1232 listings",
            "denominator": "3208 listings",
            "unit": "% listings",
            "expected_raw": 38.404,
            "query": "SELECT room_type_share_pct AS metric_value, listing_count, total_listings FROM vw_kpi03_room_type_share WHERE room_type = 'Entire home/apt';"
        },
        {
            "kpi_id": "KPI-03",
            "kpi_name": "Room Type Share - Private room",
            "section": "1. Overall Core KPIs",
            "dimension": "Private room",
            "grain": "One room type at snapshot",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "room_type = 'Private room'",
            "numerator": "1827 listings",
            "denominator": "3208 listings",
            "unit": "% listings",
            "expected_raw": 56.9514,
            "query": "SELECT room_type_share_pct AS metric_value, listing_count, total_listings FROM vw_kpi03_room_type_share WHERE room_type = 'Private room';"
        },
        {
            "kpi_id": "KPI-03",
            "kpi_name": "Room Type Share - Hotel room",
            "section": "1. Overall Core KPIs",
            "dimension": "Hotel room",
            "grain": "One room type at snapshot",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "room_type = 'Hotel room'",
            "numerator": "83 listings",
            "denominator": "3208 listings",
            "unit": "% listings",
            "expected_raw": 2.5873,
            "query": "SELECT room_type_share_pct AS metric_value, listing_count, total_listings FROM vw_kpi03_room_type_share WHERE room_type = 'Hotel room';"
        },
        {
            "kpi_id": "KPI-03",
            "kpi_name": "Room Type Share - Shared room",
            "section": "1. Overall Core KPIs",
            "dimension": "Shared room",
            "grain": "One room type at snapshot",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "room_type = 'Shared room'",
            "numerator": "66 listings",
            "denominator": "3208 listings",
            "unit": "% listings",
            "expected_raw": 2.0574,
            "query": "SELECT room_type_share_pct AS metric_value, listing_count, total_listings FROM vw_kpi03_room_type_share WHERE room_type = 'Shared room';"
        },
        {
            "kpi_id": "KPI-04",
            "kpi_name": "Calendar Available Nights Ratio",
            "section": "1. Overall Core KPIs",
            "dimension": "All Singapore (Window 2026-09-25 .. 2027-09-25)",
            "grain": "Listing-day records across 366-day window",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "calendar_date BETWEEN '2026-09-25' AND '2027-09-25'",
            "numerator": "SUM(is_available = 1) = 900,960 nights",
            "denominator": "COUNT(*) = 1,170,950 nights",
            "unit": "% listing-nights",
            "expected_raw": 76.9427,
            "query": "SELECT available_nights_ratio_pct AS metric_value, available_nights_count, total_nights_count FROM vw_kpi04_calendar_availability;"
        },
        {
            "kpi_id": "KPI-05",
            "kpi_name": "Average Overall Review Score",
            "section": "1. Overall Core KPIs",
            "dimension": "All Singapore",
            "grain": "One rated listing at snapshot",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "review_scores_rating IS NOT NULL AND review_scores_rating BETWEEN 1.00 AND 5.00",
            "numerator": "SUM(review_scores_rating) = 8,347.90",
            "denominator": "COUNT(review_scores_rating) = 1,839 listings (Coverage = 57.33%)",
            "unit": "Points (1.00..5.00)",
            "expected_raw": 4.5394,
            "query": "SELECT avg_review_score AS metric_value, rated_listings_count, sum_review_score FROM vw_kpi05_average_rating;"
        },
        {
            "kpi_id": "SUP-01",
            "kpi_name": "Median Review Count per Listing",
            "section": "2. Supplemental Indicators",
            "dimension": "All Singapore",
            "grain": "One listing at snapshot",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "number_of_reviews IS NOT NULL AND number_of_reviews >= 0",
            "numerator": "MEDIAN(number_of_reviews) across all 3,208 listings",
            "denominator": "N/A",
            "unit": "Reviews/listing",
            "expected_raw": 1.0,
            "query": "SELECT median_review_count AS metric_value, total_listings_count FROM vw_sup01_median_review_count;"
        },
        {
            "kpi_id": "SUP-02",
            "kpi_name": "Review Records in Period",
            "section": "2. Supplemental Indicators",
            "dimension": "All Singapore (Historical through 2026-09-25)",
            "grain": "One review record in snapshot",
            "snapshot_date": "2026-09-23",
            "filter_criteria": "snapshot_date = '2026-09-23' (Unique pair listing_id, review_id)",
            "numerator": "COUNT(*) = 46,000 reviews",
            "denominator": "N/A (Covering 1,839 distinct listings)",
            "unit": "Review records",
            "expected_raw": 46000.0,
            "query": "SELECT review_records_count AS metric_value, distinct_reviewed_listings_count FROM vw_sup02_review_records_period;"
        }
    ]

    with conn.cursor() as cur:
        for item in benchmarks:
            t0 = time.perf_counter()
            cur.execute(item["query"])
            row = cur.fetchone()
            t1 = time.perf_counter()
            elapsed_ms = round((t1 - t0) * 1000, 2)
            
            observed_val = float(row["metric_value"])
            exp_val = item["expected_raw"]
            variance = round(abs(observed_val - exp_val), 4)
            status = "PASS" if variance <= 0.05 else "FAIL"

            results.append({
                "section": item["section"],
                "kpi_id": item["kpi_id"],
                "kpi_name": item["kpi_name"],
                "dimension": item["dimension"],
                "grain": item["grain"],
                "snapshot_date": item["snapshot_date"],
                "filter_criteria": item["filter_criteria"],
                "numerator": item["numerator"],
                "denominator": item["denominator"],
                "observed_gold_value": observed_val,
                "expected_raw_value": round(exp_val, 2),
                "variance": variance,
                "reconciliation_status": status,
                "unit": item["unit"],
                "query_time_ms": elapsed_ms
            })

    # Thu thập kết quả phân rã khu vực cho Room Type, Calendar và Review
    with conn.cursor() as cur:
        # Regional Room Type
        t0 = time.perf_counter()
        cur.execute("SELECT neighbourhood_group, room_type, listing_count, regional_total_listings, room_type_share_pct FROM vw_kpi03_regional_room_type_share;")
        rows = cur.fetchall()
        t1 = time.perf_counter()
        elapsed_ms = round((t1 - t0) * 1000, 2)
        for r, reconciliation in reconcile_regional(
            rows, raw["room"], ("neighbourhood_group", "room_type"),
            "listing_count", "regional_total_listings", "room_type_share_pct",
        ):
            results.append({
                "section": "3. Regional Dimensional Breakdown",
                "kpi_id": "KPI-03-REGIONAL",
                "kpi_name": f"Room Type Share ({r['room_type']})",
                "dimension": r["neighbourhood_group"],
                "grain": "One room type per neighbourhood group",
                "snapshot_date": "2026-09-23",
                "filter_criteria": f"neighbourhood_group = '{r['neighbourhood_group']}' AND room_type = '{r['room_type']}'",
                "numerator": f"{r['listing_count']} listings",
                "denominator": f"{r['regional_total_listings']} regional listings",
                "observed_gold_value": float(r["room_type_share_pct"]),
                **reconciliation,
                "unit": "% listings",
                "query_time_ms": elapsed_ms
            })

        # Regional Calendar Availability
        t0 = time.perf_counter()
        cur.execute("SELECT neighbourhood_group, available_nights_count, total_nights_count, available_nights_ratio_pct FROM vw_kpi04_regional_calendar_availability;")
        rows = cur.fetchall()
        t1 = time.perf_counter()
        elapsed_ms = round((t1 - t0) * 1000, 2)
        for r, reconciliation in reconcile_regional(
            rows, raw["calendar"], ("neighbourhood_group",),
            "available_nights_count", "total_nights_count", "available_nights_ratio_pct",
        ):
            results.append({
                "section": "3. Regional Dimensional Breakdown",
                "kpi_id": "KPI-04-REGIONAL",
                "kpi_name": "Calendar Available Nights Ratio",
                "dimension": r["neighbourhood_group"],
                "grain": "Listing-day records per neighbourhood group",
                "snapshot_date": "2026-09-23",
                "filter_criteria": f"neighbourhood_group = '{r['neighbourhood_group']}' AND 2026-09-25..2027-09-25",
                "numerator": f"{r['available_nights_count']} available nights",
                "denominator": f"{r['total_nights_count']} total nights",
                "observed_gold_value": float(r["available_nights_ratio_pct"]),
                **reconciliation,
                "unit": "% listing-nights",
                "query_time_ms": elapsed_ms
            })

        # Regional Rating Score
        t0 = time.perf_counter()
        cur.execute("SELECT neighbourhood_group, rated_listings_count, sum_review_score, avg_review_score FROM vw_kpi05_regional_average_rating;")
        rows = cur.fetchall()
        t1 = time.perf_counter()
        elapsed_ms = round((t1 - t0) * 1000, 2)
        for r, reconciliation in reconcile_regional(
            rows, raw["rating"], ("neighbourhood_group",),
            "sum_review_score", "rated_listings_count", "avg_review_score",
        ):
            results.append({
                "section": "3. Regional Dimensional Breakdown",
                "kpi_id": "KPI-05-REGIONAL",
                "kpi_name": "Average Overall Review Score",
                "dimension": r["neighbourhood_group"],
                "grain": "Rated listings per neighbourhood group",
                "snapshot_date": "2026-09-23",
                "filter_criteria": f"neighbourhood_group = '{r['neighbourhood_group']}' AND rating IN (1..5)",
                "numerator": f"{r['sum_review_score']} total score",
                "denominator": f"{r['rated_listings_count']} rated listings",
                "observed_gold_value": float(r["avg_review_score"]),
                **reconciliation,
                "unit": "Points (1.00..5.00)",
                "query_time_ms": elapsed_ms
            })

    return results


def main():
    conn = get_connection()
    try:
        # 1. Deploy views
        deploy_views(conn)
        
        # 2. Benchmark and collect results
        print("\nĐang thực thi các câu truy vấn KPI và đo lường hiệu năng benchmark...")
        results = run_benchmark_and_collect_results(conn)
        
        # 3. Export to CSV
        df = pd.DataFrame(results)
        
        out_csv1 = PROJECT_ROOT / "kpi_sql_results.csv"
        out_csv2 = PROJECT_ROOT / "outputs" / "kpi_sql_results.csv"
        out_csv2.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(out_csv1, index=False, encoding="utf-8-sig")
        df.to_csv(out_csv2, index=False, encoding="utf-8-sig")
        print(f"\n-> Đã xuất kết quả thành công ra:")
        print(f"   1. {out_csv1}")
        print(f"   2. {out_csv2}")

        # In bảng tổng hợp
        print("\n" + "=" * 95)
        print("BẢNG TỔNG HỢP KPI GOLD WAREHOUSE & ĐỐI CHIẾU RAW (RECONCILIATION SUMMARY)")
        print("=" * 95)
        summary_cols = ["kpi_id", "dimension", "observed_gold_value", "expected_raw_value", "unit", "reconciliation_status", "query_time_ms"]
        print(df[df["section"] != "3. Regional Dimensional Breakdown"][summary_cols].to_string(index=False))
        print("=" * 95)
        
        # Kiểm tra trạng thái PASS
        all_passed = (df["reconciliation_status"] == "PASS").all()
        if all_passed:
            print("\n>>> TẤT CẢ CÁC CHỈ TIÊU KPI ĐÃ ĐỐI CHIẾU 100% PASS VỚI RAW DATA! <<<")
        else:
            print("\n>>> CẢNH BÁO: CÓ CHỈ TIÊU CHƯA KHỚP VỚI RAW DATA! <<<")
            sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
