#!/usr/bin/env python3

"""
Scan all TPC-DS queries in:
  /Users/tapansriv/s3-column-cache/test/example_queries/tpcds

Use sqlglot to parse each query and count:
  1. Unique referenced columns per query
  2. Percent of total TPCDS columns referenced

Output printed to stdout.
"""
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm, uniform, lognorm, gamma, kstest, probplot
import json
import pathlib
import sqlglot
import pandas as pd
from sqlglot.optimizer.scope import traverse_scope

QUERY_DIR = pathlib.Path("/Users/tapansriv/s3-column-cache/test/example_queries/tpcds")
SCHEMA_FILE = pathlib.Path("/Users/tapansriv/s3-column-cache/schema/tpcds_schema_registry.json")

def load_columns(schema_path):
    """Return schema dict and set of fully-qualified columns."""
    with open(schema_path, "r") as f:
        schema = json.load(f)

    # schema format assumed: {table: [col1, col2, ...]}
    all_cols = {f"{t}.{c}": [] for t, cols in schema.items() for c in cols}
    schema_cols = []
    for t, cols in schema.items():
        schema_cols.extend(cols)

    f = [x.strip() for x in open("../value_generation/tpcds_column_names.csv").readlines()]
    for col in f:
        if col not in schema_cols:
            print(f"Unknown column in CSV: {col}")
    return schema, all_cols

def extract_columns(query, schema):
    """Parse SQL, walk scopes, extract referenced table.column pairs."""
    cols = set()

    try:
        parsed = sqlglot.parse_one(query)
    except Exception:
        return cols  # Skip unparseable queries

    for scope in traverse_scope(parsed):
        for expr in scope.columns:
            table = expr.table
            col = expr.name
            if table not in schema and table != "":
                continue  # skip unknown tables

            # fully qualified hit
            if table and col:
                if col in schema[table]:
                    cols.add(f"{table}.{col}")
            else:
                # resolve implicitly if table omitted
                for t, cs in schema.items():
                    if col in cs:
                        cols.add(f"{t}.{col}")
                        break
    return cols

def print_stats(all_cols):
    total_cols = len(all_cols)
    sorted_list = sorted(all_cols.items(), key=lambda item: len(item[1]),
                         reverse=True)
    cnt = 0
    for col, lst in sorted_list:
        if len(lst) == 0:
            cnt += 1
        else:
            print(f"{col}: referenced {len(lst)} queries")
    print(cnt)
    print(total_cols)

def remove_queries(data, columns_to_remove):
    queries_to_remove = set()
    for col in columns_to_remove:
        # col1 = "store_returns.sr_item_sk"
        queries_col = data[col]
        queries_to_remove.update(queries_col)

    new_vals = {}
    for col, lst in data.items():
        diff_queries = set(lst).difference(set(queries_to_remove))
        new_vals[col] = list(diff_queries)
    print_stats(new_vals)
    print(len(queries_to_remove))
    return new_vals, queries_to_remove

def main():
    schema, all_cols = load_columns(SCHEMA_FILE)
    total_cols = len(all_cols)
    query_set = []

    for query_file in sorted(QUERY_DIR.glob("*.sql")):
        sql_text = query_file.read_text()
        found_cols = extract_columns(sql_text, schema)
        for col in found_cols:
            assert col in all_cols, f"Unknown column {col} in {query_file.name}"
            all_cols[col].append(query_file.name)
        query_set.append(query_file.name)
        # print(f"Processing {query_file.name}, found {found_cols} columns")
        # count = len(found_cols)
        # pct = (count / total_cols * 100) if total_cols else 0
        # print(f"{query_file.name}: {count} cols ({pct:.2f}% of {total_cols})")
    print_stats(all_cols)
    # print('====================')

    # col1 = "store_returns.sr_item_sk"
    # new_data, query_tier = remove_queries(all_cols, [col1])

    # print('====================')
    # cols = ["store_sales.ss_item_sk", "catalog_sales.cs_item_sk"]
    # new_data2, query_tier2 = remove_queries(new_data, cols)

    # remainder = list(set(query_set).difference(query_tier).difference(query_tier2))
    # print(len(remainder))

    # d_ = { "tier_1": sorted(list(query_tier)), "tier_2": sorted(list(query_tier2)), "tier_3": sorted(remainder) }
    # with open("tpcds_query_tiers.json", "w") as f:
    #     json.dump(d_, f, indent=4)


    # values = []
    # values2 = []
    # query_keys = []
    # for q in query_set:
    #     query_keys.append(f"query_{q[:2]}")
    #     if q in query_tier:
    #         values.append(100)
    #         values2.append(40)
    #     elif q in query_tier2:
    #         values.append(10)
    #         values2.append(4)
    #     else:
    #         values.append(1)
    #         values2.append(2)
    # df = pd.DataFrame({ "query_id": query_keys, "0": values, "1": values2 })
    # # df.to_csv("../value_generation/tpcds_query_values_custom.csv", index=True)




if __name__ == "__main__":
    main()
