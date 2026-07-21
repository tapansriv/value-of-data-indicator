#!/usr/bin/env python3
"""
Create a scatter plot comparing vanilla runtimes between unmod_spark and single_node_mod_spark.
X-axis: unmod_spark runtime (minutes)
Y-axis: percent difference of modified over unmod_spark
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import os

# Read the data
benchmarking_dir = os.path.dirname(os.path.dirname(__file__))
data_file = os.path.join(benchmarking_dir, 'data', 'all_results.csv')
df = pd.read_csv(data_file)

# Filter for tpch dataset and vanilla variant
filtered = df[
    (df['dataset'] == 'tpch') & 
    (df['variant'] == 'vanilla')
].copy()

# Extract query number and filter to queries 1-22
def extract_query_num(query_str):
    """Extract numeric part from query string like '1.sql' -> 1"""
    return int(query_str.replace('.sql', ''))

filtered['query_num'] = filtered['query'].apply(extract_query_num)
filtered = filtered[(filtered['query_num'] >= 1) & (filtered['query_num'] <= 22)]

# Group by query and configuration, compute mean runtime
aggregated = filtered.groupby(['query', 'configuration'])['runtime'].mean().reset_index()

# Pivot the data so each configuration becomes a column
pivoted = aggregated.pivot(index='query', columns='configuration', values='runtime').reset_index()

# Sort queries numerically
pivoted['query_num'] = pivoted['query'].apply(extract_query_num)
pivoted = pivoted.sort_values('query_num').reset_index(drop=True)
pivoted = pivoted.drop('query_num', axis=1)

# Check if both configurations exist
if 'unmod_spark' not in pivoted.columns:
    raise ValueError("unmod_spark configuration not found in data")
if 'single_node_mod_spark' not in pivoted.columns:
    raise ValueError("single_node_mod_spark configuration not found in data")

# Convert runtimes from milliseconds to minutes
pivoted['unmod_spark'] = pivoted['unmod_spark'] / 1_000 / 60
pivoted['single_node_mod_spark'] = pivoted['single_node_mod_spark'] / 1_000 / 60

# Compute percent difference: ((modified - unmod) / unmod) * 100
percent_diff = ((pivoted['single_node_mod_spark'] - pivoted['unmod_spark']) / pivoted['unmod_spark']) * 100

# Create scatter plot
fig, ax = plt.subplots(figsize=(10, 6))

blue = "#1F63A9"
ax.scatter(pivoted['unmod_spark'], percent_diff, alpha=0.7, s=50, color=blue)

ax.set_xlabel('Unmodified Spark Runtime (minutes)')
ax.set_ylabel('Percent Difference')
ax.grid(alpha=0.3, linestyle='--')
ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

plt.tight_layout()

# Save scatter plot
output_file = os.path.join(benchmarking_dir, 'figs', 'unmod_vs_mod_scatter.pdf')
os.makedirs(os.path.dirname(output_file), exist_ok=True)
plt.savefig(output_file, format='pdf', dpi=300, bbox_inches='tight')
print(f"Scatter plot saved to {output_file}")

plt.close()

# Print summary statistics
print("\n" + "="*60)
print("Summary Statistics")
print("="*60)
print(f"\nUnmod Spark Runtime (minutes):")
print(f"  Min:    {pivoted['unmod_spark'].min():.2f}")
print(f"  Mean:   {pivoted['unmod_spark'].mean():.2f}")
print(f"  Median: {pivoted['unmod_spark'].median():.2f}")
print(f"  Max:    {pivoted['unmod_spark'].max():.2f}")

print(f"\nPercent Difference (Modified over Unmod):")
print(f"  Min:    {percent_diff.min():.2f}%")
print(f"  25th:   {percent_diff.quantile(0.25):.2f}%")
print(f"  Median: {percent_diff.median():.2f}%")
print(f"  Mean:   {percent_diff.mean():.2f}%")
print(f"  75th:   {percent_diff.quantile(0.75):.2f}%")
print(f"  Max:    {percent_diff.max():.2f}%")
