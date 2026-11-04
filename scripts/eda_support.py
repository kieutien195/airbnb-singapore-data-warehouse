"""Các phép tính EDA độc lập; không thay đổi DataFrame hoặc file raw."""
import json
import numpy as np
import pandas as pd


def parse_listed_price(values):
    text = values.astype("string").str.strip()
    text = text.str.replace("$", "", regex=False).str.replace(",", "", regex=False)
    return pd.to_numeric(text, errors="coerce")


def extract_currency(value):
    if pd.isna(value):
        return "MISSING_JSON"
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return "INVALID_JSON"
    quote = payload.get("quote") if isinstance(payload, dict) else None
    currency = quote.get("currency") if isinstance(quote, dict) else None
    return currency.strip().upper() if isinstance(currency, str) and currency.strip() else "MISSING_CURRENCY"


def prepare_prices(listings):
    listed = parse_listed_price(listings["price"])
    quote = pd.to_numeric(listings["price_quote_price_per_night"], errors="coerce")
    currency = listings["price_quote_raw"].map(extract_currency)
    listed_valid = listed.notna() & np.isfinite(listed) & listed.gt(0)
    quote_valid = quote.notna() & np.isfinite(quote) & quote.gt(0)
    sgd = currency.eq("SGD")
    return pd.DataFrame({
        "listing_id": listings["id"], "listed_price_numeric": listed,
        "quote_price_numeric": quote, "currency": currency,
        "listed_price_sgd": listed.where(listed_valid & sgd),
        "quote_price_sgd": quote.where(quote_valid & sgd),
    })


def compare_prices(prices):
    """Đối chiếu hai giá trên cùng tập listing có đủ giá SGD hợp lệ."""
    pairs = prices.dropna(subset=["listed_price_sgd", "quote_price_sgd"])
    delta = pairs["listed_price_sgd"] - pairs["quote_price_sgd"]
    return pd.DataFrame([{
        "matched_listing_count": len(pairs),
        "listed_median_same_sample_sgd": pairs["listed_price_sgd"].median(),
        "quote_median_same_sample_sgd": pairs["quote_price_sgd"].median(),
        "price_difference_over_0_005_sgd": int(delta.abs().gt(0.005).sum()),
        "max_abs_difference_sgd": delta.abs().max(),
    }])


def reconcile_reviews(listings, reviews):
    """Đối chiếu số review Listings với toàn bộ lịch sử trong file Reviews.

    Đếm khóa (listing_id,id) phân biệt trong tập có khóa/ngày hợp lệ.
    Không sửa raw hay chọn một dòng để ghi đè khi khóa trùng. Số 0 ở count
    của file nghĩa là không tìm thấy review trong file; NULL từ Listings giữ NULL.
    """
    if listings["id"].isna().any() or listings["id"].duplicated().any():
        raise ValueError("Listings.id phải đầy đủ và duy nhất trong snapshot.")
    valid = reviews[["listing_id", "id"]].notna().all(axis=1)
    valid &= pd.to_datetime(reviews["date"], errors="coerce").notna()
    for column in ("listing_id", "id"):
        number = pd.to_numeric(reviews[column], errors="coerce")
        valid &= number.notna() & np.isfinite(number) & number.gt(0) & number.mod(1).eq(0)
    counts = reviews.loc[valid].groupby("listing_id")["id"].nunique()
    result = listings[["id", "neighbourhood_cleansed", "room_type", "number_of_reviews"]].copy()
    result = result.rename(columns={"id": "listing_id", "number_of_reviews": "listing_review_count"})
    result["observed_review_records"] = result["listing_id"].map(counts).fillna(0).astype("int64")
    number = pd.to_numeric(result["listing_review_count"], errors="coerce")
    valid_number = number.notna() & np.isfinite(number) & number.ge(0) & number.mod(1).eq(0)
    result["listing_review_count"] = number.where(valid_number)
    result["difference_listing_minus_file"] = result["listing_review_count"] - result["observed_review_records"]
    result["comparison_status"] = np.select(
        [~valid_number, result["difference_listing_minus_file"].eq(0)],
        ["LISTINGS_COUNT_MISSING_OR_INVALID", "MATCH"], default="DIFFERENT")
    summary = pd.DataFrame([{
        "listing_count": len(result),
        "matched_listings": int(result["comparison_status"].eq("MATCH").sum()),
        "different_listings": int(result["comparison_status"].eq("DIFFERENT").sum()),
        "missing_or_invalid_listings_count": int((~valid_number).sum()),
        "valid_review_rows": int(valid.sum()),
        "unique_review_keys": int(counts.sum()),
        "review_records_linked_to_listings": int(result["observed_review_records"].sum()),
        "review_records_not_linked_to_listings": int(counts.loc[~counts.index.isin(result["listing_id"])].sum()),
        "scope": "All valid review dates in supplied file; one Listings snapshot",
    }])
    groups = []
    for column in ("neighbourhood_cleansed", "room_type"):
        grouped = result.groupby(column, dropna=False).agg(
            listing_count=("listing_id", "size"),
            listings_with_valid_review_count=("listing_review_count", "count"),
            median_listing_review_count=("listing_review_count", "median"),
            total_observed_review_records=("observed_review_records", "sum"),
        ).reset_index().rename(columns={column: "group_value"})
        grouped.insert(0, "group_dimension", column)
        groups.append(grouped)
    return result, summary, pd.concat(groups, ignore_index=True)
