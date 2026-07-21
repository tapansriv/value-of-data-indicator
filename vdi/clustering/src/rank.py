import os
import json
from argparse import ArgumentParser
import numpy as np


parser = ArgumentParser()
parser.add_argument("--value-iter", type=str, default="0", help="iteration")
args = parser.parse_args()

HOME = os.path.expanduser("~")
SRC_DIR = os.path.join(HOME, "tpcds_30gb")

OUT_VALUE_DIR = os.path.join(HOME, "tpcds_cluster_vod")
OUT_FREQ_DIR = os.path.join(HOME, "tpcds_cluster_freq")
OUT_RAND_DIR = os.path.join(HOME, "tpcds_cluster_rand")

VALUE_JSON = "../value_generation/data_val_cols_custom.json"
FREQ_JSON = "../value_generation/frequency_cols_custom.json"
TABLES_JSON = "../value_generation/tpcds_columns_in_tables.json"

RANDOM_SEED = 42
NUM_TABLES = 2
NUM_COLS_PER_TABLE = 2


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


col_value = load_json(VALUE_JSON)[args.value_iter]
col_freq = load_json(FREQ_JSON)
table_columns = load_json(TABLES_JSON)

# Aggregate per table
table_value = {}
table_freq = {}

for table, cols in table_columns.items():
    table_value[table] = sum(col_value.get(c, 0.0) for c in cols)
    table_freq[table] = sum(col_freq.get(c, 0.0) for c in cols)

# Rank tables
top_value_tables = sorted(table_value, key=table_value.get,
                          reverse=True)[:NUM_TABLES]
top_freq_tables = sorted(table_freq, key=table_freq.get,
                         reverse=True)[:NUM_TABLES]


def top_cols_by_metric(cols, metric_dict):
    return sorted(cols, key=lambda c: metric_dict.get(c, 0.0),
                  reverse=True)[:NUM_COLS_PER_TABLE]


# ----------------------------
# Rewrite VALUE tables
# ----------------------------

output = {}

print("\n===== CHOOSING VALUE TABLES =====")
ensure_dir(OUT_VALUE_DIR)
output["value"] = {}

for table in top_value_tables:
    cols = table_columns[table]
    part_cols = top_cols_by_metric(cols, col_value)
    output["value"][table] = part_cols
    print(f"{table} and {part_cols}")


# ----------------------------
# Rewrite FREQUENCY tables
# ----------------------------

print("\n===== CHOOSING FREQUENCY TABLES =====")
ensure_dir(OUT_FREQ_DIR)
output["frequency"] = {}

for table in top_freq_tables:
    cols = table_columns[table]
    part_cols = top_cols_by_metric(cols, col_freq)
    output["frequency"][table] = part_cols
    print(f"{table} and {part_cols}")



print("\n===== CHOOSING RANDOM BASELINE TABLES =====")
ensure_dir(OUT_RAND_DIR)
output["random"] = {}

np.random.seed(RANDOM_SEED)
all_tables = list(table_columns.keys())
random_tables = np.random.choice(all_tables, size=NUM_TABLES, replace=False)

for table in random_tables:
    cols = table_columns[table]
    if len(cols) < NUM_COLS_PER_TABLE:
        raise ValueError(f"Table {table} has fewer than {NUM_COLS_PER_TABLE} columns")
    random_cols = np.random.choice(cols, size=NUM_COLS_PER_TABLE, replace=False).tolist()
    output["random"][table] = random_cols
    print(f"{table} and {random_cols}")


with open(f"ranked_tbls_{args.value_iter}.json", "w") as f:
    json.dump(output, f, indent=4)





