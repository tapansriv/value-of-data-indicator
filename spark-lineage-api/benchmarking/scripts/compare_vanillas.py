import pandas as pd
import os
import sys

mod_file = sys.argv[1]
vanilla_file = sys.argv[2]

TBL_COL = "full_mean"
ROW_COL = "rowgroup_mean"
VAN_COL = "vanilla_mean"


plain_data = pd.read_csv(vanilla_file)
plain_data = plain_data[plain_data[VAN_COL] != "fail"]

custom_data = pd.read_csv(mod_file)
custom_data = custom_data[custom_data[VAN_COL] != "fail"]

custom_data[VAN_COL] = pd.to_numeric(custom_data[VAN_COL])
plain_data[VAN_COL] = pd.to_numeric(plain_data[VAN_COL])

custom_mean = custom_data.groupby(['query', 'dataset'])[VAN_COL].mean().reset_index()
plain_mean = plain_data.groupby(['query', 'dataset'])[VAN_COL].mean().reset_index()

merged = pd.merge(custom_mean, plain_mean, on=['query', 'dataset'], suffixes=('_custom', '_plain'))

merged['percent_difference'] = ((merged['vanilla_mean_custom'] 
                                 - merged['vanilla_mean_plain']) 
                                / merged['vanilla_mean_plain']) * 100

summary_stats = merged[['vanilla_mean_custom', 
                        'vanilla_mean_plain',
                        'percent_difference']].describe()
print(summary_stats)

import matplotlib.pyplot as plt

# Scatter plot: percent_difference vs. vanilla_mean_plain
plt.figure(figsize=(8, 6))
plt.scatter(
    merged['vanilla_mean_plain'],
    merged['percent_difference'],
    alpha=0.7,
    edgecolor='k'
)

plt.xlabel("Vanilla Mean Runtime (plain)")
plt.ylabel("Percent Difference (custom vs plain)")
# plt.title("Percent Difference vs Vanilla Mean Runtime")
plt.grid(True, linestyle='--', alpha=0.6)

# Save and/or show
plt.tight_layout()
plt.savefig("../figs/mod_spark_comp.pdf")
plt.show()
