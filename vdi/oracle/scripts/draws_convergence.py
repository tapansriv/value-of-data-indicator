"""How many task-value draws do the Sec 4.4 figures need?

Sec 4.4 draws query (task) values 100 times and shows each table's share of total
value as a box over those 100 draws. The question is whether 100 is enough: would
another set of 100 draws produce the same boxes and the same orderings?

Method (Monte Carlo error of a Monte Carlo experiment):

  1. Draw a large pool of K_MAX task-value vectors from the same Zipf(2.0) the paper
     uses, with a seed independent of the paper's (generate_oracle_vals.py), and run
     the unchanged pipeline (assign_val_to_de.py, N=1500, history seed 42) on it.
     Each pool member is one draw; it gives a share for every (series, table).
  2. Treat the pool as the population. For K in K_VALUES, resample B experiments of
     K draws with replacement and recompute every statistic a box shows (median,
     quartiles). The spread across resamples is the Monte Carlo standard error
     (MCSE) of that statistic at K draws.
  3. Cross-check without resampling: split the pool into K_MAX/100 disjoint blocks of
     100 draws, i.e. genuinely independent repeats of the paper's experiment, and
     compare their spread to the bootstrap MCSE at K=100.
  4. Ordering reproducibility: for every comparison the figures display (strategy vs
     strategy and granularity vs granularity per table, VDI median vs the frequency
     baseline), the fraction of K-draw experiments that reproduce the pool's order.

Shares are bounded in [0, 1], so their sampling distribution obeys the CLT even though
Zipf(2.0) itself has an infinite mean -- raw (unnormalized) totals would not converge,
which is one more reason the figures show normalized shares. MCSE should therefore
fall as 1/sqrt(K); the script fits the slope to check.

Adequacy criteria, fixed before looking at the results:
  C1  MCSE of every displayed median at K=100 is <= 0.5 percentage points (so a 95%
      Monte Carlo interval is about +/-1 pp, the precision Sec 4.4 quotes shares to).
  C2  Every displayed ordering whose pool gap is >= 1 pp is reproduced by >= 95% of
      100-draw experiments.
  C3  The ranking of all tables by median share, per series, has Spearman rho >= 0.95
      against the pool in >= 95% of 100-draw experiments.
K* is the smallest K in K_VALUES meeting all three.
"""

import json
import os
import subprocess
import sys
from argparse import ArgumentParser

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy import stats

from analyze_history_sweep import (TPCDS_TABLES, FIGURE_TABLES_TPCDS, PALETTE,
                                   load_schema, series_shares)

K_VALUES = [10, 25, 50, 100, 200, 500, 1000]
# fig4_table is identical to fig3_equal (see analyze_history_sweep.SERIES_LABEL)
SERIES = ["fig3_full", "fig3_equal", "fig3_cardinality", "fig4_column", "fig4_rowgroup"]
SERIES_LABEL = {"fig3_full": "Full", "fig3_equal": "Equal = Table",
                "fig3_cardinality": "Cardinality", "fig4_column": "Column",
                "fig4_rowgroup": "Row Group"}
# pairs of series each figure puts side by side in one table's group
FIG_PAIRS = [("fig3_full", "fig3_equal"), ("fig3_full", "fig3_cardinality"),
             ("fig3_equal", "fig3_cardinality"),
             ("fig3_equal", "fig4_column"), ("fig4_column", "fig4_rowgroup"),
             ("fig3_equal", "fig4_rowgroup")]
# which frequency baseline each series is drawn against
FREQ_FOR = {"fig3_full": "table", "fig3_equal": "table", "fig3_cardinality": "table",
            "fig4_column": "column", "fig4_rowgroup": "rowgroup"}

C1_MCSE = 0.005
C2_GAP, C2_RATE = 0.01, 0.95
C3_RHO, C3_RATE = 0.95, 0.95


