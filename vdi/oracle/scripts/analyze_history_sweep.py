"""Quantify how query-history size N moves the Sec 4.4 results (R2D8, R2D13).

Three layers, matching what a reviewer can check:

  1. The figures themselves, regenerated per N by sweep_history.py.
  2. Rank stability: Spearman rho / Kendall tau of the table ranking at N
     against the largest N, per series. Reports N*, the smallest N at which
     every series is at or above the threshold.
  3. The specific claims Sec 4.4 makes in prose, tracked as a function of N.
     A correlation coefficient is taken on faith; "every claim holds for
     N >= X" is checkable.

Normalization mirrors graph_comp_oracles.py exactly so the numbers here are the
ones the figures show:
  Fig 3 series (table granularity) normalize each trial by the sum over tables
  under that dividing strategy; Fig 4 series normalize by the total task value.
"""

import json
import math
import os
from argparse import ArgumentParser

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# tables shown in Figures 3 and 4 (plot_divide / graph_granularity_comp).
# Pre-revision set, used by the 2026-09-13 Drill sweep; --figure-tables overrides.
FIGURE_TABLES = ["date_dim", "tpcds.customer", "store", "store_sales",
                 "web_sales", "lineitem", "orders"]
# graph_comp_oracles.SUBSET_TABLES under --tpcds-only (lineitem dropped)
FIGURE_TABLES_TPCDS = ["date_dim", "store_sales", "tpcds.customer", "store",
                       "household_demographics", "customer_demographics"]

TPCDS_TABLES = ["call_center", "catalog_page", "catalog_returns",
                "catalog_sales", "tpcds.customer", "customer_address",
                "customer_demographics", "date_dim", "household_demographics",
                "income_band", "inventory", "item", "promotion", "reason",
                "ship_mode", "store", "store_returns", "store_sales",
                "time_dim", "warehouse", "web_page", "web_returns",
                "web_sales", "web_site"]


def load_schema(static_dir, schema_dir, tpcds_only=False):
    tpch_tables = [x.strip() for x in open(os.path.join(static_dir, "table_names.csv"))]
    tables = list(TPCDS_TABLES) if tpcds_only else TPCDS_TABLES + tpch_tables
    tpch_cols = json.load(open(os.path.join(static_dir, "tpch_columns_in_tables.json")))
    tpcds_cols = json.load(open(os.path.join(schema_dir, "tpcds_columns_in_tables.json")))
    col_to_tbl = {}
    for tbl, cols in tpch_cols.items():
        for c in cols:
            col_to_tbl[c] = tbl
    for tbl, cols in tpcds_cols.items():
        for c in cols:
            col_to_tbl[c] = "tpcds.customer" if tbl == "customer" else tbl
    return tables, col_to_tbl


def series_shares(data_dir, distro, tables, col_to_tbl, num_trials):
    """Per-series {table: [share per trial]}, matching the figures."""
    out = {}

    # --- Figure 3: dividing strategies at Table granularity
    for divide in ["full", "equal", "cardinality"]:
        vals = json.load(open(os.path.join(
            data_dir, f"data_val_tbls_{distro}_{divide}.json")))
        acc = {t: [] for t in tables}
        for it in range(num_trials):
            trial = vals[str(it)]
            tot = sum(trial.values())
            for t in tables:
                acc[t].append(trial[t] / tot if tot else 0.0)
        out[f"fig3_{divide}"] = acc

    # --- Figure 4: granularities under Equal, normalized by total task value
    totals = json.load(open(os.path.join(data_dir, f"total_vals_{distro}.json")))
    tbl_vals = json.load(open(os.path.join(data_dir, f"data_val_tbls_{distro}_equal.json")))
    col_vals = json.load(open(os.path.join(data_dir, f"data_val_cols_{distro}_equal.json")))
    rg_vals = json.load(open(os.path.join(data_dir, f"data_val_rgs_tbls_{distro}_equal.json")))

    acc_t = {t: [] for t in tables}
    acc_c = {t: [] for t in tables}
    acc_r = {t: [] for t in tables}
    for it in range(num_trials):
        k = str(it)
        total = totals[k]
        for t in tables:
            acc_t[t].append(tbl_vals[k][t] / total)
        col_agg = {t: 0.0 for t in tables}
        for col, v in col_vals[k].items():
            col_agg[col_to_tbl[col]] += v
        for t in tables:
            acc_c[t].append(col_agg[t] / total)
        rg_agg = {t: 0.0 for t in tables}
        for t, rgs in rg_vals[k].items():
            rg_agg[t] = sum(rgs.values())
        for t in tables:
            acc_r[t].append(rg_agg[t] / total)
    out["fig4_table"] = acc_t
    out["fig4_column"] = acc_c
    out["fig4_rowgroup"] = acc_r
    return out


