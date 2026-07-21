import numpy as np
import json
import pandas as pd
from argparse import ArgumentParser

parser = ArgumentParser(description="Generate Values")
parser.add_argument("distro", choices=["normal", "zipf"], help="Distribution choice")
parser.add_argument("--num-trials", type=int, default=100, help="number of trials")
parser.add_argument("--seed", type=int, default=42)
args = parser.parse_args()

tpch_keys = []
tpcds_keys = []

# infer the current query set
query_set = []
with open("../drill_logs/tpch_completed.json") as fp:
    completed = json.load(fp)
    q = [("tpch", i) for i in completed]
    query_set.extend(q)
    tpch_keys = [f"query_{i}" for i in completed]

len_tpch = len(query_set)

with open("../tpcds_drill_logs/tpcds_completed.json") as fp:
    completed = json.load(fp)
    q = [("tpcds", i) for i in completed]
    query_set.extend(q)
    tpcds_keys = [f"query_{i}" for i in completed]

num_queries = len(query_set)
print(f"Total Queries: {num_queries}, TPC-H: {len_tpch}, TPC-DS: {len(tpcds_keys)}")

# draw samples from underlying supported distributions
rng = np.random.default_rng(seed=args.seed)
samples = []
if args.distro == "normal":
    samples = rng.normal(50, 15, size=(num_queries, args.num_trials))
elif args.distro == "zipf":
    # using parameter of 2.0
    samples = rng.zipf(2.0, size=(num_queries, args.num_trials))

tpch_vals =  samples[:len_tpch]
tpcds_vals = samples[len_tpch:]

# print to help manually validate results
print(f"TPC-H Shape: {tpch_vals.shape}, TPC-DS Shape: {tpcds_vals.shape}")

# write resulting samples to file
df = pd.DataFrame(tpch_vals)
df["query_id"] = tpch_keys
df.to_csv(f"../data/tpch_query_values_{args.distro}.csv", index=False)

df = pd.DataFrame(tpcds_vals)
df["query_id"] = tpcds_keys
df.to_csv(f"../data/tpcds_query_values_{args.distro}.csv", index=False)








