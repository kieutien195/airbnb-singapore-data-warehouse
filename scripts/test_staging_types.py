import gzip
import csv
import sys
import datetime

sys.stdout.reconfigure(encoding='utf-8')

def test_dry_run():
    print("Testing dry run against DDL types...")
    # 1. Neighbourhoods
    with open('data/raw/neighbourhoods.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            assert len(r['neighbourhood_group']) <= 100
            assert len(r['neighbourhood']) <= 100
    print("Neighbourhoods OK (55 rows)")

    # 2. Calendar
    with gzip.open('data/raw/calendar.csv.gz', 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for r in reader:
            count += 1
            int(r['listing_id'])
            datetime.date.fromisoformat(r['date'])
            assert r['available'] in ('t', 'f')
            int(r['minimum_nights'])
            int(r['maximum_nights'])
    print(f"Calendar OK ({count} rows)")

    # 3. Reviews
    with gzip.open('data/raw/reviews.csv.gz', 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for r in reader:
            count += 1
            int(r['listing_id'])
            int(r['id'])
            datetime.date.fromisoformat(r['date'])
            int(r['reviewer_id'])
            assert len(r['reviewer_name']) <= 255
    print(f"Reviews OK ({count} rows)")

    # 4. Listings
    with gzip.open('data/raw/listings.csv.gz', 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for r in reader:
            count += 1
            int(r['id'])
            assert len(r['listing_url']) <= 255
            int(r['scrape_id'])
            datetime.date.fromisoformat(r['last_scraped'])
            assert len(r['name']) <= 500
            assert len(r['picture_url']) <= 500
            int(r['host_id'])
            assert len(r['host_name']) <= 255
            float(r['latitude'])
            float(r['longitude'])
            assert len(r['property_type']) <= 100
            assert len(r['room_type']) <= 50
            if r['price_quote_checkin_date']: datetime.date.fromisoformat(r['price_quote_checkin_date'])
            if r['price_quote_checkout_date']: datetime.date.fromisoformat(r['price_quote_checkout_date'])
            if r['price_quote_total_price']: float(r['price_quote_total_price'])
            if r['price_quote_price_per_night']: float(r['price_quote_price_per_night'])
            if r['calendar_last_scraped']: datetime.date.fromisoformat(r['calendar_last_scraped'])
            if r['first_review']: datetime.date.fromisoformat(r['first_review'])
            if r['last_review']: datetime.date.fromisoformat(r['last_review'])
            if r['review_scores_rating']: float(r['review_scores_rating'])
            if r['reviews_per_month']: float(r['reviews_per_month'])
    print(f"Listings OK ({count} rows)")

if __name__ == '__main__':
    test_dry_run()

