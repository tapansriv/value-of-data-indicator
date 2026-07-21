#!/usr/bin/env python3
"""
Create a grouped bar chart for TPC-H queries with single_node_mod_spark configuration.
Shows average runtime for each variant (bare, cols, rowgroup, vanilla).
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

red = "#E65742"
orange = "#FE9C22"
yellow = "#F8DD3D"
teal = "#71EAB9"
green = "#ADDC5A"
blue = "#1F63A9"

# Read the data
data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'all_results.csv')
df = pd.read_csv(data_file)

# Filter for tpch dataset and single_node_mod_spark configuration, exclude nowrite and register variants
filtered_mod = df[
    (df['dataset'] == 'tpch') & 
    (df['configuration'] == 'single_node_mod_spark') &
    (df['variant'] != 'nowrite') &
    (df['variant'] != 'register')
]

# For query 18.sql, get cols and vanilla from unmod_spark configuration
filtered_unmod_18 = df[
    (df['dataset'] == 'tpch') &
    (df['configuration'] == 'unmod_spark') &
    (df['query'] == '18.sql') &
    (df['variant'].isin(['cols', 'vanilla']))
]

# Remove query 18.sql's cols and vanilla from mod_spark data
filtered_mod = filtered_mod[
    ~((filtered_mod['query'] == '18.sql') & 
      (filtered_mod['variant'].isin(['cols', 'vanilla'])))
]

# Combine the dataframes
filtered = pd.concat([filtered_mod, filtered_unmod_18], ignore_index=True)

# Group by query and variant, compute mean runtime
aggregated = filtered.groupby(['query', 'variant'])['runtime'].mean().reset_index()

# Pivot the data so each variant becomes a column
pivoted = aggregated.pivot(index='query', columns='variant', values='runtime').reset_index()

# Sort queries numerically (extract number from query string)
def extract_query_num(query_str):
    """Extract numeric part from query string like '1.sql' -> 1"""
    return int(query_str.replace('.sql', ''))

pivoted['query_num'] = pivoted['query'].apply(extract_query_num)
# Filter to only include queries 1.sql through 22.sql
pivoted = pivoted[(pivoted['query_num'] >= 1) & (pivoted['query_num'] <= 22)]
pivoted = pivoted.sort_values('query_num').reset_index(drop=True)
pivoted = pivoted.drop('query_num', axis=1)

# Define variant order and color mapping (vanilla on the left)
variant_order = ['vanilla', 'bare', 'cols', 'rowgroup']

# Convert runtimes from milliseconds to minutes
for variant in variant_order:
    if variant in pivoted.columns:
        pivoted[variant] = pivoted[variant] / 1_000 / 60  # milliseconds -> seconds -> minutes
colors_map = {
    'bare': red,
    'cols': orange,
    'rowgroup': green,
    'vanilla': blue
}
# Label mapping for legend
label_map = {
    'bare': 'Listener Only',
    'cols': 'Columns',
    'rowgroup': 'Row Group',
    'vanilla': 'Vanilla'
}

# Create the plot
font = {'size': 17}
plt.rc('font', **font)
fig, ax = plt.subplots(figsize=(10, 5.5))

# X locations for each query
x = np.arange(len(pivoted))
width = 0.2  # width of each bar

# Plot bars for each variant
for i, variant in enumerate(variant_order):
    if variant in pivoted.columns:
        offset = (i - len(variant_order) / 2 + 0.5) * width
        ax.bar(x + offset, pivoted[variant], width, 
               label=label_map[variant], 
               color=colors_map[variant])

# Set x-axis labels (format as QN instead of N.sql, no rotation)
query_labels = [f"{extract_query_num(q)}" for q in pivoted['query']]
ax.set_xticks(x)
ax.set_xticklabels(query_labels)
ax.set_xlim([-0.6, 21.6])
ax.set_ylabel('Time (minutes)')
ax.set_xlabel('TPC-H Query Number')
ax.legend(loc='upper left')
ax.grid(axis='y', alpha=0.3, linestyle='--')

plt.tight_layout()

# Save to figs directory
output_file = os.path.join(os.path.dirname(__file__), '..', 'figs', 'tpch_mod_node1_1tb.pdf')
plt.savefig(output_file, format='pdf', dpi=300, bbox_inches='tight')
print(f"Figure saved to {output_file}")

plt.close()

# Compute percent differences compared to vanilla for each variant
print("\n" + "="*60)
print("Percent Difference Statistics (compared to Vanilla)")
print("="*60)

# Variants to compare (excluding vanilla itself)
variants_to_compare = ['bare', 'cols', 'rowgroup']

for variant in variants_to_compare:
    if variant in pivoted.columns and 'vanilla' in pivoted.columns:
        # Compute percent difference: ((variant - vanilla) / vanilla) * 100
        percent_diff = ((pivoted[variant] - pivoted['vanilla']) / pivoted['vanilla']) * 100
        
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

if 'rowgroup' in pivoted.columns and 'cols' in pivoted.columns:
    # Compute percent difference: ((rowgroup - cols) / cols) * 100
    rowgroup_vs_cols = ((pivoted['rowgroup'] - pivoted['cols']) / pivoted['cols']) * 100
    
    print(f"\nRowgroup (compared to Columns):")
    print(f"  Min:    {rowgroup_vs_cols.min():.2f}%")
    print(f"  25th:   {rowgroup_vs_cols.quantile(0.25):.2f}%")
    print(f"  Median: {rowgroup_vs_cols.median():.2f}%")
    print(f"  Mean:   {rowgroup_vs_cols.mean():.2f}%")
    print(f"  75th:   {rowgroup_vs_cols.quantile(0.75):.2f}%")
    print(f"  Max:    {rowgroup_vs_cols.max():.2f}%")
