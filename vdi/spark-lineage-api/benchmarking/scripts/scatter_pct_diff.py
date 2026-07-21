import pandas as pd
import os
import sys

mod_file = sys.argv[1]
vanilla_file = sys.argv[2]



TBL_COL = "full_mean"
ROW_COL = "rowgroup_mean"
VAN_COL = "vanilla_mean"



grouped = pd.read_csv(mod_file)
grouped = grouped[grouped[VAN_COL] != "fail"]

# exclude_cols = ['query', 'dataset']
# numeric_cols = [col for col in df.columns if col not in exclude_cols]
# df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
# grouped = df.groupby(['query', 'dataset'])[numeric_cols].mean().reset_index()

grouped["rg_tb_overhead"] = 100 * (grouped[ROW_COL] - grouped[TBL_COL] ) / grouped[TBL_COL]
print(grouped["rg_tb_overhead"].describe())
print("")
print(grouped.loc[grouped["rg_tb_overhead"].idxmax()])
print("")


grouped["rg_overhead"] = 100 * (grouped[ROW_COL] - grouped[VAN_COL] ) / grouped[VAN_COL]
grouped["tb_overhead"] = 100 * (grouped[TBL_COL] - grouped[VAN_COL] ) / grouped[VAN_COL]
grouped = grouped[grouped["rg_overhead"] > 0]
grouped = grouped[grouped["tb_overhead"] > 0]

print("")
print(grouped["rg_overhead"].describe())
print("")
print(grouped["tb_overhead"].describe())
print("")

# df = grouped[grouped[VAN_COL] > grouped[ROW_COL]]
# print(df[["query", "dataset", TBL_COL, ROW_COL, VAN_COL, "rg_overhead",
#           "tb_overhead"]])
import matplotlib.pyplot as plt
import numpy as np

# Example: plot column 'A' vs 'B'
grouped.plot(x=VAN_COL, y="rg_overhead", kind='scatter', figsize=(8,6), ylim=(-5, 100))
plt.xlabel('Absolute Vanilla Time')
plt.ylabel('Percent Difference')
plt.savefig("../figs/rg_vs_vanilla.pdf")
# plt.show()

grouped.plot(x=VAN_COL, y="tb_overhead", kind='scatter', figsize=(8,6), ylim=(-5, 100))
plt.xlabel('Absolute Vanilla Time')
plt.ylabel('Percent Difference')
plt.savefig("../figs/tbl_vs_vanilla.pdf")
# plt.show()

grouped['label'] = grouped['query'] + ' | ' + grouped['dataset']
grouped.plot(x="label", y="rg_tb_overhead", kind="bar", legend=False,
             figsize=(8,6))
# plt.show()
plt.clf()




grouped = pd.read_csv(vanilla_file)
grouped = grouped[grouped[VAN_COL] != "fail"]

# exclude_cols = ['run_number', 'query', 'dataset']
# numeric_cols = [col for col in df.columns if col not in exclude_cols]
# df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
# grouped = df.groupby(['query', 'dataset'])[numeric_cols].mean().reset_index()

grouped["tb_overhead"] = 100 * (grouped[TBL_COL] - grouped[VAN_COL] ) / grouped[VAN_COL]
grouped = grouped[grouped["tb_overhead"] > 0]

df = grouped[grouped[VAN_COL] > grouped[TBL_COL]]
print(df[["query", "dataset", TBL_COL, VAN_COL, "tb_overhead"]])

grouped.plot(x=VAN_COL, y="tb_overhead", kind='scatter', figsize=(8,6))
plt.xlabel('Absolute Vanilla Time')
plt.ylabel('Percent Difference')
# plt.show()
