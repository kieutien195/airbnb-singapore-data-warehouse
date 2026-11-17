# Warehouse ERD – Task 3.5

## Grain đã duyệt

| Bảng | Grain (một dòng đại diện) | Khóa nghiệp vụ duy nhất |
|---|---|---|
| `dim_date` | Một ngày lịch | `full_date` |
| `dim_neighbourhood` | Một khu vực quy hoạch thuộc một vùng | `(neighbourhood_group, neighbourhood_name)` |
| `dim_listing` | Một tin đăng ở một snapshot | `(listing_id, snapshot_date)` |
| `fact_listing_snapshot` | Một tin đăng ở một snapshot | `(listing_id, snapshot_date)` |
| `fact_calendar` | Một tin đăng ở một ngày lịch trong một snapshot | `(listing_id, calendar_date, snapshot_date)` |
| `fact_review` | Một review của một listing trong một snapshot | `(listing_id, review_id, snapshot_date)` |

## Sơ đồ quan hệ

```mermaid
erDiagram
    dim_date ||--o{ dim_listing : snapshot_date
    dim_listing ||--o{ fact_listing_snapshot : listing_snapshot
    dim_neighbourhood ||--o{ fact_listing_snapshot : geography
    dim_date ||--o{ fact_listing_snapshot : snapshot_date
    dim_listing ||--o{ fact_calendar : listing_snapshot
    dim_neighbourhood ||--o{ fact_calendar : geography
    dim_date ||--o{ fact_calendar : calendar_date
    dim_date ||--o{ fact_calendar : snapshot_date
    dim_listing ||--o{ fact_review : listing_snapshot
    dim_neighbourhood ||--o{ fact_review : geography
    dim_date ||--o{ fact_review : review_date
    dim_date ||--o{ fact_review : snapshot_date

    dim_date {
        INT date_sk PK
        DATE full_date UK
    }
    dim_neighbourhood {
        INT neighbourhood_sk PK
        VARCHAR neighbourhood_group UK
        VARCHAR neighbourhood_name UK
        DATE snapshot_date
    }
    dim_listing {
        BIGINT listing_sk PK
        BIGINT listing_id UK
        DATE snapshot_date UK
        INT snapshot_date_sk FK
        INT neighbourhood_sk FK
        DECIMAL latitude
        DECIMAL longitude
    }
    fact_listing_snapshot {
        BIGINT listing_snapshot_sk PK
        BIGINT listing_sk FK
        INT neighbourhood_sk FK
        INT snapshot_date_sk FK
        BIGINT listing_id UK
        DATE snapshot_date UK
        DECIMAL listed_price_sgd
    }
    fact_calendar {
        BIGINT calendar_sk PK
        BIGINT listing_sk FK
        INT neighbourhood_sk FK
        INT calendar_date_sk FK
        INT snapshot_date_sk FK
        BIGINT listing_id UK
        DATE calendar_date UK
        DATE snapshot_date UK
        BOOLEAN is_available
    }
    fact_review {
        BIGINT review_sk PK
        BIGINT listing_sk FK
        INT neighbourhood_sk FK
        INT review_date_sk FK
        INT snapshot_date_sk FK
        BIGINT listing_id UK
        BIGINT review_id UK
        DATE review_date
        DATE snapshot_date UK
    }
```

Các Fact tham chiếu `dim_listing` bằng bộ `(listing_sk, snapshot_date_sk, neighbourhood_sk)`. Khóa ngoại ghép này ngăn Fact gắn listing với snapshot hoặc khu vực khác. Mỗi Fact giữ UNIQUE theo đúng business grain để chặn nạp trùng cùng snapshot. `fact_calendar` và `fact_review` là các grain chi tiết riêng; không nối trực tiếp hai bảng này rồi cộng số listing. KPI cấp listing phải lấy từ `fact_listing_snapshot` hoặc tổng hợp từng Fact về grain đích trước khi kết hợp.

DDL vật lý: [`sql/02_warehouse_schema.sql`](../sql/02_warehouse_schema.sql). Bảng ánh xạ nguồn–đích: [`source_to_target_mapping.csv`](source_to_target_mapping.csv).
