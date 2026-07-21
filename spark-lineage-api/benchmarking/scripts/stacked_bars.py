import pandas as pd
import sys

mod_file = sys.argv[1]
# vanilla_file = sys.argv[2]

TBL_COL = "full_mean"
ROW_COL = "rowgroup_mean"
VAN_COL = "vanilla_mean"
BAR_COL = "bare_mean"
REG_COL = "register_mean"

ROW_DIFF = "rowgroup_overhead"
TBL_DIFF = "table_overhead"
REG_DIFF = "register_overhead"


grouped = pd.read_csv(mod_file)
grouped = grouped[grouped['dataset'] == 'tpch']

# exclude_cols = ['run_number', 'query', 'dataset']
# numeric_cols = [col for col in df.columns if col not in exclude_cols]
# df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
# grouped = df.groupby(['query', 'dataset'])[numeric_cols].mean().reset_index()


import matplotlib.pyplot as plt
import numpy as np

# Suppose your grouped DataFrame is called 'grouped'
# Columns: query, dataset, listener_time_sec, listener_rg_time, VAN_COL

# Create a label for each (query, dataset) pair
def extract_query_num(query_str):
    return int(query_str.replace('.sql', ''))

grouped['label'] = grouped['query'] + ' | ' + grouped['dataset']

grouped[REG_DIFF] = grouped[REG_COL] - grouped[VAN_COL]
grouped[TBL_DIFF] = grouped[TBL_COL] - grouped[REG_COL]
grouped[ROW_DIFF] = grouped[ROW_COL] - grouped[REG_COL]
df = grouped

# Filter to only queries 1 through 22 and sort numerically
df['query_num'] = df['query'].apply(extract_query_num)
df = df[(df['query_num'] >= 1) & (df['query_num'] <= 22)]
df = df.sort_values('query_num').reset_index(drop=True)
df = df.drop('query_num', axis=1)

# Convert time columns from millisecodns to minutes
time_cols = [VAN_COL, BAR_COL, TBL_COL, ROW_COL, REG_COL, ROW_DIFF, TBL_DIFF, REG_DIFF]
for col in time_cols:
    if col in df.columns:
        df[col] = df[col] / (1_000 * 60)
# df = grouped[grouped[ROW_DIFF] < 0]
# print(df.describe())
# 
# grouped = grouped[grouped[ROW_DIFF] >= 0]
# grouped = grouped[grouped[TBL_DIFF] >= 0]
# grouped = grouped[grouped[REG_DIFF] >= 0]
# print(grouped.describe())






# # X locations for each group
# x = np.arange(len(grouped))
# width = 0.2  # width of the bars
# 
# fig, ax = plt.subplots(figsize=(12, 6))
# 
# # Plot listener_time_sec stacked on VAN_COL
# 
# ax.bar(x - width/2, grouped[VAN_COL], width, color='g', label='Vanilla Time')
# 
# bottom1 = grouped[VAN_COL]
# ax.bar(x - width/2, grouped[REG_DIFF], width, color='b', 
#        bottom=bottom1, label='Register Listener')
# 
# bottom2 = bottom1 + grouped[REG_DIFF]
# ax.bar(x - width/2, grouped[TBL_DIFF], width,
#        bottom=bottom2, label='Parse Columns')
# 
# # Plot listener_rg_time stacked on VAN_COL
# 
# ax.bar(x + width/2, grouped[VAN_COL], width, color='g', label='Vanilla Time')
# 
# bottom1 = grouped[VAN_COL]
# ax.bar(x + width/2, grouped[REG_DIFF], width, color='b',
#        bottom=bottom1, label='Register Listener')
# 
# bottom2 = bottom1 + grouped[REG_DIFF]
# ax.bar(x + width/2, grouped[ROW_DIFF], width, 
#        bottom=bottom2, label='Parse Row Groups')
# 
# # Labels and ticks
# ax.set_xticks(x)
# ax.set_xticklabels(grouped['label'], fontsize=7, rotation=90, ha='right')
# ax.set_ylabel('Time (sec)')
# ax.set_title('Listener Times vs Registration Time per Query/Dataset')
# ax.legend()
# 
# plt.tight_layout()
# plt.savefig("../figs/storage_rg_vs_col.pdf")


red = "#E65742"
orange = "#FE9C22"
yellow = "#F8DD3D"
teal = "#71EAB9"
green = "#ADDC5A"
blue = "#1F63A9"

colors_map = {
    'bare': red,
    'cols': orange,
    'rowgroup': green,
    'vanilla': blue
}

