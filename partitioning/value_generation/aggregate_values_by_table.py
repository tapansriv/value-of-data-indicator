import json
import numpy as np
import re
from argparse import ArgumentParser

parser = ArgumentParser(description="Run time-series oracle")
parser.add_argument("--num-trials", type=int, default=100, 
                    help="Number of different value generation trials that were run")
args = parser.parse_args()

def sum_agg(data):
    output = {k: sum(data[k]) for k in data}
    return output
    
# TPCH/TPCDS tables and columns
tpcds_tables = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]

tables = tpcds_tables
tpcds_cols_in_tbls = json.load(open("../schema/tpcds_schema_registry.json"))

# accumulate data for the value-based DE assignment
data_column_values = json.load(open(f"data_val_cols_custom_raw.json"))
frequency_column_values = json.load(open("frequency_cols_custom.json"))

data_column_table_final = {tbl: [] for tbl in tables}
freq_column_table_final = {tbl: [] for tbl in tables}

dv_by_table = {tbl: {} for tbl in tables}
fv_by_table = {tbl: {} for tbl in tables}
dvs = {}
fvs = {}

for iter_ in range(args.num_trials):
    iter_key = str(iter_)

    column_values = data_column_values[iter_key]

    data_column_table_aggregates = {tbl: 0 for tbl in tables}
    freq_column_table_aggregates = {tbl: 0 for tbl in tables}
    for col in column_values:
        matches = []
        for tbl in tpcds_cols_in_tbls:
            if col in tpcds_cols_in_tbls[tbl]:
                matches.append(tbl)

        assert len(matches) == 1, f"{matches}"
        key = matches[0]
        data_column_table_aggregates[key] += column_values[col]
        freq_column_table_aggregates[key] += frequency_column_values[col]

        if col not in dv_by_table[key]:
            dv_by_table[key][col] = {}
        dv_by_table[key][col][iter_key] = column_values[col]
        fv_by_table[key][col] = frequency_column_values[col]

        if col not in dvs:
            dvs[col] = []
        dvs[col].append(column_values[col])
        if iter_ == 0:
            fvs[col] = frequency_column_values[col]
    
    for tbl in data_column_table_final:
        data_column_table_final[tbl].append(data_column_table_aggregates[tbl])

    for tbl in freq_column_table_final:
        freq_column_table_final[tbl] = freq_column_table_aggregates[tbl]





num_tbls = 2
num_cols = 2

x = sorted(data_column_table_final.items(), key = lambda item: item[1][0],
           reverse=True)

asdf1 = [d[0] for d in x]
with open("dv.csv", 'w') as file:
    file.write("\n".join(asdf1))

print("")
tbl_names = [d[0] for d in x[:num_tbls]]
tbls_with_values = [(d[0], d[1][0]) for d in x[:num_tbls]]
print(f"By data value we will partition tables: {tbls_with_values}")
for tbl in tbl_names:
    cols = dv_by_table[tbl]
    y = sorted(cols.items(), key = lambda item: item[1]["0"])
    cols_chosen = [d[0] for d in y[:num_cols]]
    print(f"For {tbl} we will partition columns {cols_chosen}")


print("")
print("")
x = sorted(freq_column_table_final.items(), key = lambda item: item[1],
           reverse=True)
asdf2 = [d[0] for d in x]
with open("fv.csv", 'w') as file:
    file.write("\n".join(asdf2))

print("")
tbl_names = [d[0] for d in x[:num_tbls]]
tbls_with_values = [(d[0], d[1]) for d in x[:num_tbls]]
print(f"By Frequency we will partition tables: {tbls_with_values}")
for tbl in tbl_names:
    cols = fv_by_table[tbl]
    y = sorted(cols.items(), key = lambda item: item[1])
    cols_chosen = [d[0] for d in y[:num_cols]]
    print(f"For {tbl} we will partition columns {cols_chosen}")



new = []
diffs = []
for i in range(len(asdf1)):
    tbl = asdf1[i]
    i2 = asdf2.index(tbl)
    new.append(f"{tbl}, {i}, {i2}, {i-i2}")
    diffs.append([tbl, abs(i-i2)])

print(sorted(diffs, key = lambda item: item[1]))
with open("comp.csv", 'w') as file:
    file.write("\n".join(new))



foo1 = sorted(dvs.items(), key = lambda item: item[1][0], reverse = True)
foo2 = sorted(fvs.items(), key = lambda item: item[1], reverse = True)
foo2_1 = [d[0] for d in foo2]
diffs = []
for i1 in range(len(foo1)):
    col = foo1[i1][0]
    i2 = foo2_1.index(col)
    diffs.append([col, abs(i1 - i2), i1, i2])


foo3 = sorted(diffs, key = lambda item: item[1], reverse=True)
data = [f"{d[0]}, {d[1]}, {d[2]}, {d[3]}" for d in foo3[:20]]
with open('compcol.csv', 'w') as fp:
    fp.write("\n".join(data))
print(foo3[:20])
    
              


