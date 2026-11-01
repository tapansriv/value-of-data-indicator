'''
Generate values for each query in a query workload according to various
distributions. The workload is inferred from the "tpch_completed.json" or
"tpcds_completed.json" files that are looked for containing a newline-delimited
file of query ids for which there exists table, column, and row group access
information. 

7.22: support for normal, zipf
'''

import numpy as np
import json
import pandas as pd
import glob
from argparse import ArgumentParser
import os

parser = ArgumentParser(description="Generate Values")
parser.add_argument("distro", choices=["normal", "zipf"], help="Distribution choice")
parser.add_argument("--num-trials", type=int, default=100, help="number of trials")
args = parser.parse_args()

tpch_keys = []
tpcds_keys = []

# infer the current query set
query_set = []
tpch_keys = []
tpcds_keys = []

for qfile in sorted(glob.glob("../test/example_queries/tpch/*.sql"), key =
                    lambda x: int(os.path.basename(x).replace(".sql", ""))):
    key = os.path.basename(qfile).replace(".sql", "")
    query_set.append(("tpch", key))
    tpch_keys.append(f"query_{key}")

len_tpch = len(query_set)

qkeys = [f"0{i}" if i < 10 else f"{i}" for i in range(1, 100)]
q = [("tpcds", q) for q in qkeys]
query_set.extend(q)
tpcds_keys = [f"query_{q}" for q in qkeys]

num_queries = len(query_set)
print(num_queries)

# draw samples from underlying supported distributions
samples = []
if args.distro == "normal":
    samples = np.random.normal(50, 15, size=(num_queries, args.num_trials))
elif args.distro == "zipf":
    # using parameter of 2.0
    samples = np.random.zipf(2.0, size=(num_queries, args.num_trials))

tpch_vals =  samples[:len_tpch]
tpcds_vals = samples[len_tpch:]

# print to help manually validate results
print(tpch_vals.shape)
print(tpcds_vals.shape)
print(len(tpch_keys))
print(len(tpcds_keys))

# write resulting samples to file
df = pd.DataFrame(tpch_vals)
df["query_id"] = tpch_keys
df.to_csv("tpch_query_values.csv", index=False)

df = pd.DataFrame(tpcds_vals)
df["query_id"] = tpcds_keys
df.to_csv("tpcds_query_values.csv")