def frequency_shares(data_dir, tables):
    """Glavic et al. baseline: the red line in Figure 3.

    The raw value for a table is the summed relative frequency of the queries
    touching it, i.e. the fraction of the history that accesses that table --
    which is the '60% of queries' number Sec 4.4 quotes for date_dim.
    """
    raw = json.load(open(os.path.join(data_dir, "boris_data_val_tbls.json")))
    # NB: this file keys TPC-H customer as "customer" and TPC-DS customer as
    # "tpcds.customer" -- do not collapse them. plot_divide() looks the red line
    # up as label.lower(), which resolves "Customer" to the TPC-H table; see the
    # note in the results write-up.
    tot = sum(raw.values())
    return raw, {t: (raw.get(t, 0.0) / tot if tot else 0.0) for t in tables}



# Validated categorical palette (six slots, passes the lightness/chroma/CVD
# gates on the adjacent pairlist). Deliberately NOT the Fig 3/4 palette: that
# one puts Equal (#7F9C64) next to Cardinality (#2CBA9A) at normal-vision
# delta-E 10, below the 15 floor.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
# fig4_table is omitted from the plot: under the Equal dividing strategy the sum
# over tables equals the total task value, so Fig 3's Equal series and Fig 4's
# Table series are the same quantity (verified identical to 1e-16). Both are
# still written to sweep_summary.csv; plotting both just hides one line.
SERIES_LABEL = {
    "fig3_full": "Full (Fig 3)",
    "fig3_equal": "Equal (Fig 3) = Table (Fig 4)",
    "fig3_cardinality": "Cardinality (Fig 3)",
    "fig4_column": "Column (Fig 4)",
    "fig4_rowgroup": "Row Group (Fig 4)",
}


def _style(ax, ns):
    ax.set_xscale("log")
    ax.set_xticks(ns)
    ax.set_xticklabels([str(n) for n in ns])
    ax.tick_params(axis="x", which="minor", bottom=False)
    ax.grid(axis="y", alpha=0.3, linestyle="--", linewidth=0.8)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)


def plot_rank_stability(ranks, out_dir, threshold, scope="figure_tables"):
    sub = ranks[(ranks.scope == scope) & (ranks.series != "frequency")]
    ns = sorted(sub.N.unique())
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    for i, series in enumerate(SERIES_LABEL):
        d = sub[sub.series == series].groupby("N")["spearman"].mean().reindex(ns)
        ax.plot(ns, d.values, marker="o", markersize=7, linewidth=2,
                color=PALETTE[i % len(PALETTE)], label=SERIES_LABEL[series])
    ax.axhline(threshold, color="#5c5c5c", linewidth=1.5, linestyle=":",
               zorder=1)
    ax.annotate(f"rho = {threshold}", xy=(ns[0], threshold), xytext=(0, -14),
                textcoords="offset points", color="#5c5c5c", fontsize=9)
    ax.set_xlabel("Query history size N")
    ax.set_ylabel(f"Spearman rho vs N={max(ns)}")
    ax.set_title(f"VDI table ranking stability vs history size ({scope.replace('_', ' ')})",
                 fontsize=11)
    _style(ax, ns)
    ax.legend(fontsize=9, frameon=False, loc="lower right")
    fig.tight_layout()
    path = os.path.join(out_dir, f"history_rank_stability_{scope}.pdf")
    fig.savefig(path)
    fig.savefig(path.replace(".pdf", ".png"), dpi=160)
    plt.close(fig)
    return path


