"""
Placement figures for the Spark rerun, from the results 40_fetch.sh downloads.

Same computation and plot as analyze.py (percent runtime reduction of VoD vs. LRU over the
top-K queries by value, one bar per value assignment), reading
    data/spark/<run>/**/<iter>_<size>/{lru_hot_static,vod_hot_<mode>}_spark_<size>.json
Figures go to metric/spark/<run>/ so the DuckDB figures in metric/ are never overwritten.

Also prints where the time goes from the *.breakdown.json files: per run, total query
time and the share spent reading eviction order from the VDI tables via Spark SQL.

    python3 analyze_spark.py --run sweep1
    python3 analyze_spark.py --run smoke --data-root ../run/results/spark --flat   (local test)
"""
import glob
import json
import os
from argparse import ArgumentParser

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import analyze  # reuse TOP_KS and VALUE_ITERS

HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = [2.75, 3.5, 5.0, 7.5, 13.75]


def find(root, flat, value_iter, size, name):
    pattern = (os.path.join(root, f"{value_iter}_{size}", name) if flat else
               os.path.join(root, "**", f"{value_iter}_{size}", name))
    hits = glob.glob(pattern, recursive=True)
    if len(hits) > 1:
        raise ValueError(f"ambiguous: {hits}")
    return hits[0] if hits else None


def analyze_size(root, flat, size, vod_mode, value_iters, lru_iter, query_value_file):
    results = {k: [] for k in analyze.TOP_KS}
    used_iters = []
    for it in value_iters:
        lru_path = find(root, flat, lru_iter if lru_iter is not None else it, size,
                        f"lru_hot_static_spark_{size}.json")
        vod_path = find(root, flat, it, size, f"vod_hot_{vod_mode}_spark_{size}.json")
        if not lru_path or not vod_path:
            print(f"  skip iter={it} size={size} {vod_mode}: missing "
                  f"{'LRU' if not lru_path else 'VoD'} result")
            continue
        lru, vod = json.load(open(lru_path)), json.load(open(vod_path))
        # As analyze.py: iter 0 has equal values, so group queries by iter 4's values.
        qv = pd.read_csv(query_value_file).set_index("query_id")["4" if it == 0 else str(it)]
        df = pd.DataFrame([{"t_lru": lru[q], "t_vod": vod[q], "value": qv[q]}
                           for q in lru if q.endswith(".sql") and q in vod])
        for k in analyze.TOP_KS:
            s = df.nlargest(k, "value")[["t_lru", "t_vod"]].sum()
            results[k].append(100 * (s["t_lru"] - s["t_vod"]) / s["t_lru"])
        used_iters.append(it)
        print(f"  iter={it} size={size} {vod_mode}: top-1 {results[1][-1]:+.1f}%, "
              f"all {results[analyze.TOP_KS[-1]][-1]:+.1f}%")
    return results, used_iters


def plot_value_def_bars(results, cache_size, vod_mode):
    """analyze.plot_value_def_bars with the paper's current styling (5.0 GB is the full-width
    figure: smaller font, legend), plotting the real points. Kept separate so the DuckDB
    script's working-copy edits never change the Spark figures."""
    colors = ["#1F63A9", "#ADDC5A", "#F8DD3D", "#FE9C22", "#E65742"]
    points = np.array(list(results.values()))  # shape (num_k, num_value_iters)
    X, Y = 8, 5.25
    if cache_size != 5.0:
        plt.rc('font', size=22)
    else:
        plt.rc('font', size=18)
        Y = 4.75

    fig, ax = plt.subplots(figsize=(X, Y))
    labels = ["Constant", "Value 50", "Value 100", "Value 500", "Value 1000"]
    x = np.arange(len(analyze.TOP_KS))
    width = 0.15
    for i, _ in enumerate(analyze.VALUE_ITERS):
        ax.bar(x + i * width, points[:, i], width, label=labels[i], color=colors[i])

    ax.set_xticks(x + width * 2)
    ax.set_yticks([-75, -50, -25, 0, 25, 50, 75, 100])
    ax.set_xticklabels(["All" if k == 99 else f"{k}" for k in analyze.TOP_KS])
    ax.set_xlabel("Number of top-value queries")
    ax.set_ylabel("% Speedup vs LRU")
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim([-80, 105])
    if cache_size in [5.0, 13.75]:
        ax.legend(ncol=2, loc="lower right")

    plt.tight_layout()
    plt.savefig(f"{vod_mode}_cache{str(cache_size).replace('.', 'p')}_value_defs.pdf",
                bbox_inches='tight')
    plt.close(fig)


