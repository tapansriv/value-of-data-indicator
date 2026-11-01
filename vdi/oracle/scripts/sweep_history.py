"""Sweep the query-history size N and regenerate the Sec 4.4 figures at each point.

Answers R2D8/R2D13: does the number of queries in the history change the VDI
results reported in Figures 3 (dividing strategies) and 4 (granularities)?

Task values are NOT regenerated between points. generate_oracle_vals.py draws
one value per query per trial, independent of N, so leaving those files alone
means every history size sees identical task values and any movement in the
figures is attributable to history size alone.

Histories are nested: with a fixed seed the draw for N=100 is a strict prefix of
the draw for N=2000, so smaller N is the same workload observed for less time
rather than an unrelated sample.

Each point writes to its own directory, so nothing overwrites the committed
Sec 4.4 results in ../data.
"""

import json
import os
import subprocess
import sys
import time
from argparse import ArgumentParser
from datetime import datetime, timezone

DEFAULT_N_VALUES = [100, 250, 500, 1000, 1500, 2000]
DEFAULT_SEEDS = [42]


def point_name(n, seed):
    return f"N{n}_s{seed}"


def run(cmd):
    print("  $ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + "\n" + proc.stderr + "\n")
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(cmd)}")
    return proc.stdout


if __name__ == "__main__":
    parser = ArgumentParser(description="Query-history size sweep for Sec 4.4")
    parser.add_argument("--n-values", type=int, nargs="+", default=DEFAULT_N_VALUES,
                        help="History sizes to sweep")
    parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS,
                        help="Seeds for the history draw. One seed answers the "
                             "question; more separate history size from which "
                             "particular queries landed in the prefix.")
    parser.add_argument("--num-trials", type=int, default=100,
                        help="Task-value draws per point (unchanged from Sec 4.4)")
    parser.add_argument("--distro", choices=["normal", "zipf", "both"], default="both")
    parser.add_argument("--data-root", default="../data/sweep")
    parser.add_argument("--fig-root", default="../figs/sweep")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip points whose manifest already exists")
    parser.add_argument("--no-plots", action="store_true",
                        help="Compute values only; regenerate figures later")
    # Inputs for the R2D7 Spark capture (one scale factor per sweep); forwarded
    # unchanged to assign_val_to_de.py. Defaults reproduce the Drill-based sweep.
    parser.add_argument("--logs-dir", default=None)
    parser.add_argument("--values-dir", default=None)
    parser.add_argument("--columns-in-queries", default=None)
    parser.add_argument("--cardinality", default=None)
    parser.add_argument("--query-set", default=None)
    parser.add_argument("--tpcds-only", action="store_true")
    args = parser.parse_args()

    input_args = []
    for flag in ["logs_dir", "values_dir", "columns_in_queries", "cardinality", "query_set"]:
        if getattr(args, flag) is not None:
            input_args += ["--" + flag.replace("_", "-"), getattr(args, flag)]
    if args.tpcds_only:
        input_args.append("--tpcds-only")

    os.makedirs(args.data_root, exist_ok=True)
    points = [(n, s) for s in args.seeds for n in args.n_values]

    print(f"Sweep: {len(points)} points "
          f"(N={args.n_values}, seeds={args.seeds}, distro={args.distro})")

    started = time.time()
    completed = []
    for i, (n, seed) in enumerate(points, start=1):
        name = point_name(n, seed)
        data_dir = os.path.join(args.data_root, name)
        fig_dir = os.path.join(args.fig_root, name)
        manifest = os.path.join(data_dir, "manifest.json")

        print(f"\n[{i}/{len(points)}] {name}", flush=True)
        if args.skip_existing and os.path.exists(manifest):
            print("  already present, skipping")
            completed.append(name)
            continue

        t0 = time.time()
        run([sys.executable, "assign_val_to_de.py",
             "-n", str(n), "-s", str(seed),
             "--num-trials", str(args.num_trials),
             "--distro", args.distro,
             "--out-dir", data_dir] + input_args)

        if not args.no_plots:
            run([sys.executable, "graph_comp_oracles.py",
                 "--distro", args.distro,
                 "--num-trials", str(args.num_trials),
                 "--data-dir", data_dir,
                 "--fig-dir", fig_dir] + (["--tpcds-only"] if args.tpcds_only else []))

        print(f"  done in {time.time() - t0:.1f}s")
        completed.append(name)

    sweep_manifest = {
        "n_values": args.n_values,
        "seeds": args.seeds,
        "num_trials": args.num_trials,
        "distro": args.distro,
        "points": completed,
        "inputs": input_args,
        "data_root": os.path.abspath(args.data_root),
        "fig_root": os.path.abspath(args.fig_root),
        "elapsed_seconds": round(time.time() - started, 1),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(os.path.join(args.data_root, "sweep_manifest.json"), "w") as fp:
        json.dump(sweep_manifest, fp, indent=4, sort_keys=True)

    print(f"\nSweep complete: {len(completed)} points in "
          f"{sweep_manifest['elapsed_seconds']}s -> {args.data_root}")
