import matplotlib.pyplot as plt
import json
import numpy as np
import re
from argparse import ArgumentParser

parser = ArgumentParser(description="Run time-series oracle")
parser.add_argument("--num-trials", type=int, default=100, 
                    help="Number of different value generation trials that were run")
args = parser.parse_args()
def sum_agg(data):
    output = {k: sum(data[k]) for k in data}
    return output
    
def avg_agg(data):
    output = {}
    for k in data:
        if len(data[k]) > 0:
            output[k] = float(float(sum(data[k])) / float(len(data[k])))
        else: 
            output[k] = 0
    return output

# TPCH/TPCDS tables and columns
tpcds_tables = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "tpcds.customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]

tpch_tables = ["nation", "region", "part", "supplier", "partsupp", "customer", "orders", "lineitem"]
assert len(set(tpcds_tables) & set(tpch_tables)) == 0
tables = tpcds_tables + tpch_tables


tpch_cols_in_tbls = json.load(open("tpch_columns_in_tables.json"))
tpcds_cols_in_tbls = json.load(open("tpcds_columns_in_tables.json"))

# accumulate data for the value-based DE assignment
total_values = json.load(open("total_values.json"))

data_column_values = json.load(open(f"data_val_cols.json"))
data_table_values = json.load(open(f"data_val_tbls.json"))

data_column_table_final = {tbl: [] for tbl in tables}
data_table_values_final = {tbl: [] for tbl in tables}

for iter_ in range(args.num_trials):
    iter_key = str(iter_)

    column_values = data_column_values[iter_key]
    table_values = data_table_values[iter_key]

    total_value = total_values[iter_]

    data_column_table_aggregates = {tbl: [] for tbl in tables}
    for col in column_values:
        matches = []
        for tbl in tpch_cols_in_tbls:
            if col in tpch_cols_in_tbls[tbl]:
                matches.append(tbl)

        for tbl in tpcds_cols_in_tbls:
            if col in tpcds_cols_in_tbls[tbl]:
                if tbl == "customer":
                    matches.append("tpcds.customer")
                else:
                    matches.append(tbl)

        assert len(matches) == 1, f"{matches}"
        data_column_table_aggregates[matches[0]].append(column_values[col])
    
    data_column_table_aggregates = avg_agg(data_column_table_aggregates)
    for tbl in data_column_table_final: 
        data_column_table_final[tbl].append(data_column_table_aggregates[tbl] / total_value)
        

    for tbl in data_table_values_final:
        data_table_values_final[tbl].append(table_values[tbl] / total_value)