def overhead_table(root):
    rows = []
    for path in sorted(glob.glob(os.path.join(root, "**", "*.breakdown.json"), recursive=True)):
        b = json.load(open(path))
        q = list(b["queries"].values())
        rows.append({
            "run": os.path.relpath(path, root).replace(".breakdown.json", ""),
            "query_s": sum(x["query_s"] for x in q),
            "fetch_evict_s": sum(x["fetch_evict_s"] for x in q),
            "vdi_lookup_s": sum(x["vdi_lookup_s"] for x in q),
            "exec_s": sum(x["exec_s"] for x in q),
            "listener_wait_s": sum(x["listener_wait_s"] for x in q),
            "s3_GiB": sum(x.get("s3_bytes_fetched", 0) for x in q) / 2**30,
            "spark_read_GiB": sum(x.get("spark_bytes_read", 0) for x in q) / 2**30,
            "evictions": b.get("evictions"),
            "xcheck_mismatch": len(b.get("crosscheck_mismatches", [])),
        })
    if rows:
        df = pd.DataFrame(rows)
        df["vdi_pct"] = 100 * df["vdi_lookup_s"] / df["query_s"]
        print(df.round(3).to_string(index=False))
    return rows


def main():
    ap = ArgumentParser()
    ap.add_argument("--run", required=True, help="run name (data/spark/<run>)")
    ap.add_argument("--data-root", default=None, help="default: ../data/spark/<run>")
    ap.add_argument("--flat", action="store_true",
                    help="data-root holds <iter>_<size>/ directly (run/results/spark)")
    ap.add_argument("--value-iters", default="0,1,2,3,4")
    ap.add_argument("--sizes", default=",".join(str(s) for s in SIZES))
    ap.add_argument("--lru-iter", default="0",
                    help="value iter whose LRU run is the baseline for all ('same' = each "
                         "iter's own). analyze.py used iter 0's.")
    ap.add_argument("--query-value-file",
                    default=os.path.join(HERE, "..", "metadata", "tpcds_query_values_custom.csv"))
    args = ap.parse_args()

    root = os.path.abspath(args.data_root or os.path.join(HERE, "..", "data", "spark", args.run))
    out_dir = os.path.join(HERE, "spark", args.run)
    os.makedirs(out_dir, exist_ok=True)
    lru_iter = None if args.lru_iter == "same" else int(args.lru_iter)
    iters = [int(x) for x in args.value_iters.split(",")]

    print(f"results: {root}\nfigures: {out_dir}")
    cwd = os.getcwd()
    os.chdir(out_dir)  # plot_value_def_bars saves into the working directory
    try:
        for size in [float(s) for s in args.sizes.split(",")]:
            for mode in ("dynamic", "static"):
                results, used = analyze_size(root, args.flat, size, mode, iters, lru_iter,
                                             args.query_value_file)
                # analyze.py's plot has one bar per value assignment, all five of them.
                if used == list(analyze.VALUE_ITERS):
                    plot_value_def_bars(results, size, mode)
                elif used:
                    print(f"  not plotting size={size} {mode}: needs iters "
                          f"{analyze.VALUE_ITERS}, have {used}")
    finally:
        os.chdir(cwd)
    print("\nTime breakdown (seconds, summed over the timed queries):")
    overhead_table(root)


if __name__ == "__main__":
    main()
