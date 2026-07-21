import os
import json
import duckdb

HOME = os.path.expanduser("~")

VALUE_JSON = "../value_generation/data_val_cols_custom_1.json"
FREQ_JSON = "../value_generation/frequency_cols_custom.json"
TABLES_JSON = "../value_generation/tpcds_columns_in_tables.json"


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


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


def top_col_by_metric(cols, metric_dict):
    return sorted(cols, key=lambda c: metric_dict.get(c, 0.0), reverse=True)[0]


# ----------------------------
# DuckDB connection
# ----------------------------
def build_index(con, table, col):
    idx_name = f"idx_{col}"
    qry = f"CREATE INDEX {idx_name} ON {table} ({col})"
    print(f"    Building index for {col} on {table}")
    con.execute(qry)

# ----------------------------
# Rewrite VALUE tables
# ----------------------------

print("\n===== BUILDING VALUE INDICES =====")
con = duckdb.connect("tpcds_vod.db")
for table in top_value_tables:
    cols = table_columns[table]
    part_cols = top_col_by_metric(cols, col_value)
    build_index(con, table, part_cols)


# ----------------------------
# Rewrite FREQUENCY tables
# ----------------------------

print("\n===== BUILDING FREQUENCY INDICES =====")
con = duckdb.connect("tpcds_freq.db")
for table in top_freq_tables:
    cols = table_columns[table]
    part_col = top_col_by_metric(cols, col_freq)
    build_index(con, table, part_col)


print("\nDone.")

