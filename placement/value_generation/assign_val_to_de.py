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
        # df1 = pd.read_csv("tpch_query_values_zipf.csv")
        df2 = pd.read_csv("tpcds_query_values_custom.csv")

        # can also derive this from the number of columns (minus one) in df1.shape 
        self.num_trials = num_trials 

        # values for queries
        # df1p = df1.set_index("query_id").to_dict("index")
        df2p = df2.set_index("query_id").to_dict("index")
        self.values = {"tpcds": df2p} # {"tpch": df1p, "tpcds": df2p}

        # get relevant columns/tables for query
        # f = open("tpch_columns_in_queries.json")
        # qdict1 = json.load(f)
        f = open("tpcds_columns_in_queries.json")
        qdict2 = json.load(f)
        self.qdict = {"tpcds": qdict2} #{"tpch": qdict1, "tpcds": qdict2}
        
        # have list of all tables, columns in DB
        # tpch_columns = [x.strip() for x in open("tpch_column_names.csv").readlines()]
        tpcds_columns = [x.strip() for x in open("tpcds_column_names.csv").readlines()]
        # only using this for caching experiment with tpcds columns + queries.
        # TODO clean this all up
        self.columns = tpcds_columns  # tpch_columns + tpcds_columns

        self.tables = tpcds_tables # tpch_tables + tpcds_tables

    def get_rel_tbls(self, schema, qry):
        # get relevant tables for a query within a schema
        return self.qdict[schema][str(qry) + ".sql"]

    def get_query_value(self, schema, qry, iter_):
        return self.values[schema][f"{qry}.sql"][iter_]

parser = ArgumentParser(description="Run time-series oracle")
parser.add_argument("-n", "--num-samples", type=int, default=50, help="Number of queries that run")
parser.add_argument("--num-trials", type=int, default=100, 
                    help="Number of different value generation trials that were run")
parser.add_argument("-s", "--seed", type=int, default=0, help="Random seed")
args = parser.parse_args()

qdm = QueryDataManager(args.num_trials)

query_set = []
q = [("tpcds", f"{i:02d}") for i in range(1,100)]
query_set.extend(q)
num_queries = len(query_set)
print(query_set)
print(len(qdm.columns))


# assign frequencies (values) 
rng = np.random.default_rng(args.seed)
sampled_queries = rng.integers(num_queries, size=args.num_samples)
unique, counts = np.unique(sampled_queries, return_counts=True)

# assert len(unique) == len(counts)
# query_frequencies = {}
# for i in range(len(unique)):
#     freq = counts[i] / args.num_samples
#     query_frequencies[unique[i]] = freq


# get the total value generated from a workload this is sum of the value of each
# unique query run times the number of times it was run
# dump that to a file
# total_values = []
# for iter_ in range(qdm.num_trials):
#     tot = 0
#     for i in range(len(unique)):
#         qry_num = unique[i]
#         schema, qry = query_set[qry_num]
#         tot += (counts[i] * qdm.get_query_value(schema, qry, str(iter_)))
#     total_values.append(int(tot))
# print(total_values)
# with open("total_values.json", 'w') as fp:
#     json.dump(total_values, fp, indent=4, sort_keys=True)


# same process for the non-baseline metric
dvt = {}
dvc = {}
dvrt = {}
for iter_ in range(qdm.num_trials):
    # initialize data collection for a trial of value assignment
    data_value_for_tables = {t: 0 for t in qdm.tables}
    data_value_for_columns = {l: 0 for l in qdm.columns}

    # iterate over all queries in the sample 
    for qry_num in sampled_queries:
        # grab relevant DEs for each query
        schema, qry = query_set[qry_num]
        tbls = qdm.get_rel_tbls(schema, qry)

        rel_tbls = [t for t in tbls if len(tbls[t]) > 0]
        rel_cols = []
        for t in tbls:
            rel_cols.extend(tbls[t])

        # grab value for each query and define variables for how that value will
        # be spread across DEs
        value = qdm.get_query_value(schema, qry, str(iter_))
        tval = value / len(rel_tbls)
        cval = value / len(rel_cols)
        
        # for each DE we don't keep the list we just sum it up because too much
        # data would be generated to hold a list of all values arriving at a DE
        # for all DEs in the DB at 3 different granularities and across all N
        # trials of value generation.
        for t in rel_tbls:
            tname = t
            if schema == "tpcds" and t == "customer":
                tname = "tpcds.customer"
            data_value_for_tables[tname] += tval

        for c in rel_cols:
            data_value_for_columns[c] += cval
    
    # assign DE value assignment to the trial number
    dvt[str(iter_)] = data_value_for_tables
    dvc[str(iter_)] = data_value_for_columns

with open(f"data_val_tbls_custom.json", 'w') as fp:
    json.dump(dvt, fp, indent=4, sort_keys=True)

with open(f"data_val_cols_custom.json", 'w') as fp:
    json.dump(dvc, fp, indent=4, sort_keys=True)



# with open(f"data_val_cols_custom_1.json", 'w') as fp:
#     json.dump(dvc["0"], fp, indent=4, sort_keys=True)
# 
# with open(f"data_val_cols_custom_2.json", 'w') as fp:
#     json.dump(dvc["1"], fp, indent=4, sort_keys=True)
# 

