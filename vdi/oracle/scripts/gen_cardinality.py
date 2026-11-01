'''
Write a tpcds_cardinality.json for one scale factor from the Parquet footers.

Cardinality here is the row count of each table (not distinct rows), read from the
footer of the <table>.parquet file the capture run reads. Keys follow the convention
of the existing tpcds_cardinality.json and assign_val_to_de.py: the TPC-DS customer
table is "tpcds.customer", to keep it apart from the TPC-H customer table.
'''

import json
import os
from argparse import ArgumentParser

import pyarrow.parquet as pq

TPCDS_TABLES = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]

if __name__ == "__main__":
    parser = ArgumentParser(description="Per-SF TPC-DS cardinality from Parquet footers")
    parser.add_argument("--parquet-dir", required=True, help="Directory of <table>.parquet")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    cardinality = {}
    for tbl in TPCDS_TABLES:
        path = os.path.join(args.parquet_dir, f"{tbl}.parquet")
        key = "tpcds.customer" if tbl == "customer" else tbl
        cardinality[key] = pq.ParquetFile(path).metadata.num_rows

    with open(args.out, "w") as fp:
        json.dump(cardinality, fp, indent=4)
    print(f"Wrote {len(cardinality)} tables to {args.out}")
