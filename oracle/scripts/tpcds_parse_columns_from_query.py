'''
Parse what columns are in each query in the TPCDS schema

TODO: 
    - make query numbers not hard coded
'''

import json
import re
import os


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
queries = [i for i in range(1, 132)]
outputs = {q: {t: [] for t in tpcds_names} for q in queries}

# dont need regex since we have full list of all column names. Also don't need
# validation in the same way
for query in queries:
    fl = f"../../tpcds_queries/{query}_drill2.sql"
    lines = [line for line in open(fl).readlines()]
    for line in lines:
        for col in column_names:
            if col in line:
                outputs[query][col_to_tbl[col]].append(col)


for query in queries:
    for tbl in tpcds_names:
        lst = outputs[query][tbl]
        outputs[query][tbl] = sorted(list(set(lst)))


# write this out to json and csv
with open("../data/tpcds_columns_in_queries.json", 'w') as fp:
    json.dump(outputs, fp, indent=4)

ret = []
for query in queries:
    for tbl in tpcds_names:
        for col in outputs[query][tbl]:
            line = f"{tbl}, {col}, query_{query}"
            ret.append(line)

with open('../data/tpcds_columns_in_queries.csv', 'w') as fp:
    for l in ret:
        fp.write(f"{l}\n")
