'''
Parse what columns are in each query in the TPCDS schema

TODO: 
    - make query numbers not hard coded
'''

import json
import re
import os
from argparse import ArgumentParser

parser = ArgumentParser(description="Columns referenced by each TPC-DS query")
parser.add_argument("--query-dir", default="../../tpcds_queries",
                    help="Directory of query files")
parser.add_argument("--pattern", default="{}_drill2.sql",
                    help="Query file name, with {} for the query number. The Spark "
                         "set in spark-lineage-api/benchmarking/tpcds_queries_spark "
                         "uses query{}.sql")
parser.add_argument("--queries", default="1-131", help="Query number range, inclusive")
parser.add_argument("--out-dir", default="../data",
                    help="Where to write tpcds_columns_in_queries.{json,csv}")
args = parser.parse_args()


tpcds_names = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "tpcds.customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]

# build the column prefixes for each table 
prefixes = {}
for tbl in tpcds_names: 
    if tbl == "inventory": 
        prefixes["inv_"] = tbl
    elif tbl == "web_site": 
        prefixes["web_"] = tbl
    elif tbl == "tpcds.customer":
        prefixes["c_"] = tbl
    elif "_" in tbl and tbl != "date_dim" and tbl != "time_dim":
        parts = tbl.split("_")
        assert len(parts) == 2
        p = f"{parts[0][0]}{parts[1][0]}_"
        prefixes[p] = tbl
    else: 
        prefixes[tbl[0] + "_"] = tbl

# full list of column names in TPCDS
column_names = [x.strip() for x in open("../../tpcds_schema/tpcds_column_names.csv").readlines()]

# map each column name to the table it's contained within
col_to_tbl = {}
for col in column_names:
    out = []
    for p in prefixes:
        if col.startswith(p):
            out.append(prefixes[p])
    assert len(out) == 1
    col_to_tbl[col] = out[0]


# hard coded query range
lo, hi = (int(x) for x in args.queries.split("-"))
queries = [i for i in range(lo, hi + 1)]
outputs = {q: {t: [] for t in tpcds_names} for q in queries}

# Match whole identifiers only, after stripping SQL comments. A substring test
# credited d_date for d_date_sk, t_time for t_time_sk, i_manufact for
# i_manufact_id, p_cost for *_ext_ship_cost, s_store_sk for ss_store_sk, and
# columns named in commented-out SQL (fixed 2026-10-07, see
# r2d7_results/RESULTS_NOTE.md).
for query in queries:
    fl = os.path.join(args.query_dir, args.pattern.format(query))
    text = open(fl).read()
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"--[^\n]*", " ", text)
    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
    for col in column_names:
        if col in identifiers:
            outputs[query][col_to_tbl[col]].append(col)


for query in queries:
    for tbl in tpcds_names:
        lst = outputs[query][tbl]
        outputs[query][tbl] = sorted(list(set(lst)))


# write this out to json and csv
os.makedirs(args.out_dir, exist_ok=True)
with open(os.path.join(args.out_dir, "tpcds_columns_in_queries.json"), 'w') as fp:
    json.dump(outputs, fp, indent=4)

ret = []
for query in queries:
    for tbl in tpcds_names:
        for col in outputs[query][tbl]:
            line = f"{tbl}, {col}, query_{query}"
            ret.append(line)

with open(os.path.join(args.out_dir, "tpcds_columns_in_queries.csv"), 'w') as fp:
    for l in ret:
        fp.write(f"{l}\n")
