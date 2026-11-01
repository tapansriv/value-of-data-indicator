"""Does the figure output change with more task-value draws (K) or a longer query history (N)?

Plots each displayed table's median share -- the number the Fig 3/4 boxes are centred on --
against K (left) and N (right), so a reader can see the lines go flat.

  Left:  K draws resampled without replacement from the 2000-draw pool built by
         draws_convergence.py (N=1500, history seed 42), B times; line = median over the B
         experiments of the box median, band = 5th-95th percentile. The paper uses K=100.
  Right: the history sweep (100 draws each, seeds 42-46); line = mean over seeds of the box
         median, band = min-max over seeds. The paper uses N=1500.

Also writes convergence_summary.csv: per table and series, the pool median, the K=100
5-95% half-width, and the largest seed deviation at N=1500 from the same seed at N=2000.

  python convergence_figure.py --sf 30 --tables date_dim,store_sales,... --out-dir ../../r2d7_results/paper_figs
"""
import os
from argparse import ArgumentParser

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_history_sweep import load_schema, series_shares

KS = [10, 25, 50, 100, 200, 500, 1000]
NS = [100, 250, 500, 1000, 1500, 2000]
SEEDS = [42, 43, 44, 45, 46]
ROWS = [("fig3_equal", "Table / Equal\n(Fig 3 Equal, Fig 4 Table)"),
        ("fig3_cardinality", "Table / Cardinality\n(Fig 3)"),
        ("fig4_rowgroup", "Row Group / Equal\n(Fig 4)")]
INK, BAND, MUTED = "#1F63A9", "#1F63A9", "#6B6B6B"
FLOOR = 0.001   # medians below 0.1% are not drawn on the log axis
LABELS = {"tpcds.customer": "customer"}

p = ArgumentParser()
p.add_argument("--sf", type=int, required=True)
p.add_argument("--tables", required=True)
p.add_argument("--results", default="../../r2d7_results")
p.add_argument("--pool-root", default="../data/sweep/draws_pool")
p.add_argument("--sweep-root", default="../data/sweep")
p.add_argument("--out-dir", required=True)
p.add_argument("--B", type=int, default=1000)
p.add_argument("--seed", type=int, default=20261007)
a = p.parse_args()

disp = a.tables.split(",")
tables, c2t = load_schema("../data", "../../tpcds_schema", True)
rng = np.random.default_rng(a.seed)

pool = series_shares(os.path.join(a.pool_root, f"sf{a.sf}", "vdi"), "zipf", tables, c2t, 2000)
draws = {}   # (series, table) -> {K: (lo, mid, hi)}
for s, _ in ROWS:
    arr = np.array([pool[s][t] for t in disp])               # tables x 2000
    for K in KS:
        idx = np.array([rng.choice(arr.shape[1], K, replace=False) for _ in range(a.B)])
        med = np.median(arr[:, idx], axis=2)                  # tables x B
        for i, t in enumerate(disp):
            draws.setdefault((s, t), {})[K] = np.percentile(med[i], [5, 50, 95])
pool_med = {(s, t): np.median(pool[s][t]) for s, _ in ROWS for t in disp}

hist = {}    # (series, table) -> {N: per-seed medians}
for N in NS:
    for seed in SEEDS:
        d = os.path.join(a.sweep_root, f"r2d7_sf{a.sf}", f"N{N}_s{seed}")
        sh = series_shares(d, "zipf", tables, c2t, 100)
        for s, _ in ROWS:
            for t in disp:
                hist.setdefault((s, t), {}).setdefault(N, []).append(np.median(sh[s][t]))

plt.rcParams.update({"font.size": 11})
fig, axes = plt.subplots(len(ROWS), 2, figsize=(9.5, 3.0 * len(ROWS)), sharey="row")
for r, (s, title) in enumerate(ROWS):
    for c, (xs, get, xref, xl) in enumerate([
            (KS, lambda st, x: draws[st][x], 100, "Task-value draws K (log)"),
            (NS, lambda st, x: (min(hist[st][x]), np.mean(hist[st][x]), max(hist[st][x])),
             1500, "Query history size N (log)")]):
        ax = axes[r, c]
        ends = []
        for t in disp:
            pts = np.array([get((s, t), x) for x in xs])
            if pts[:, 1].max() < FLOOR:
                continue
            ax.fill_between(xs, np.maximum(pts[:, 0], FLOOR), pts[:, 2], color=BAND, alpha=0.15, lw=0)
            ax.plot(xs, pts[:, 1], color=INK, lw=1.6)
            ends.append([np.log10(pts[-1, 1]), LABELS.get(t, t), pts[-1, 1]])
        if c == 1:
            # direct labels, nudged apart in log space so none collide
            ends.sort()
            gap = 0.075 * (np.log10(max(e[2] for e in ends)) - np.log10(min(e[2] for e in ends)) + 1) / 1.6
            for i in range(1, len(ends)):
                ends[i][0] = max(ends[i][0], ends[i - 1][0] + gap)
            for y, lab, yv in ends:
                ax.annotate(lab, (xs[-1], yv), xytext=(xs[-1] * 1.12, 10 ** y), textcoords="data",
                            va="center", fontsize=9, color="black",
                            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5, shrinkA=0, shrinkB=2))
        ax.axvline(xref, color=MUTED, ls=":", lw=1)
        if r == 0:
            ax.text(xref, 1.0, f" {'K' if c == 0 else 'N'}={xref}", transform=ax.get_xaxis_transform(),
                    fontsize=9, color=MUTED, va="top", ha="left")
        ax.set_xscale("log"); ax.set_yscale("log")
        ticks = [x for x in xs if x != 1500]
        ax.set_xticks(ticks); ax.set_xticklabels([str(x) for x in ticks])
        ax.minorticks_off()
        ax.grid(axis="y", color="#E5E5E5", lw=0.6)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        if r == len(ROWS) - 1:
            ax.set_xlabel(xl)
        if c == 0:
            ax.set_ylabel(title + "\nmedian share (log)", fontsize=10)
        if r == 0:
            ax.set_title("More task-value draws" if c == 0 else "Longer query history", fontsize=11)
fig.tight_layout()
fig.subplots_adjust(right=0.86)
os.makedirs(a.out_dir, exist_ok=True)
out = os.path.join(a.out_dir, f"convergence_sf{a.sf}.pdf")
fig.savefig(out); fig.savefig(out.replace(".pdf", ".png"), dpi=130)

rows = []
for s, _ in ROWS:
    for t in disp:
        lo, mid, hi = draws[(s, t)][100]
        dev = max(abs(x - y) for x, y in zip(hist[(s, t)][1500], hist[(s, t)][2000]))
        rows.append({"sf": a.sf, "series": s, "table": t, "pool_median_pct": 100 * pool_med[(s, t)],
                     "K100_halfwidth_5_95_pp": 100 * (hi - lo) / 2,
                     "K1000_halfwidth_5_95_pp": 100 * (draws[(s, t)][1000][2] - draws[(s, t)][1000][0]) / 2,
                     "N1500_vs_N2000_max_seed_dev_pp": 100 * dev})
pd.DataFrame(rows).round(3).to_csv(os.path.join(a.out_dir, f"convergence_summary_sf{a.sf}.csv"), index=False)
print("wrote", out)
