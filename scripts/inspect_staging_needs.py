import gzip
import csv
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

def analyze_listings():
    with gzip.open('data/raw/listings.csv.gz', 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        stats = {k: {'nulls': 0, 'max_len': 0, 'is_int': True, 'is_float': True, 'samples': []} for k in fieldnames}
        total = 0
        for row in reader:
            total += 1
            for k, v in row.items():
                if v == '' or v is None:
                    stats[k]['nulls'] += 1
                else:
                    l = len(v)
                    if l > stats[k]['max_len']:
                        stats[k]['max_len'] = l
                    if len(stats[k]['samples']) < 2:
                        stats[k]['samples'].append(v[:30])
                    try:
                        int(v)
                    except ValueError:
                        stats[k]['is_int'] = False
                    try:
                        float(v)
                    except ValueError:
                        stats[k]['is_float'] = False

        print(f"Total rows: {total}")
        for k in fieldnames:
            s = stats[k]
            print(f"{k:35} | nulls: {s['nulls']:4} | max_l: {s['max_len']:4} | int: {str(s['is_int']):5} | flt: {str(s['is_float']):5} | samples: {s['samples']}")

if __name__ == '__main__':
    analyze_listings()