# Separate data by dataset
df_tpch = df[df['dataset'] == 'tpch']
# df_tpcds = df[df['dataset'] == 'tpcds']
# df_tpcds_small = df_tpcds[df_tpcds['rowgroup_mean'] < 2500]
# df_tpcds_large = df_tpcds[df_tpcds['rowgroup_mean'] >= 2500]

def plot_grouped(df_subset, title, filename):
    font = {'size': 17}
    plt.rc('font', **font)
    query_labels = [f"{extract_query_num(q)}" for q in df_subset['query']]
    x = np.arange(len(df_subset))  # one slot per query
    width = 0.2

    fig, ax = plt.subplots(figsize=(10, 5.5))

    ax.bar(x - 1.5*width, df_subset[VAN_COL], width, label='Vanilla',
           color=colors_map['vanilla'])
    ax.bar(x - 0.5*width, df_subset[BAR_COL], width, label='Listener Only', 
           color=colors_map['bare'])
    ax.bar(x + 0.5*width, df_subset[TBL_COL], width, label='Columns',
           color=colors_map['cols'])
    ax.bar(x + 1.5*width, df_subset[ROW_COL], width, label='Row Group',
           color=colors_map['rowgroup'])

    ax.set_xticks(x)
    ax.set_xticklabels(query_labels)
    ax.set_xlabel("TPC-H Query Number")
    ax.set_ylabel('Time (minutes)')
    # ax.set_title(title)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.legend(loc='upper left')
    ax.set_xlim([-0.6,21.6])


    plt.tight_layout()
    plt.savefig(filename, bbox_inches='tight')
    # plt.show()

# Make the two plots
plot_grouped(df_tpch, "Vanilla vs Register vs Table vs RowGroup (TPC-H)", "../figs/tpch_node1_30gb.pdf")
# plot_grouped(df_tpcds, "Vanilla vs Register vs Table vs RowGroup (TPC-DS)", "../figs/grouped_bars_tpcds.pdf")
# plot_grouped(df_tpcds_small, "Vanilla vs Register vs Table vs RowGroup (TPC-DS)", "../figs/grouped_bars_tpcds_small.pdf")
# plot_grouped(df_tpcds_large, "Vanilla vs Register vs Table vs RowGroup (TPC-DS)", "../figs/grouped_bars_tpcds_large.pdf")



# Compute percent differences compared to vanilla for each variant
print("\n" + "="*60)
print("Percent Difference Statistics (compared to Vanilla)")
print("="*60)

# Variants to compare (excluding vanilla itself)
variants_to_compare = [BAR_COL, TBL_COL, ROW_COL]
print(df_tpch.columns)
for variant in variants_to_compare:
    if variant in df_tpch.columns and VAN_COL in df_tpch.columns:
        # Compute percent difference: ((variant - vanilla) / vanilla) * 100
        percent_diff = ((df_tpch[variant] - df_tpch[VAN_COL]) / df_tpch[VAN_COL]) * 100
        
        print(f"\n{variant.upper()} (compared to Vanilla):")
        print(f"  Min:    {percent_diff.min():.2f}%")
        print(f"  25th:   {percent_diff.quantile(0.25):.2f}%")
        print(f"  Median: {percent_diff.median():.2f}%")
        print(f"  Mean:   {percent_diff.mean():.2f}%")
        print(f"  75th:   {percent_diff.quantile(0.75):.2f}%")
        print(f"  Max:    {percent_diff.max():.2f}%")

# Compute percent difference between rowgroup and cols
print("\n" + "="*60)
print("Percent Difference: Rowgroup vs Columns")
print("="*60)

if ROW_COL in df_tpch.columns and TBL_COL in df_tpch.columns:
    # Compute percent difference: ((rowgroup - cols) / cols) * 100
    rowgroup_vs_cols = ((df_tpch[ROW_COL] - df_tpch[TBL_COL]) / df_tpch[TBL_COL]) * 100
    
    print(f"\nRowgroup (compared to Columns):")
    print(f"  Min:    {rowgroup_vs_cols.min():.2f}%")
    print(f"  25th:   {rowgroup_vs_cols.quantile(0.25):.2f}%")
    print(f"  Median: {rowgroup_vs_cols.median():.2f}%")
    print(f"  Mean:   {rowgroup_vs_cols.mean():.2f}%")
    print(f"  75th:   {rowgroup_vs_cols.quantile(0.75):.2f}%")
    print(f"  Max:    {rowgroup_vs_cols.max():.2f}%")

