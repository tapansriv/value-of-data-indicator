import json 
import os
import pandas as pd
import numpy as np
from argparse import ArgumentParser
import glob

tpch_tables = ["nation", "region", "part", "supplier", "partsupp", "customer", "orders", "lineitem"]

tpcds_tables = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "tpcds.customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]

# class to abstract away accessing information about queries
class QueryDataManager:
    def __init__(self, num_trials):
        # can also derive this from the number of columns (minus one) in df.shape 
        self.num_trials = num_trials 

        # values for queries
        df = pd.read_csv("tpcds_query_values_custom_v2.csv")
        df = df.set_index("query_id").to_dict("index")
        self.values = {"tpcds": df}

        # get relevant columns/tables for query
        f = open("tpcds_columns_in_queries.json")
        qdict2 = json.load(f)
        self.qdict = {"tpcds": qdict2} #{"tpch": qdict1, "tpcds": qdict2}
        f.close()

        # have list of all tables, columns in DB
        tpcds_columns = [x.strip() for x in open("tpcds_column_names.csv").readlines()]
        self.columns = tpcds_columns 
        self.tables = tpcds_tables

    def get_rel_tbls(self, schema, qry):
        # get relevant tables for a query within a schema
        return self.qdict[schema][str(qry) + ".sql"]

    def get_query_value(self, schema, qry, iter_):
        return self.values[schema][f"query_{qry}"][iter_]

parser = ArgumentParser(description="Run time-series oracle")
parser.add_argument("-n", "--num-samples", type=int, default=50, help="Number of queries that run")
parser.add_argument("--num-trials", type=int, default=100, 
                    help="Number of different value generation trials that were run")
parser.add_argument("-s", "--seed", type=int, default=0, help="Random seed")
args = parser.parse_args()



qdm = QueryDataManager(args.num_trials)
query_set = [("tpcds", f"{i:02d}") for i in range(1,100)]
num_queries = len(query_set)
print(query_set)
print(len(qdm.columns))

# assign frequencies (values) 
rng = np.random.default_rng(args.seed)
sampled_queries = rng.integers(num_queries, size=args.num_samples)
unique, counts = np.unique(sampled_queries, return_counts=True)

for qry_num in unique:
    print(f"Query {query_set[qry_num]} ran {counts[qry_num]}")


dvcol = {}
freq_col = {}
for iter_ in range(qdm.num_trials):
    # initialize data collection for a trial of value assignment
    data_value_for_columns = {l: 0 for l in qdm.columns}
    frequency_for_columns = {l: 0 for l in qdm.columns}

    # iterate over all queries in the sample 
    for qry_num in sampled_queries:
        # grab relevant DEs for each query
        schema, qry = query_set[qry_num]
        tbls = qdm.get_rel_tbls(schema, qry)

        rel_cols = []
        for t in tbls:
            rel_cols.extend(tbls[t])
        # grab value for each query and define variables for how that value will
        # be spread across DEs
        value = qdm.get_query_value(schema, qry, str(iter_))
        cval = value / len(rel_cols)
        
        # for each DE we don't keep the list we just sum it up because too much
        # data would be generated to hold a list of all values arriving at a DE
        # for all DEs in the DB at 3 different granularities and across all N
        # trials of value generation.
        for c in rel_cols:
            data_value_for_columns[c] += cval
            frequency_for_columns[c] += 1

    # assign DE value assignment to the trial number
    dvcol[str(iter_)] = data_value_for_columns
    freq_col[str(iter_)] = frequency_for_columns

with open(f"data_val_cols_custom_raw.json", 'w') as fp:
    json.dump(dvcol, fp, indent=4, sort_keys=True)

with open(f"frequency_cols_custom.json", 'w') as fp:
    json.dump(freq_col["0"], fp, indent=4, sort_keys=True)

with open(f"data_val_cols_custom_1.json", 'w') as fp:
    json.dump(dvcol["0"], fp, indent=4, sort_keys=True)
# 
# with open(f"data_val_cols_custom_2.json", 'w') as fp:
#     json.dump(dvcol["1"], fp, indent=4, sort_keys=True)