def run(cmd):
    print("  $ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def build_pool(sf_dir, query_set, pool_dir, k_max, value_seed):
    """Task values and VDI for K_MAX draws, through the unchanged pipeline."""
    if os.path.exists(os.path.join(pool_dir, "vdi", "manifest.json")):
        print(f"  pool exists: {pool_dir}")
        return
    py = sys.executable
    run([py, "generate_oracle_vals.py", "zipf", "--tpcds-only", "--query-set", query_set,
         "--num-trials", str(k_max), "--seed", str(value_seed),
         "--out-dir", os.path.join(pool_dir, "values")])
    run([py, "assign_val_to_de.py", "--tpcds-only", "--distro", "zipf",
         "--num-trials", str(k_max), "-n", "1500", "-s", "42",
         "--logs-dir", os.path.join(sf_dir, "logs"), "--query-set", query_set,
         "--values-dir", os.path.join(pool_dir, "values"),
         "--columns-in-queries", os.path.join(sf_dir, "tpcds_columns_in_queries.json"),
         "--cardinality", os.path.join(sf_dir, "tpcds_cardinality.json"),
         "-o", os.path.join(pool_dir, "vdi")])


def frequency_baselines(vdi_dir, tables, col_to_tbl):
    """Normalized frequency share per table at each granularity, as the figures draw it."""
    t = json.load(open(os.path.join(vdi_dir, "boris_data_val_tbls.json")))
    c = json.load(open(os.path.join(vdi_dir, "boris_data_val_cols.json")))
    r = json.load(open(os.path.join(vdi_dir, "boris_data_val_rgs_tbls.json")))
    col = {x: 0.0 for x in tables}
    for k, v in c.items():
        col[col_to_tbl[k]] += v
    rg = {x: sum(r.get(x, {}).values()) for x in tables}
    out = {}
    for name, d in [("table", {x: t.get(x, 0.0) for x in tables}), ("column", col),
                    ("rowgroup", rg)]:
        tot = sum(d.values())
        out[name] = {x: d[x] / tot for x in tables}
    return out


def load_array(vdi_dir, tables, col_to_tbl, k):
    """shares[s, t, draw] for the series in SERIES."""
    sh = series_shares(vdi_dir, "zipf", tables, col_to_tbl, k)
    return np.array([[sh[s][t] for t in tables] for s in SERIES])


def comparisons(tables, fig_tables, freq):
    """Every ordering the figures display: (kind, table, a, b); b may be a baseline."""
    out = []
    for t in fig_tables:
        for a, b in FIG_PAIRS:
            out.append(("series", t, a, b))
        for s in SERIES:
            out.append(("frequency", t, s, FREQ_FOR[s]))
    return out


def analyze_sf(sf, pool, paper, tables, fig_tables, freq, rng, B, out_dir):
    k_max = pool.shape[2]
    ti = {t: i for i, t in enumerate(tables)}
    si = {s: i for i, s in enumerate(SERIES)}
    fig_idx = [ti[t] for t in fig_tables]

    ref_med = np.percentile(pool, 50, axis=2)
    ref_q1 = np.percentile(pool, 25, axis=2)
    ref_q3 = np.percentile(pool, 75, axis=2)
    comps = comparisons(tables, fig_tables, freq)

    def comp_value(med, c):
        kind, t, a, b = c
        lhs = med[..., si[a], ti[t]]
        rhs = med[..., si[b], ti[t]] if kind == "series" else freq[b][t]
        return lhs - rhs

    ref_gap = np.array([comp_value(ref_med, c) for c in comps])

    mcse_rows, comp_rows, rank_rows = [], [], []
    for K in K_VALUES:
        idx = rng.integers(0, k_max, size=(B, K))
        # [B, S, T] for each statistic; one series at a time to bound memory
        shape = (B, len(SERIES), len(tables))
        med, q1, q3, mean = (np.empty(shape) for _ in range(4))
        for i in range(len(SERIES)):
            samp = pool[i][:, idx]                   # T, B, K
            q = np.percentile(samp, [25, 50, 75], axis=2)
            q1[:, i, :], med[:, i, :], q3[:, i, :] = (x.T for x in q)
            mean[:, i, :] = samp.mean(axis=2).T
        for s in SERIES:
            for t in tables:
                i, j = si[s], ti[t]
                mcse_rows.append({
                    "sf": sf, "K": K, "series": s, "table": t,
                    "in_figure": t in fig_tables,
                    "pool_median": ref_med[i, j], "pool_iqr": ref_q3[i, j] - ref_q1[i, j],
                    "mcse_median": med[:, i, j].std(ddof=1),
                    "mcse_q1": q1[:, i, j].std(ddof=1),
                    "mcse_q3": q3[:, i, j].std(ddof=1),
                    "mcse_mean": mean[:, i, j].std(ddof=1),
                })
        for c, g in zip(comps, ref_gap):
            v = comp_value(med, c)
            comp_rows.append({"sf": sf, "K": K, "kind": c[0], "table": c[1],
                              "a": c[2], "b": c[3], "pool_gap": g,
                              "agree_rate": float(np.mean(np.sign(v) == np.sign(g)))})
        for s in SERIES:
            i = si[s]
            rhos = np.array([stats.spearmanr(ref_med[i], med[b, i]).statistic
                             for b in range(B)])
            rank_rows.append({"sf": sf, "K": K, "series": s,
                              "rho_p05": np.percentile(rhos, 5),
                              "rho_median": np.median(rhos),
                              "frac_rho_ge": float(np.mean(rhos >= C3_RHO))})
        print(f"  SF{sf} K={K} done", flush=True)

    mcse = pd.DataFrame(mcse_rows)
    comp = pd.DataFrame(comp_rows)
    rank = pd.DataFrame(rank_rows)

    # independent-block cross-check at K=100
    nblk = k_max // 100
    blocks = pool[:, :, :nblk * 100].reshape(pool.shape[0], pool.shape[1], nblk, 100)
    blk_sd = np.percentile(blocks, 50, axis=3).std(axis=2, ddof=1)       # S, T
    boot = mcse[mcse.K == 100].set_index(["series", "table"])["mcse_median"]
    xcheck = pd.DataFrame([{"sf": sf, "series": s, "table": t,
                            "block_sd_median": blk_sd[si[s], ti[t]],
                            "bootstrap_mcse_median": boot[(s, t)]}
                           for s in SERIES for t in fig_tables])

    # where does the paper's own set of 100 draws sit?
    paper_med = np.percentile(paper, 50, axis=2)
    z = [{"sf": sf, "series": s, "table": t,
          "paper_median": paper_med[si[s], ti[t]], "pool_median": ref_med[si[s], ti[t]],
          "z": (paper_med[si[s], ti[t]] - ref_med[si[s], ti[t]]) / boot[(s, t)]
          if boot[(s, t)] > 0 else 0.0}
         for s in SERIES for t in fig_tables]
    paperz = pd.DataFrame(z)

    # 1/sqrt(K) check: slope of log MCSE vs log K for the displayed medians
    slopes = []
    for s in SERIES:
        for t in fig_tables:
            d = mcse[(mcse.series == s) & (mcse.table == t)]
            if (d.mcse_median > 0).all():
                slopes.append(np.polyfit(np.log(d.K), np.log(d.mcse_median), 1)[0])

    # criteria
    verdict = {}
    for K in K_VALUES:
        m = mcse[(mcse.K == K) & mcse.in_figure]
        c = comp[(comp.K == K) & (comp.pool_gap.abs() >= C2_GAP)]
        r = rank[rank.K == K]
        verdict[K] = {
            "C1_max_mcse_median_pp": 100 * m.mcse_median.max(),
            "C1": bool(m.mcse_median.max() <= C1_MCSE),
            "C2_min_agree_rate_gap_ge_1pp": float(c.agree_rate.min()) if len(c) else 1.0,
            "C2_n_orderings": int(len(c)),
            "C2": bool(len(c) == 0 or c.agree_rate.min() >= C2_RATE),
            "C3_min_frac_rho_ge": float(r.frac_rho_ge.min()),
            "C3": bool(r.frac_rho_ge.min() >= C3_RATE),
        }
        verdict[K]["all"] = verdict[K]["C1"] and verdict[K]["C2"] and verdict[K]["C3"]
    kstar = next((K for K in K_VALUES if verdict[K]["all"]), None)

    summary = {
        "sf": sf, "k_max": int(k_max), "bootstrap_B": B, "figure_tables": fig_tables,
        "criteria": {"C1_mcse_max": C1_MCSE, "C2_gap": C2_GAP, "C2_rate": C2_RATE,
                     "C3_rho": C3_RHO, "C3_rate": C3_RATE},
        "verdict_by_K": verdict, "K_star": kstar,
        "mcse_slope_vs_K": {"median": float(np.median(slopes)),
                            "min": float(np.min(slopes)), "max": float(np.max(slopes))},
        "block_crosscheck_ratio_block_over_bootstrap": {
            "median": float((xcheck.block_sd_median / xcheck.bootstrap_mcse_median).median()),
            "n_blocks": int(nblk)},
        "paper_draw_max_abs_z": float(paperz.z.abs().max()),
        "unresolved_at_100": comp[(comp.K == 100) & (comp.agree_rate < C2_RATE)]
            .sort_values("pool_gap", key=abs).to_dict("records"),
    }
    os.makedirs(out_dir, exist_ok=True)
    mcse.to_csv(os.path.join(out_dir, "mcse.csv"), index=False)
    comp.to_csv(os.path.join(out_dir, "orderings.csv"), index=False)
    rank.to_csv(os.path.join(out_dir, "rank_stability.csv"), index=False)
    xcheck.to_csv(os.path.join(out_dir, "block_crosscheck.csv"), index=False)
    paperz.to_csv(os.path.join(out_dir, "paper_draw_position.csv"), index=False)
    json.dump(summary, open(os.path.join(out_dir, "summary.json"), "w"), indent=2,
              default=float)
    return mcse, comp, summary


def _style(ax):
    ax.set_xscale("log")
    ax.set_xticks(K_VALUES)
    ax.set_xticklabels([str(k) for k in K_VALUES])
    ax.tick_params(axis="x", which="minor", bottom=False)
    ax.grid(axis="y", alpha=0.3, linestyle="--", linewidth=0.8)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.axvline(100, color="#5c5c5c", linewidth=1, linestyle=":", zorder=1)


def plot(all_mcse, all_comp, sfs, out_dir):
    """Color = quantity, marker = scale factor (the SFs nearly coincide)."""
    markers = ["o", "s", "^"]
    worst_c, typ_c = PALETTE[0], PALETTE[1]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    ax = axes[0]
    for sf, mk in zip(sfs, markers):
        m = all_mcse[(all_mcse.sf == sf) & all_mcse.in_figure]
        worst = 100 * m.groupby("K").mcse_median.max()
        typ = 100 * m.groupby("K").mcse_median.median()
        ax.plot(worst.index, worst.values, marker=mk, markersize=7, linewidth=2, color=worst_c)
        ax.plot(typ.index, typ.values, marker=mk, markersize=7, linewidth=2, color=typ_c)
    k = np.array(K_VALUES, dtype=float)
    anchor = 100 * all_mcse[(all_mcse.K == 100) & all_mcse.in_figure].mcse_median.max()
    ax.plot(k, anchor * np.sqrt(100 / k), color="#8a8984", linewidth=1, linestyle="--",
            zorder=1)
    ax.axhline(100 * C1_MCSE, color="#5c5c5c", linewidth=1.5, linestyle=":")
    ax.annotate("C1 threshold, 0.5 pp", xy=(K_VALUES[0], 100 * C1_MCSE), xytext=(2, 4),
                textcoords="offset points", color="#5c5c5c", fontsize=9)
    ax.set_yscale("log")
    ax.set_xlabel("Task-value draws K")
    ax.set_ylabel("MC std. error of box median (pp)")
    ax.set_title("Box medians: Monte Carlo error vs draws", fontsize=11)
    _style(ax)
    handles = [Line2D([0], [0], color=worst_c, linewidth=2,
                      label="worst median (store_sales)"),
               Line2D([0], [0], color=typ_c, linewidth=2, label="typical median"),
               Line2D([0], [0], color="#8a8984", linewidth=1, linestyle="--",
                      label="1/sqrt(K)")]
    handles += [Line2D([0], [0], color="#52514e", marker=mk, linestyle="none",
                       markersize=7, label=f"SF{sf}") for sf, mk in zip(sfs, markers)]
    ax.legend(handles=handles, fontsize=8, frameon=False, loc="upper right", ncol=2)

    ax = axes[1]
    for sf, mk in zip(sfs, markers):
        c = all_comp[(all_comp.sf == sf) & (all_comp.pool_gap.abs() >= C2_GAP)]
        worst = c.groupby("K").agree_rate.min()
        frac = c.groupby("K").agree_rate.apply(lambda x: np.mean(x >= C2_RATE))
        ax.plot(worst.index, worst.values, marker=mk, markersize=7, linewidth=2, color=worst_c)
        ax.plot(frac.index, frac.values, marker=mk, markersize=7, linewidth=2, color=typ_c)
    ax.axhline(C2_RATE, color="#5c5c5c", linewidth=1.5, linestyle=":")
    ax.annotate("C2 threshold, 95%", xy=(K_VALUES[-1], C2_RATE), xytext=(-95, -14),
                textcoords="offset points", color="#5c5c5c", fontsize=9)
    ax.set_ylim(0.4, 1.02)
    ax.set_xlabel("Task-value draws K")
    ax.set_ylabel("Fraction")
    ax.set_title("Displayed orderings with gap >= 1 pp", fontsize=11)
    _style(ax)
    handles = [Line2D([0], [0], color=worst_c, linewidth=2,
                      label="reproduction rate, worst ordering"),
               Line2D([0], [0], color=typ_c, linewidth=2,
                      label="orderings reproduced in >= 95% of experiments")]
    ax.legend(handles=handles, fontsize=8, frameon=False, loc="lower right")
    fig.tight_layout()
    path = os.path.join(out_dir, "draws_convergence.pdf")
    fig.savefig(path)
    fig.savefig(path.replace(".pdf", ".png"), dpi=160)
    plt.close(fig)
    return path


if __name__ == "__main__":
    parser = ArgumentParser(description="Convergence in the number of task-value draws")
    parser.add_argument("--results", default="../../r2d7_results")
    parser.add_argument("--sfs", type=int, nargs="+", default=[30, 60, 100])
    parser.add_argument("--k-max", type=int, default=2000)
    parser.add_argument("--value-seed", type=int, default=20260927,
                        help="Seed for the pool's task values; deliberately not 42, "
                             "so the pool is independent of the paper's draws")
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--pool-root", default="../data/sweep/draws_pool",
                        help="Pool outputs (large; gitignored under data/sweep)")
    parser.add_argument("--out-dir", default="../../r2d7_results/num_draws")
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--query-set", default=None,
                        help="Query-set JSON (default: <results>/common_completed_sf30_60_100.json)")
    parser.add_argument("--tables", default=None,
                        help="Comma-separated figure tables to check orderings on "
                             "(default: FIGURE_TABLES_TPCDS)")
    args = parser.parse_args()

    qset = os.path.abspath(args.query_set or os.path.join(args.results, "common_completed_sf30_60_100.json"))
    tables, col_to_tbl = load_schema("../data", "../../tpcds_schema", tpcds_only=True)
    fig_tables = args.tables.split(",") if args.tables else FIGURE_TABLES_TPCDS
    rng = np.random.default_rng(0)

    all_mcse, all_comp = [], []
    for sf in args.sfs:
        sf_dir = os.path.abspath(os.path.join(args.results, f"sf{sf}"))
        pool_dir = os.path.join(args.pool_root, f"sf{sf}")
        print(f"SF{sf}: building pool of {args.k_max} draws", flush=True)
        build_pool(sf_dir, qset, pool_dir, args.k_max, args.value_seed)
        if args.build_only:
            continue
        pool = load_array(os.path.join(pool_dir, "vdi"), tables, col_to_tbl, args.k_max)
        paper = load_array(os.path.join(sf_dir, "vdi"), tables, col_to_tbl, 100)
        freq = frequency_baselines(os.path.join(sf_dir, "vdi"), tables, col_to_tbl)
        mcse, comp, summary = analyze_sf(sf, pool, paper, tables, fig_tables,
                                         freq, rng, args.bootstrap,
                                         os.path.join(args.out_dir, f"sf{sf}"))
        all_mcse.append(mcse)
        all_comp.append(comp)
        print(json.dumps({k: summary[k] for k in
                          ["K_star", "mcse_slope_vs_K",
                           "block_crosscheck_ratio_block_over_bootstrap",
                           "paper_draw_max_abs_z"]}, indent=2, default=float))
        print(json.dumps(summary["verdict_by_K"], indent=1, default=float))

    if not args.build_only:
        path = plot(pd.concat(all_mcse), pd.concat(all_comp), args.sfs, args.out_dir)
        print(f"figure: {path}")