def plot_date_dim(claims, out_dir):
    """The Sec 4.4 date_dim numbers as a function of history size.

    Three quantities on their true scales, because the figures do not treat the
    frequency baseline the same way:
      - raw access fraction: the share of the history touching date_dim. This is
        the "60% of queries" number, and it is what Figure 3 draws as the red
        line (graph_divide_comp calls collect_boris_data with normalized=False).
      - normalized frequency share: what Figure 4 plots for the same baseline.
      - VDI share under Full and Equal: the boxes in Figure 3.

    Note the first is a fraction of queries and the others are shares of total
    value; they do not live on a common scale. Plotted together only to show
    that each is flat in N.
    """
    d = claims.groupby("N").mean(numeric_only=True)
    ns = list(d.index)
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.plot(ns, d["date_dim_access_fraction"], marker="s", markersize=7,
            linewidth=2, color=PALETTE[1],
            label="Access fraction (share of queries)")
    ax.plot(ns, d["date_dim_share_full"], marker="o", markersize=7, linewidth=2,
            color=PALETTE[0], label="VDI share, Full")
    ax.plot(ns, d["date_dim_share_equal"], marker="^", markersize=7, linewidth=2,
            color=PALETTE[2], label="VDI share, Equal")
    ax.plot(ns, d["date_dim_frequency_share"], marker="D", markersize=6,
            linewidth=2, linestyle="--", color=PALETTE[3],
            label="Frequency share (red marks, Figs 3-4)")
    ax.set_xlabel("Query history size N")
    ax.set_ylabel("Fraction / share")
    ax.set_title("date_dim: Sec 4.4 quantities are flat in history size", fontsize=11)
    ax.set_ylim(0, 1.0)
    _style(ax, ns)
    ax.legend(fontsize=9, frameon=False, loc="center right")
    fig.tight_layout()
    path = os.path.join(out_dir, "history_date_dim_gap.pdf")
    fig.savefig(path)
    fig.savefig(path.replace(".pdf", ".png"), dpi=160)
    plt.close(fig)
    return path


def ci_halfwidth(x, conf=0.95):
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return float("nan")
    return float(stats.t.ppf(0.5 + conf / 2, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x)))


