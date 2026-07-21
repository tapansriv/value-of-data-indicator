#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

os.chdir("../data/storage_1_node/spark_mod_internal_listener")

def group_data(combined_results, outfile):
    # grouped = combined_results.groupby(['query', 'dataset'])[
    #     ['vanilla_time', 'listener_register_time','listener_bare_time', 'listener_nowrite_time', 'listener_full_time']
    # ].mean().reset_index()
    grouped = combined_results

    # Rename columns for clarity
    grouped.rename(columns={
        'vanilla_time': 'avg_vanilla_time',
        'listener_register_time': 'avg_listener_register_time',
        'listener_bare_time': 'avg_listener_bare_time',
        'listener_nowrite_time': 'avg_listener_nowrite_time',
        'listener_full_time': 'avg_listener_full_time'
    }, inplace=True)

    # Compute derived differences between the averages
    grouped['overhead_register'] = grouped['avg_listener_register_time'] - grouped['avg_vanilla_time']
    grouped['overhead_bare'] = grouped['avg_listener_bare_time'] - grouped['avg_listener_register_time']
    grouped['overhead_nowrite'] = grouped['avg_listener_nowrite_time'] - grouped['avg_listener_bare_time']
    grouped['overhead_write'] = grouped['avg_listener_full_time'] - grouped['avg_listener_nowrite_time']
    grouped['total_overhead'] = grouped['avg_listener_full_time'] - grouped['avg_vanilla_time']

    # Clip negative values to zero (i can change this if needed, but i think assumptions are fair)

    grouped['clipped'] = grouped['total_overhead'] < 0

    grouped['total_overhead'] = grouped['total_overhead'].clip(lower=0)
    grouped['overhead_register'] = grouped['overhead_register'].clip(lower=0)
    grouped['overhead_bare'] = grouped['overhead_bare'].clip(lower=0)
    grouped['overhead_nowrite'] = grouped['overhead_nowrite'].clip(lower=0)
    grouped['overhead_write'] = grouped['overhead_write'].clip(lower=0)

    # Avoid division by zero
    grouped['overhead_register_pct'] = np.where(
        grouped['total_overhead'] == 0, 0,
        (grouped['overhead_register'] / grouped['total_overhead']) * 100
    )

    grouped['overhead_bare_pct'] = np.where(
        grouped['total_overhead'] == 0, 0,
        (grouped['overhead_bare'] / grouped['total_overhead']) * 100
    )

    grouped['overhead_nowrite_pct'] = np.where(
        grouped['total_overhead'] == 0, 0,
        (grouped['overhead_nowrite'] / grouped['total_overhead']) * 100
    )

    grouped['overhead_write_pct'] = np.where(
        grouped['total_overhead'] == 0, 0,
        (grouped['overhead_write'] / grouped['total_overhead']) * 100
    )
    grouped['listener_overhead_pct'] = np.where(
        grouped['avg_vanilla_time'] == 0, 0,
        (grouped['total_overhead'] / grouped['avg_vanilla_time']) * 100
    )
    grouped.to_csv(outfile, index=False)


combined_results = pd.read_csv("final_spark_mod_data.csv")
group_data(combined_results,'experiment_comparison_stats.csv')
grouped = pd.read_csv('experiment_comparison_stats.csv')


labels = grouped['query'] + ' (' + grouped['dataset'] + ')'
# Updated color palette for 4 categories
colors = ['#9467bd', '#1f77b4', '#2ca02c', '#ff7f0e']  # purple, blue, green, orange

plt.figure(figsize=(14, 6))

# Bottom: listener registration overhead
plt.bar(labels, grouped['overhead_register_pct'], label='Listener Registration Overhead', color=colors[0])

# Next layer: plan access and attribute extraction
bottom1 = grouped['overhead_register_pct']
plt.bar(labels, grouped['overhead_bare_pct'], bottom=bottom1,
        label='Plan Traversal + Column Extraction', color=colors[1])

bottom2 = bottom1 + grouped['overhead_bare_pct']
plt.bar(labels, grouped['overhead_nowrite_pct'], bottom=bottom2,
        label='Attribute Processing Overhead', color=colors[2])

bottom3 = bottom2 + grouped['overhead_nowrite_pct']
plt.bar(labels, grouped['overhead_write_pct'], bottom=bottom3,
        label='Write Overhead', color=colors[3])

plt.xticks(rotation=90, fontsize=9)
plt.ylabel("Percent of Total Listener Overhead")
plt.title("Granular Breakdown of Spark Listener Overhead per Query")
plt.ylim(0, 100)

plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0, frameon=False)
plt.tight_layout()
plt.show()





# In[ ]:


# Add labels for x-axis
grouped['label'] = grouped['query'] + ' (' + grouped['dataset'] + ')'

# Sort by total listener time
grouped = grouped.sort_values('avg_listener_full_time', ascending=False)

# Compute stacking bottoms
bottom1 = grouped['avg_vanilla_time']
bottom2 = bottom1 + grouped['overhead_register']
bottom3 = bottom2 + grouped['overhead_bare']
bottom4 = bottom3 + grouped['overhead_nowrite']

