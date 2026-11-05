"""Validate raw CSV values against the non-lossy staging contract (read-only)."""
from __future__ import annotations

import csv
import gzip
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_LISTINGS = ROOT / "data" / "raw" / "listings.csv.gz"
STAGING_DDL = ROOT / "sql" / "01_staging_schema.sql"
SILVER_DDL = ROOT / "sql" / "02_warehouse_schema_draft.sql"


def main() -> int:
    if not RAW_LISTINGS.is_file():
        raise FileNotFoundError(f"Raw data file not found: {RAW_LISTINGS}")
    staging = STAGING_DDL.read_text(encoding="utf-8")
    silver = SILVER_DDL.read_text(encoding="utf-8")
    if not re.search(r"^\s*latitude\s+VARCHAR\(50\)", staging, re.M | re.I):
        raise AssertionError("stg_listings.latitude must keep the source text using VARCHAR(50).")
    if not re.search(r"^\s*longitude\s+VARCHAR\(50\)", staging, re.M | re.I):
        raise AssertionError("stg_listings.longitude must keep the source text using VARCHAR(50).")
    if not re.search(r"^\s*latitude\s+DECIMAL\(10,\s*7\)", silver, re.M | re.I):
        raise AssertionError("Silver dim_listing.latitude must normalize to DECIMAL(10,7).")
    if not re.search(r"^\s*longitude\s+DECIMAL\(10,\s*7\)", silver, re.M | re.I):
        raise AssertionError("Silver dim_listing.longitude must normalize to DECIMAL(10,7).")

    rows = 0
    non_null_coordinates = 0
    coordinates_with_more_than_8_decimals = 0
    listings_with_more_than_8_decimals: set[str] = set()
    max_text_length = 0
    with gzip.open(RAW_LISTINGS, "rt", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"latitude", "longitude"}
        if not required.issubset(reader.fieldnames or []):
            raise AssertionError(f"CSV is missing coordinate columns: {sorted(required - set(reader.fieldnames or []))}")
        for line_number, row in enumerate(reader, start=2):
            rows += 1
            for name in ("latitude", "longitude"):
                raw_value = row[name]
                if raw_value in (None, ""):
                    continue
                if not re.fullmatch(r"-?\d+(?:\.\d+)?", raw_value):
                    raise AssertionError(f"{name} CSV row {line_number} has a non-numeric {name} value: {raw_value!r}")
                non_null_coordinates += 1
                max_text_length = max(max_text_length, len(raw_value))
                decimals = raw_value.partition(".")[2]
                if len(decimals) > 8:
                    coordinates_with_more_than_8_decimals += 1
                    listings_with_more_than_8_decimals.add(row.get("id", str(line_number)))
    if rows == 0 or non_null_coordinates == 0:
        raise AssertionError("No listing rows or valid coordinates were found in raw CSV.")
    if coordinates_with_more_than_8_decimals == 0:
        raise AssertionError("No coordinates exceed 8 decimal places; this dataset does not demonstrate the precision-loss case.")
    if max_text_length > 50:
        raise AssertionError(f"VARCHAR(50) is too short for the longest coordinate ({max_text_length} chars).")

    print(f"[PASS] Read {rows:,} listings and {non_null_coordinates:,} non-NULL coordinate values.")
    print(f"[PASS] {coordinates_with_more_than_8_decimals:,} coordinate values in {len(listings_with_more_than_8_decimals):,} listings have more than 8 decimal places and remain source text.")
    print(f"[PASS] Longest coordinate is {max_text_length} chars; Staging VARCHAR(50), Silver DECIMAL(10,7).")
    return 0


if __name__ == "__main__":
    main()
