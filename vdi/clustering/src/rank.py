import os
import json
from argparse import ArgumentParser
import numpy as np


HOME = os.path.expanduser("~")
SRC_DIR = os.path.join(HOME, "tpcds_30gb")

OUT_VALUE_DIR = os.path.join(HOME, "tpcds_cluster_vod")
OUT_FREQ_DIR = os.path.join(HOME, "tpcds_cluster_freq")
OUT_RAND_DIR = os.path.join(HOME, "tpcds_cluster_rand")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Inputs come from the workload profile (WORKLOAD=tpcds by default: the same TPC-DS files
# as before; WORKLOAD=imdb for the Redbench IMDb workload). See workload.py.
from workload import P as _WORKLOAD  # noqa: E402
VALUE_JSON = str(_WORKLOAD["value_json"])
FREQ_JSON = str(_WORKLOAD["freq_json"])
TABLES_JSON = str(_WORKLOAD["tables_json"])
# TPC-DS: row counts from the SF30 Parquet footers (r2d7_results/sf30/tpcds_cardinality.json)
ROW_COUNTS_JSON = str(_WORKLOAD["row_counts_json"])

RANDOM_SEED = 42
NUM_TABLES = 2
NUM_COLS_PER_TABLE = 2
ROW_GROUP_SIZE = 128_000  # rows; matches cluster.py


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def multi_rowgroup_tables(row_counts_path=ROW_COUNTS_JSON, row_group_size=ROW_GROUP_SIZE):
    """Tables spanning more than one row group; only these can benefit from pruning."""
    row_counts = load_json(row_counts_path)
    return {t for t, n in row_counts.items() if n > row_group_size}


def rank(value_iter, num_tables=NUM_TABLES, num_cols=NUM_COLS_PER_TABLE,
         multi_rowgroup_only=False):
    """Choose tables and sort columns for the value, frequency and random strategies.

    Rankings are prefixes: the top-k tables are the top-(k-1) plus one, and the
    top-c columns of a table are its top-(c-1) plus one. Random draws use a fixed
    seed and are nested in the same way.

    multi_rowgroup_only restricts every strategy to tables spanning more than one
    row group. The default (False) reproduces the published configurations.
    """
    col_value = load_json(VALUE_JSON)[value_iter]
    col_freq = load_json(FREQ_JSON)
    table_columns = load_json(TABLES_JSON)
    if multi_rowgroup_only:
        eligible = multi_rowgroup_tables()
        table_columns = {t: c for t, c in table_columns.items() if t in eligible}

    # Aggregate per table
    table_value = {}
    table_freq = {}

    for table, cols in table_columns.items():
        table_value[table] = sum(col_value.get(c, 0.0) for c in cols)
        table_freq[table] = sum(col_freq.get(c, 0.0) for c in cols)

    # Rank tables
    top_value_tables = sorted(table_value, key=table_value.get,
                              reverse=True)[:num_tables]
    top_freq_tables = sorted(table_freq, key=table_freq.get,
                             reverse=True)[:num_tables]

    def top_cols_by_metric(cols, metric_dict):
        return sorted(cols, key=lambda c: metric_dict.get(c, 0.0),
                      reverse=True)[:num_cols]

    def bare(table, cols):
        # Workloads whose column names collide across tables (IMDb) key columns as
        # `table.column`; layouts and SQL need the bare name. No-op for TPC-DS.
        return [c[len(table) + 1:] if c.startswith(table + ".") else c for c in cols]

    output = {"value": {}, "frequency": {}, "random": {}}

    for table in top_value_tables:
        output["value"][table] = bare(table, top_cols_by_metric(table_columns[table], col_value))

    for table in top_freq_tables:
        output["frequency"][table] = bare(table, top_cols_by_metric(table_columns[table], col_freq))

    np.random.seed(RANDOM_SEED)
    all_tables = list(table_columns.keys())
    random_tables = np.random.choice(all_tables, size=num_tables, replace=False)

    for table in random_tables:
        cols = table_columns[table]
        if len(cols) < num_cols:
            raise ValueError(f"Table {table} has fewer than {num_cols} columns")
        random_cols = np.random.choice(cols, size=num_cols, replace=False).tolist()
        output["random"][str(table)] = bare(str(table), random_cols)

    return output


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--value-iter", type=str, default="0", help="iteration")
    parser.add_argument("--num-tables", type=int, default=NUM_TABLES)
    parser.add_argument("--num-cols", type=int, default=NUM_COLS_PER_TABLE)
    parser.add_argument("--multi-rowgroup-only", action="store_true",
                        help="rank only tables spanning more than one row group")
    parser.add_argument("--out", type=str, default=None,
                        help="output path (default: ranked_tbls_<iter>.json)")
    args = parser.parse_args()

    output = rank(args.value_iter, args.num_tables, args.num_cols,
                  args.multi_rowgroup_only)

    for strategy, out_dir in [("value", OUT_VALUE_DIR), ("frequency", OUT_FREQ_DIR),
                              ("random", OUT_RAND_DIR)]:
        print(f"\n===== CHOOSING {strategy.upper()} TABLES =====")
        ensure_dir(out_dir)
        for table, cols in output[strategy].items():
            print(f"{table} and {cols}")

    out_path = args.out or f"ranked_tbls_{args.value_iter}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=4)
