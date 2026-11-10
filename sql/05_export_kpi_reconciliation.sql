-- Task 4.2. Read-only. Run after deploying 04_kpi_views.sql on the loaded warehouse.
-- Export the single result grid as UTF-8 CSV with header to tests/kpi_workbench_42.csv.
-- From the repo root, run:
-- python scripts/reconcile_kpis.py --sql-csv tests/kpi_workbench_42.csv
-- Views fix the snapshot to 2026-09-23, Calendar to 2026-09-25..2027-09-25
-- and Reviews to 2011-05-04..2026-09-25. Both windows include the endpoints.

WITH scoped AS (
    SELECT number_of_reviews, historical_review_records
    FROM vw_gold_bi_analytical_base
    WHERE snapshot_date = '2026-09-23'
      AND neighbourhood_group = 'Central Region'
      AND room_type = 'Private room'
),
ranked_counts AS (
    SELECT number_of_reviews,
           ROW_NUMBER() OVER (ORDER BY number_of_reviews) AS rn,
           COUNT(*) OVER () AS n
    FROM scoped
    WHERE number_of_reviews >= 0
),
results AS (
    SELECT snapshot_date, 'KPI-01' AS kpi_id, 'ALL' AS region, 'ALL' AS room_type,
           active_listings_count AS metric_value, total_snapshot_records AS sample_count,
           CAST(NULL AS DECIMAL(20,2)) AS support_value
    FROM vw_kpi01_active_listings
    UNION ALL
    SELECT snapshot_date, 'KPI-02', 'ALL', 'ALL', median_price_sgd, verified_listings_count, NULL
    FROM vw_kpi02_median_price_sgd
    UNION ALL
    SELECT snapshot_date, 'KPI-03', 'ALL', room_type,
           room_type_share_pct, total_listings, listing_count
    FROM vw_kpi03_room_type_share
    UNION ALL
    SELECT snapshot_date, 'KPI-03', neighbourhood_group, room_type,
           room_type_share_pct, regional_total_listings, listing_count
    FROM vw_kpi03_regional_room_type_share
    UNION ALL
    SELECT snapshot_date, 'KPI-04', 'ALL', 'ALL',
           available_nights_ratio_pct, total_nights_count, available_nights_count
    FROM vw_kpi04_calendar_availability
    UNION ALL
    SELECT snapshot_date, 'KPI-04', neighbourhood_group, 'ALL',
           available_nights_ratio_pct, total_nights_count, available_nights_count
    FROM vw_kpi04_regional_calendar_availability
    UNION ALL
    SELECT snapshot_date, 'KPI-05', 'ALL', 'ALL', avg_review_score, rated_listings_count, sum_review_score
    FROM vw_kpi05_average_rating
    UNION ALL
    SELECT snapshot_date, 'KPI-05', neighbourhood_group, 'ALL',
           avg_review_score, rated_listings_count, sum_review_score
    FROM vw_kpi05_regional_average_rating
    UNION ALL
    SELECT snapshot_date, 'SUP-01', 'ALL', 'ALL', median_review_count, total_listings_count, NULL
    FROM vw_sup01_median_review_count
    UNION ALL
    SELECT snapshot_date, 'SUP-02', 'ALL', 'ALL', review_records_count, distinct_reviewed_listings_count, NULL
    FROM vw_sup02_review_records_period
    UNION ALL
    SELECT '2026-09-23', 'SUP-01', 'Central Region', 'Private room',
           ROUND(AVG(number_of_reviews), 2), COALESCE(MAX(n), 0), NULL
    FROM ranked_counts
    WHERE rn IN (FLOOR((n+1)/2), CEIL((n+1)/2))
    UNION ALL
    SELECT '2026-09-23', 'SUP-02', 'Central Region', 'Private room',
           COALESCE(SUM(historical_review_records), 0),
           COUNT(CASE WHEN historical_review_records > 0 THEN 1 END), NULL
    FROM scoped
)
SELECT snapshot_date, kpi_id, region, room_type,
       CAST(metric_value AS DECIMAL(20,2)) AS metric_value, sample_count, support_value
FROM results
ORDER BY kpi_id, CASE WHEN region = 'ALL' THEN 0 ELSE 1 END, region, room_type;
