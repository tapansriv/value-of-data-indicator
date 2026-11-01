"""
Compressed size per column, summed over row groups, for a directory of <table>.parquet
files (the generalization of column_sizes.py, which has a hardcoded path).

    python3 tools/column_sizes_for.py --data-dir ~/tpcds_sf1_place --out sizes.json
"""
import json
import os
from argparse import ArgumentParser

import pyarrow.parquet as pq

ROOT = os.path.join(os.path.dirname(__file__), "..")

ap = ArgumentParser()
ap.add_argument("--data-dir", required=True)
ap.add_argument("--schema-file", default=os.path.join(ROOT, "metadata", "tpcds_schema_registry.json"))
ap.add_argument("--out", required=True)
args = ap.parse_args()

sizes = {}
for table, columns in json.load(open(args.schema_file)).items():
    pf = pq.ParquetFile(os.path.join(os.path.expanduser(args.data_dir), f"{table}.parquet"))
    sizes[table] = {}
    for col in columns:
        idx = pf.schema_arrow.get_field_index(col)
        sizes[table][col] = sum(pf.metadata.row_group(rg).column(idx).total_compressed_size
                                for rg in range(pf.num_row_groups))
with open(args.out, "w") as f:
    json.dump(sizes, f, indent=4, sort_keys=True)
print(f"total {sum(sum(c.values()) for c in sizes.values()) / 2**30:.3f} GiB -> {args.out}")