if __name__ == "__main__":
    parser = ArgumentParser(description="Analyze the query-history sweep")
    parser.add_argument("--data-root", default="../data/sweep")
    parser.add_argument("--static-dir", default="../data",
                        help="Where the static schema inputs live")
    parser.add_argument("--schema-dir", default="../../tpcds_schema")
    parser.add_argument("--distro", default="zipf", choices=["normal", "zipf"],
                        help="Sec 4.4 reports zipf")
    parser.add_argument("--num-trials", type=int, default=100)
    parser.add_argument("--rho-threshold", type=float, default=0.95,
                        help="Threshold for N*, fixed before looking at results")
    parser.add_argument("--out-dir", default="../data/sweep/analysis")
    parser.add_argument("--tpcds-only", action="store_true",
                        help="Sweep over a TPC-DS-only run (R2D7 Spark capture)")
    parser.add_argument("--figure-tables", default=None,
                        help="Comma-separated tables the figures show. Default: the "
                             "pre-revision set, or the revision set under --tpcds-only")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    tables, col_to_tbl = load_schema(args.static_dir, args.schema_dir, args.tpcds_only)
    if args.figure_tables:
        FIGURE_TABLES = args.figure_tables.split(",")
    elif args.tpcds_only:
        FIGURE_TABLES = FIGURE_TABLES_TPCDS

    # discover sweep points
    points = []
    for name in sorted(os.listdir(args.data_root)):
        mpath = os.path.join(args.data_root, name, "manifest.json")
        if os.path.exists(mpath):
            m = json.load(open(mpath))
            points.append((m["num_samples"], m["seed"], os.path.join(args.data_root, name), m))
    points.sort()
    if not points:
        raise SystemExit(f"no sweep points found under {args.data_root}")
    print(f"Found {len(points)} sweep points: "
          + ", ".join(f"N={n}/s={s}" for n, s, _, _ in points))

    # ---- load every point
    per_point = {}
    summary_rows = []
    for n, seed, ddir, manifest in points:
        shares = series_shares(ddir, args.distro, tables, col_to_tbl, args.num_trials)
        freq_raw, freq_norm = frequency_shares(ddir, tables)
        per_point[(n, seed)] = (shares, freq_raw, freq_norm, manifest)

        for series, acc in shares.items():
            for t in tables:
                v = np.asarray(acc[t], dtype=float)
                summary_rows.append({
                    "N": n, "seed": seed, "distro": args.distro, "series": series,
                    "table": t, "mean_share": v.mean(), "std_share": v.std(ddof=1),
                    "p25": np.percentile(v, 25), "median": np.percentile(v, 50),
                    "p75": np.percentile(v, 75),
                    "iqr": np.percentile(v, 75) - np.percentile(v, 25),
                    "ci95_halfwidth": ci_halfwidth(v),
                    "in_figure": t in FIGURE_TABLES,
                })
        for t in tables:
            summary_rows.append({
                "N": n, "seed": seed, "distro": args.distro, "series": "frequency",
                "table": t, "mean_share": freq_norm[t], "std_share": 0.0,
                "p25": freq_norm[t], "median": freq_norm[t], "p75": freq_norm[t],
                "iqr": 0.0, "ci95_halfwidth": 0.0, "in_figure": t in FIGURE_TABLES,
            })

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(os.path.join(args.out_dir, "sweep_summary.csv"), index=False)

    # ---- Layer 2: rank stability vs the largest N, per seed
    seeds = sorted({s for _, s, _, _ in points})
    all_series = ["fig3_full", "fig3_equal", "fig3_cardinality",
                  "fig4_table", "fig4_column", "fig4_rowgroup", "frequency"]
    rank_rows = []
    for seed in seeds:
        ns = sorted(n for n, s, _, _ in points if s == seed)
        ref_n = ns[-1]
        for series in all_series:
            ref = summary[(summary.seed == seed) & (summary.N == ref_n)
                          & (summary.series == series)].set_index("table")["mean_share"]
            for n in ns:
                cur = summary[(summary.seed == seed) & (summary.N == n)
                              & (summary.series == series)].set_index("table")["mean_share"]
                for scope, subset in [("all_tables", tables), ("figure_tables", FIGURE_TABLES)]:
                    a = ref.reindex(subset).values
                    b = cur.reindex(subset).values
                    rho = stats.spearmanr(a, b).statistic
                    tau = stats.kendalltau(a, b).statistic
                    top3 = len(set(ref.reindex(subset).nlargest(3).index)
                               & set(cur.reindex(subset).nlargest(3).index)) / 3
                    top5 = len(set(ref.reindex(subset).nlargest(5).index)
                               & set(cur.reindex(subset).nlargest(5).index)) / 5
                    rank_rows.append({
                        "N": n, "seed": seed, "distro": args.distro, "series": series,
                        "scope": scope, "reference_N": ref_n,
                        "spearman": rho, "kendall": tau,
                        "top3_overlap": top3, "top5_overlap": top5,
                    })
    ranks = pd.DataFrame(rank_rows)
    ranks.to_csv(os.path.join(args.out_dir, "rank_stability.csv"), index=False)

    # ---- N*: smallest N where every VDI series clears the threshold
    vdi_series = [s for s in all_series if s != "frequency"]
    print(f"\n=== Rank stability vs largest N (Spearman rho, {args.distro}) ===")
    for scope in ["all_tables", "figure_tables"]:
        sub = ranks[(ranks.scope == scope) & (ranks.series.isin(vdi_series))]
        piv = sub.pivot_table(index="N", columns="series", values="spearman")
        print(f"\n-- {scope} --")
        print(piv.round(4).to_string())
        worst = piv.min(axis=1)
        ok = worst[worst >= args.rho_threshold]
        nstar = int(ok.index.min()) if len(ok) else None
        print(f"min across series: {worst.round(4).to_dict()}")
        print(f"N* (rho >= {args.rho_threshold} for all series): {nstar}")

    # ---- Layer 3: the claims Sec 4.4 makes in prose
    claim_rows = []
    for (n, seed), (shares, freq_raw, freq_norm, manifest) in sorted(per_point.items()):
        dd_full = np.mean(shares["fig3_full"]["date_dim"])
        dd_equal = np.mean(shares["fig3_equal"]["date_dim"])
        dd_freq_access = freq_raw.get("date_dim", 0.0)
        dd_freq_share = freq_norm["date_dim"]
        card_top = max(tables, key=lambda t: np.mean(shares["fig3_cardinality"][t]))

        def gran(t, g):
            return np.mean(shares[f"fig4_{g}"][t])

        claim_rows.append({
            "N": n, "seed": seed, "distro": args.distro,
            "distinct_queries_drawn": manifest["distinct_queries_drawn"],
            # "date_dim ... receives only 15-18% of value under Full or Equal"
            "date_dim_share_full": dd_full,
            "date_dim_share_equal": dd_equal,
            "claim_date_dim_15_to_18pct": bool(0.15 <= dd_full <= 0.18 and 0.15 <= dd_equal <= 0.18),
            # "date_dim is accessed by 60% of queries"
            "date_dim_access_fraction": dd_freq_access,
            "date_dim_frequency_share": dd_freq_share,
            # "a frequency-based approach would thus overvalue date_dim".
            # Figure 3 draws the red line from the RAW access fraction
            # (collect_boris_data is called with normalized=False there), which
            # is the quantity the prose compares against the 15-18% value share.
            # Figure 4 instead plots the NORMALIZED frequency share, so the two
            # figures treat the baseline differently -- tracked separately below.
            "claim_frequency_overvalues_date_dim": bool(dd_freq_access > dd_full and dd_freq_access > dd_equal),
            "freq_share_exceeds_vdi_share": bool(dd_freq_share > dd_full and dd_freq_share > dd_equal),
            # "Cardinality assigns greater values to larger tables, like store_sales"
            "cardinality_top_table": card_top,
            "claim_cardinality_top_is_store_sales": bool(card_top == "store_sales"),
            # Fig 4: "In store and date_dim, Column value is lower than Table,
            #         and Row Group lower still"
            "claim_store_col_lt_tbl": bool(gran("store", "column") < gran("store", "table")),
            "claim_store_rg_lt_col": bool(gran("store", "rowgroup") < gran("store", "column")),
            "claim_datedim_col_lt_tbl": bool(gran("date_dim", "column") < gran("date_dim", "table")),
            "claim_datedim_rg_lt_col": bool(gran("date_dim", "rowgroup") < gran("date_dim", "column")),
            # "Conversely, in customer a subset of row groups drives the Table value,
            #  so Row Group is lower"
            "claim_customer_rg_lt_tbl": bool(gran("tpcds.customer", "rowgroup") < gran("tpcds.customer", "table")),
        })
    claims = pd.DataFrame(claim_rows)
    claims.to_csv(os.path.join(args.out_dir, "claims.csv"), index=False)

    # --- how far each headline quantity sits from its value at the largest N
    ref_n = claims.N.max()
    for col in ["date_dim_share_full", "date_dim_share_equal",
                "date_dim_access_fraction", "date_dim_frequency_share"]:
        # against the same seed's largest-N value: histories are nested per seed,
        # so this is the drift of one workload as it is observed for longer
        ref = claims[claims.N == ref_n].set_index("seed")[col]
        claims[col + "_delta_vs_ref"] = (claims[col] - claims.seed.map(ref)).abs()

    claims.to_csv(os.path.join(args.out_dir, "claims.csv"), index=False)
    print(f"\n=== Drift of the headline quantities vs N={ref_n} ===")
    delta_cols = [c for c in claims.columns if c.endswith("_delta_vs_ref")]
    print(claims[["N"] + delta_cols].round(4).to_string(index=False))
    tol = 0.005
    # smallest N from which every point (every seed, every larger N) is in the band
    worst_by_n = claims.groupby("N")[delta_cols].max().max(axis=1).sort_index()
    ok = worst_by_n <= tol
    onward = [n for n in worst_by_n.index if ok.loc[n:].all()]
    if onward:
        print(f"All headline quantities within +/-{tol} of their N={ref_n} value "
              f"from N={int(onward[0])} onward.")
    else:
        print(f"No N from which every point stays in the +/-{tol} band.")

    claim_cols = [c for c in claims.columns if c.startswith("claim_")]
    print(f"\n=== Sec 4.4 prose claims vs N ({args.distro}) ===")
    print(claims[["N", "seed", "distinct_queries_drawn", "date_dim_share_full",
                  "date_dim_share_equal", "date_dim_access_fraction",
                  "date_dim_frequency_share"]].round(4).to_string(index=False))
    print()
    print(claims[["N", "seed"] + claim_cols].to_string(index=False))

    holds_all = claims[claim_cols].all(axis=1)
    if holds_all.all():
        print(f"\nAll Sec 4.4 claims hold at every N tested ({claims.N.min()}-{claims.N.max()}).")
    else:
        bad = claims.loc[~holds_all, "N"].tolist()
        print(f"\nClaims do NOT all hold at N = {bad}")
        for c in claim_cols:
            failing = claims.loc[~claims[c], "N"].tolist()
            if failing:
                print(f"  {c}: fails at N={failing}")

    figs = [plot_rank_stability(ranks, args.out_dir, args.rho_threshold, "figure_tables"),
            plot_rank_stability(ranks, args.out_dir, args.rho_threshold, "all_tables"),
            plot_date_dim(claims, args.out_dir)]

    print(f"\nWrote sweep_summary.csv, rank_stability.csv, claims.csv to {args.out_dir}")
    for f in figs:
        print(f"  figure: {f}")
