import csv
import gzip
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Read source_to_target_mapping to get exact staging column mappings
with open('docs/source_to_target_mapping.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    mapping = list(reader)

listings_map = [r for r in mapping if r['staging_table'] == 'stg_listings']
print(f"Total listings mapped columns: {len(listings_map)}")

for r in listings_map:
    sc = r['source_column']
    stgc = r['staging_column']
    p_dtype = r['source_pandas_dtype']
    cat = r['field_category']
    print(f"{stgc:35} | source: {sc:30} | pd: {p_dtype:10} | cat: {cat}")

