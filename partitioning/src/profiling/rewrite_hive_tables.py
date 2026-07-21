import os
import json
import duckdb

HOME = os.path.expanduser("~")
SRC_DIR = os.path.join(HOME, "tpcds_30gb")

OUT_VALUE_DIR = os.path.join(HOME, "tpcds_partitioned_value")
OUT_FREQ_DIR = os.path.join(HOME, "tpcds_partitioned_freq")

VALUE_JSON = "../value_generation/data_val_cols_custom_1.json"
FREQ_JSON = "../value_generation/frequency_cols_custom.json"
TABLES_JSON = "../value_generation/tpcds_columns_in_tables.json"


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


col_value = load_json(VALUE_JSON)
col_freq = load_json(FREQ_JSON)
table_columns = load_json(TABLES_JSON)

# Aggregate per table
table_value = {}
table_freq = {}

for table, cols in table_columns.items():
    table_value[table] = sum(col_value.get(c, 0.0) for c in cols)
    table_freq[table] = sum(col_freq.get(c, 0.0) for c in cols)

# Rank tables
top_value_tables = sorted(table_value, key=table_value.get, reverse=True)[:2]
top_freq_tables = sorted(table_freq, key=table_freq.get, reverse=True)[:2]


def top_cols_by_metric(cols, metric_dict):
    return sorted(cols, key=lambda c: metric_dict.get(c, 0.0), reverse=True)[:2]


# ----------------------------
# DuckDB connection
# ----------------------------

con = duckdb.connect('hi')
con.execute("SET memory_limit='58GB'")
con.execute("SET threads=1")
con.execute("SET preserve_insertion_order=false;") 
con.execute(" SET partitioned_write_max_open_files = 10;")


def rewrite_table(table, partition_cols, out_root):
    src_path = os.path.join(SRC_DIR, f"{table}.parquet")
    out_path = os.path.join(out_root, table)

    ensure_dir(out_path)

    part_cols_sql = ", ".join(partition_cols[:1])

    print(f"\nRewriting {table}")
    print(f"  Partition columns: {partition_cols}")
    print(f"  Output: {out_path}")

    query = f"""
        CREATE TABLE {table} AS SELECT * FROM read_parquet('{src_path}')
    """
    con.execute(query)

    query = f"""
        COPY {table}
        TO '{out_path}'
        (FORMAT PARQUET, PARTITION_BY ({part_cols_sql}));
    """

    con.execute(query)


# ----------------------------
# Rewrite VALUE tables
# ----------------------------

print("\n===== REWRITING VALUE TABLES =====")
ensure_dir(OUT_VALUE_DIR)

for table in top_value_tables:
    cols = table_columns[table]
    part_cols = top_cols_by_metric(cols, col_value)
    rewrite_table(table, part_cols, OUT_VALUE_DIR)


# ----------------------------
# Rewrite FREQUENCY tables
# ----------------------------

print("\n===== REWRITING FREQUENCY TABLES =====")
ensure_dir(OUT_FREQ_DIR)

for table in top_freq_tables:
    cols = table_columns[table]
    part_cols = top_cols_by_metric(cols, col_freq)
    rewrite_table(table, part_cols, OUT_FREQ_DIR)


print("\nDone.")