# Plot
plt.figure(figsize=(14, 5))
plt.bar(grouped['label'], grouped['avg_vanilla_time'], label='Baseline', color='#4C72B0')
plt.bar(grouped['label'], grouped['overhead_register'], bottom=bottom1,
        label='Listener Registration Overhead', color='#9467bd')  # purple
plt.bar(grouped['label'], grouped['overhead_bare'], bottom=bottom2,
        label='Plan Traversal + Column Extraction', color='#8c564b')  # dark red
plt.bar(grouped['label'], grouped['overhead_nowrite'], bottom=bottom3,
        label='Attribute Processing Overhead', color='#55A868')  # green
plt.bar(grouped['label'], grouped['overhead_write'], bottom=bottom4,
        label='Write Overhead', color='#C44E52')  # red

plt.ylabel("Average Runtime (s)")
plt.title("Decomposition of Spark Query Runtime (Absolute)")
plt.xticks(rotation=90, fontsize=8)
plt.legend(loc='upper right', frameon=False)
plt.grid(axis='y', linestyle='--', linewidth=0.5)
plt.tight_layout()
plt.show()


# In[ ]:


# Add labels for x-axis
grouped['label'] = grouped['query'] + ' (' + grouped['dataset'] + ')'

# Sort by total listener time
grouped = grouped.sort_values('avg_listener_full_time', ascending=False)

# Compute bottom stacks
bottom1 = grouped['avg_vanilla_time']
bottom2 = bottom1 + grouped['overhead_register']
bottom3 = bottom2 + grouped['overhead_bare']
bottom4 = bottom3 + grouped['overhead_nowrite']

# Font weight for consistency
font_weight = 'medium'

# Plot setup
fig, ax = plt.subplots(figsize=(14, 3))  # Match height to Chart 2

# Stacked bars
ax.bar(grouped['label'], grouped['avg_vanilla_time'], label='Baseline', color='#4C72B0')
ax.bar(grouped['label'], grouped['overhead_register'], bottom=bottom1,
       label='Listener Registration Overhead', color='#9467bd')  # purple
ax.bar(grouped['label'], grouped['overhead_bare'], bottom=bottom2,
       label='Plan Traversal + Column Extraction', color='#8c564b')
ax.bar(grouped['label'], grouped['overhead_nowrite'], bottom=bottom3,
       label='Attribute Processing Overhead', color='#55A868')
ax.bar(grouped['label'], grouped['overhead_write'], bottom=bottom4,
       label='Write Overhead', color='#C44E52')

# Axis labels
ax.set_ylabel("Average Runtime (s)", fontweight=font_weight)
ax.set_xlabel("Query", fontweight=font_weight)
ax.set_xticklabels([], fontweight=font_weight)  # Hide x-axis labels
plt.yticks(fontweight=font_weight)

# Add black border around plot
for spine in ax.spines.values():
    spine.set_visible(True)
    spine.set_color('black')
    spine.set_linewidth(1.0)

# Tick styling
ax.tick_params(axis='both', which='both', direction='out', length=4, width=1)

# Remove gridlines
ax.grid(False)

# Add legend
legend = ax.legend(
    loc='upper right',
    bbox_to_anchor=(0.95, 1),
    frameon=True,
    title=None
)
plt.setp(legend.get_texts(), fontweight=font_weight)

# Title and layout
plt.title("Decomposition of Spark Query Runtime (Absolute)", fontweight=font_weight)
plt.tight_layout()
# plt.savefig('spark_runtime_decomposition.pdf', bbox_inches='tight')
plt.show()


# In[ ]:


plt.figure(figsize=(8, 3))  # Slightly less wide than your original 8,3

ax = sns.scatterplot(
    data=grouped,
    x='avg_vanilla_time',
    y='listener_overhead_pct',
    hue='dataset',
    s=50
)

# Add a black border around the entire plot
ax.spines['top'].set_visible(True)  # Make top spine visible
ax.spines['right'].set_visible(True)  # Make right spine visible
for spine in ax.spines.values():
    spine.set_color('black')
    spine.set_linewidth(1.0)

# Add tick marks on both axes
ax.tick_params(axis='both', which='both', direction='out', length=4, width=1)

# Use a more moderate font weight instead of very bold
font_weight = 'medium'  # Options: 'normal', 'medium', 'semibold', 'bold'

# clean style but keep the border
plt.grid(False)

# axis labels with moderate font weight
plt.xlabel('Baseline Query Runtime (s)', fontweight=font_weight)
plt.ylabel('% Difference', fontweight=font_weight)
plt.xticks(fontweight=font_weight)
plt.yticks(fontweight=font_weight)

# move legend inside the box in the top right corner
handles, labels = ax.get_legend_handles_labels()
legend = ax.legend(
    handles=handles,
    labels=labels,
    loc='upper right',  # Position in upper right inside the plot
    frameon=True       # Keep the box around the legend
)

# Make the legend text match the moderate font weight
plt.setp(legend.get_texts(), fontweight=font_weight)

# Adjust layout
plt.tight_layout()

# Save as PDF
# plt.savefig('spark_pct_diff_per_query.pdf', bbox_inches='tight')
plt.show()




grouped['total_overhead'].mean()
plt.figure(figsize=(8, 3))
plt.hist(grouped['total_overhead'], bins=20)

