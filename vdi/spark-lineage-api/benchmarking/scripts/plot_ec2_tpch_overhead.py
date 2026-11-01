#!/usr/bin/env python3
"""
R2D16: grouped bar chart of TPC-H SF1000 runtimes per query for the EC2 scale-up runs,
one figure per node count. Same style as the paper's tpch_node4_1tb.pdf
(legacy_results/cluster/.../plot_spark_internal_tpch.py).

    python3 plot_ec2_tpch_overhead.py [out_dir]

Reads data/ec2/n{1,4,8,16}-v3/rep*/<variant>/spark_internal_listener_<variant>_results.csv
and averages runtime over reps. Writes figs/ec2/tpch_ec2_node<N>_1tb.pdf (and to out_dir
if given).
"""

import glob
import os
import shutil
import sys

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Colors
red = "#E65742"
orange = "#FE9C22"
green = "#ADDC5A"
blue = "#1F63A9"

variant_order = ['vanilla', 'bare', 'cols', 'rowgroup']
colors_map = {'bare': red, 'cols': orange, 'rowgroup': green, 'vanilla': blue}
label_map = {'bare': 'Listener Only', 'cols': 'Columns', 'rowgroup': 'Row Group', 'vanilla': 'Vanilla'}

NODES = [1, 4, 8, 16]

benchmarking_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fig_dir = os.path.join(benchmarking_dir, 'figs', 'ec2')
out_dir = sys.argv[1] if len(sys.argv) > 1 else None


def query_num(q):
    return int(q.replace('.sql', '').lstrip('q'))


def load(run_dir):
    frames = []
    for f in glob.glob(os.path.join(run_dir, 'rep*', '*', 'spark_internal_listener_*_results.csv')):
        df = pd.read_csv(f)
        df['variant'] = os.path.basename(os.path.dirname(f))
        df['rep'] = os.path.basename(os.path.dirname(os.path.dirname(f)))
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    # Same exclusion rule as overhead_summary.py: failed runs and listener timeouts never averaged in.
    bad = (df['runtime'] < 0) | (df['listener_timeout'].astype(str).str.lower() == 'true')
    if bad.any():
        print(f"  excluding {bad.sum()} rows (failed or listener timeout)")
    df = df[~bad & (df['dataset'] == 'tpch')].copy()
    df['query_num'] = df['query'].apply(query_num)
    return df[(df['query_num'] >= 1) & (df['query_num'] <= 22)]


# Size and font match the placement subfigures (Figs 8/10), set at the same printed width.
font = {'size': 22}
plt.rc('font', **font)
os.makedirs(fig_dir, exist_ok=True)

for n in NODES:
    run_dir = os.path.join(benchmarking_dir, 'data', 'ec2', f'n{n}-v3')
    print(f"== n{n}-v3")
    df = load(run_dir)
    reps = df.groupby(['query_num', 'variant'])['rep'].nunique()
    print(f"  reps per (query, variant): {sorted(reps.unique())}")

    pivoted = (df.groupby(['query_num', 'variant'])['runtime'].mean()
                 .unstack('variant').sort_index() / 1_000 / 60)  # ms -> minutes

    fig, ax = plt.subplots(figsize=(8, 5.25))
    x = np.arange(len(pivoted))
    width = 0.2
    for i, variant in enumerate(variant_order):
        offset = (i - len(variant_order) / 2 + 0.5) * width
        ax.bar(x + offset, pivoted[variant], width, label=label_map[variant], color=colors_map[variant])

    ax.set_xticks(x)
    # Every other label: all 22 collide at font 22.
    ax.set_xticklabels([str(q) if q % 2 else '' for q in pivoted.index])
    ax.set_ylabel('Time (minutes)')
    ax.set_xlabel('TPC-H Query Number')
    if n == NODES[-1]:  # one legend per figure, on its last subfigure, as in Figs 8/10
        # 18pt (as in the full-width placement figure) so it ends before q17.
        ax.legend(ncol=2, loc='upper left', fontsize=18, handlelength=1, handletextpad=0.4,
                  columnspacing=0.8, borderaxespad=0.3)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_xlim([-0.5, len(pivoted) - 0.5])
    plt.tight_layout()

    out = os.path.join(fig_dir, f'tpch_ec2_node{n}_1tb.pdf')
    plt.savefig(out, format='pdf', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  saved {out}")
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        shutil.copy(out, out_dir)

    for v in ['bare', 'cols', 'rowgroup']:
        pct = (pivoted[v] - pivoted['vanilla']) / pivoted['vanilla'] * 100
        tot = (pivoted[v].sum() - pivoted['vanilla'].sum()) / pivoted['vanilla'].sum() * 100
        print(f"  {label_map[v]:<13} vs Vanilla: per-query mean {pct.mean():+.2f}%, "
              f"min {pct.min():+.2f}%, max {pct.max():+.2f}%; total {tot:+.2f}%")
