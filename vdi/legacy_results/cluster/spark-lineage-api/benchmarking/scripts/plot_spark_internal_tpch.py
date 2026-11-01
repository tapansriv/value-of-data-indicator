#!/usr/bin/env python3
"""
Create a grouped bar chart for TPC-H queries using spark_internal_listener results.
Shows average runtime for each variant (vanilla, bare, cols, rowgroup).
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

# Colors
red = "#E65742"
orange = "#FE9C22"
yellow = "#F8DD3D"
teal = "#71EAB9"
green = "#ADDC5A"
blue = "#1F63A9"

# Define variant order and color mapping (vanilla on the left)
variant_order = ['vanilla', 'bare', 'cols', 'rowgroup']
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

# Get the benchmarking directory
benchmarking_dir = os.path.dirname(os.path.dirname(__file__))

# Read all variant files
variant_files = {
    'vanilla': os.path.join(benchmarking_dir, 'spark_internal_listener_vanilla_results.csv'),
    'bare': os.path.join(benchmarking_dir, 'spark_internal_listener_bare_results.csv'),
    'cols': os.path.join(benchmarking_dir, 'spark_internal_listener_cols_results.csv'),
    'rowgroup': os.path.join(benchmarking_dir, 'spark_internal_listener_rowgroup_results.csv')
}

# Read and combine all variant data
all_data = []
for variant, filepath in variant_files.items():
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        df['variant'] = variant
        all_data.append(df)
    else:
        print(f"Warning: File not found: {filepath}")

if not all_data:
    raise FileNotFoundError("No variant files found!")

# Combine all dataframes
combined = pd.concat(all_data, ignore_index=True)

# Filter for tpch dataset
filtered = combined[combined['dataset'] == 'tpch'].copy()

# Extract query number and filter to queries 1-22
def extract_query_num(query_str):
    """Extract numeric part from query string like '1.sql' -> 1"""
    return int(query_str.replace('.sql', ''))

filtered['query_num'] = filtered['query'].apply(extract_query_num)
filtered = filtered[(filtered['query_num'] >= 1) & (filtered['query_num'] <= 22)]

# Group by query and variant, compute mean runtime
aggregated = filtered.groupby(['query', 'variant'])['runtime'].mean().reset_index()

# Pivot the data so each variant becomes a column
pivoted = aggregated.pivot(index='query', columns='variant', values='runtime').reset_index()

# Sort queries numerically
pivoted['query_num'] = pivoted['query'].apply(extract_query_num)
pivoted = pivoted.sort_values('query_num').reset_index(drop=True)
pivoted = pivoted.drop('query_num', axis=1)

# Convert runtimes from milliseconds to minutes
for variant in variant_order:
    if variant in pivoted.columns:
        pivoted[variant] = pivoted[variant] / 1_000 / 60  # milliseconds -> seconds -> minutes

# Create the plot
font = {'size': 17}
plt.rc('font', **font)
fig, ax = plt.subplots(figsize=(10, 5.5))

# X locations for each query
x = np.arange(len(pivoted))
width = 0.15  # width of each bar

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
ax.set_xticklabels(query_labels )
ax.set_ylabel('Time (minutes)')
ax.set_xlabel('TPC-H Query Number')
ax.legend(loc='upper left')
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_xlim([-0.6, 21.6])

plt.tight_layout()

# Save to figs directory
output_file = os.path.join(benchmarking_dir, 'figs', 'tpch_node4_1tb.pdf')
os.makedirs(os.path.dirname(output_file), exist_ok=True)
plt.savefig(output_file, format='pdf', dpi=300, bbox_inches='tight')
print(f"Figure saved to {output_file}")

plt.close()

# Create scatter plot: percent overhead vs vanilla runtime
fig, ax = plt.subplots(figsize=(11, 5.5))

# Compute percent overhead for rowgroup and columns vs vanilla
if 'rowgroup' in pivoted.columns and 'vanilla' in pivoted.columns:
    rowgroup_overhead = ((pivoted['rowgroup'] - pivoted['vanilla']) / pivoted['vanilla']) * 100
    ax.scatter(pivoted['vanilla'], rowgroup_overhead, color=green, label='Rowgroup', alpha=0.7, s=50)

if 'cols' in pivoted.columns and 'vanilla' in pivoted.columns:
    cols_overhead = ((pivoted['cols'] - pivoted['vanilla']) / pivoted['vanilla']) * 100
    ax.scatter(pivoted['vanilla'], cols_overhead, color=orange, label='Columns', alpha=0.7, s=50)

ax.set_xlabel('Vanilla Runtime (minutes)', fontsize=10)
ax.set_ylabel('Percent Overhead vs Vanilla', fontsize=10)
ax.legend(loc='upper left')
ax.grid(alpha=0.3, linestyle='--')
ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

plt.tight_layout()

# Save scatter plot
scatter_output = os.path.join(benchmarking_dir, 'figs', 'tpch_overhead_scatter.pdf')
plt.savefig(scatter_output, format='pdf', dpi=300, bbox_inches='tight')
print(f"Scatter plot saved to {scatter_output}")

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
