import json
from collections import defaultdict

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

VALUE_JSON = "../value_generation/data_val_cols_custom_1.json"
FREQ_JSON = "../value_generation/frequency_cols_custom.json"
TABLES_JSON = "../value_generation/tpcds_columns_in_tables.json"

col_value = load_json(VALUE_JSON)       # column -> value
col_freq = load_json(FREQ_JSON)         # column -> frequency
table_columns = load_json(TABLES_JSON)  # table -> [columns]

table_value = defaultdict(float)
table_freq = defaultdict(float)

for table, cols in table_columns.items():
    for col in cols:
        assert col in col_value
        assert col in col_freq
        v = col_value.get(col, 0.0)
        f = col_freq.get(col, 0.0)

        table_value[table] += v
        table_freq[table] += f
# ----------------------------
# Rank tables separately
# ----------------------------

top_value_tables = sorted(
    table_value.items(),
    key=lambda x: x[1],
    reverse=True
)[:2]

top_freq_tables = sorted(
    table_freq.items(),
    key=lambda x: x[1],
    reverse=True
)[:2]


# ----------------------------
# Print top tables by VALUE
# ----------------------------

print("\n===== TOP 2 TABLES BY TOTAL VALUE =====")
for rank, (table, val) in enumerate(top_value_tables, start=1):
    print(f"{rank}. {table} (total_value={val:.2f})")

print("\n===== TOP COLUMNS (BY VALUE) FOR VALUE TABLES =====")

for table, _ in top_value_tables:
    cols = table_columns[table]

    top_val_cols = sorted(
        cols,
        key=lambda c: col_value.get(c, 0.0),
        reverse=True
    )[:2]

    print(f"\nTable: {table}")
    for c in top_val_cols:
        print(f"  {c:30s} value={col_value.get(c, 0.0):.2f}")


# ----------------------------
# Print top tables by FREQUENCY
# ----------------------------

print("\n===== TOP 2 TABLES BY TOTAL FREQUENCY =====")
for rank, (table, freq) in enumerate(top_freq_tables, start=1):
    print(f"{rank}. {table} (total_freq={freq:.2f})")

print("\n===== TOP COLUMNS (BY FREQUENCY) FOR FREQUENCY TABLES =====")

for table, _ in top_freq_tables:
    cols = table_columns[table]

    top_freq_cols = sorted(
        cols,
        key=lambda c: col_freq.get(c, 0.0),
        reverse=True
    )[:2]

    print(f"\nTable: {table}")
    for c in top_freq_cols:
        print(f"  {c:30s} freq={col_freq.get(c, 0.0):.2f}")







