#!/usr/bin/env python3
"""Budget and wall-clock model for the Spark scale-up runs (R2D16).

See REVISION_SCALEUP.md section 5 for the reasoning behind every parameter.

The model scales a measured reference -- the wall time of one full TPC-H SF1000
pass of one listener variant on the 4-node Chameleon cluster (branch `cluster`) --
to EC2 nodes:

    node-hours per pass  H = ref_pass_hours * ref_nodes * k
    wall time at N nodes   = passes * H / N          (ideal scaling)
    cost                   = (worker node-hours + one driver node for the wall time) * price

k is the throughput of one reference node divided by one EC2 node. It is unknown
until measured (Phase E calibration); pass the measured value with --k.

Ideal scaling is optimistic at large N. Reruns, data staging and the AMI build are
not modelled -- that is what --contingency is for.

Usage:
    python budget_model.py                        # working plan, k in {1, 1.5, 2}
    python budget_model.py --k 1.3                # after k has been measured
    python budget_model.py --nodes 1 4 8 16       # include the optional N=1 point
    python budget_model.py --derive               # recompute the reference numbers
                                                  # from legacy_results/cluster/ before modelling
"""

import argparse
import csv
import io
import statistics
from collections import defaultdict
from pathlib import Path

# r7g.2xlarge (8 vCPU Graviton3, 64 GiB) on-demand, us-east-2, published list price.
# Not fetched live: the `tapan` IAM user lacks pricing:GetProducts. Re-check before spending.
DEFAULT_PRICE = 0.4284

# Reference measurements from the `cluster` branch, archived 2026-09-27 under
# legacy_results/cluster/: spark_internal_listener_*_results.csv,
# TPC-H rows only, mean of the 2 reps per query, summed over queries. The six variants
# agree to within ~1%, so one number per query set is used. Regenerate with --derive.
REF_NODES = 4
REF_PASS_HOURS = {22: 5.64, 37: 7.62}

VARIANTS = ["vanilla", "bare", "cols", "rowgroup"]
RESULTS = "legacy_results/cluster/spark-lineage-api/benchmarking/spark_internal_listener_{}_results.csv"


def _load_cluster_tpch(variant):
    """Per-query runtimes (ms) for one variant from the archived 4-node run, TPC-H only."""
    repo = Path(__file__).resolve().parents[3]
    raw = (repo / RESULTS.format(variant)).read_text()
    rows = list(csv.reader(io.StringIO(raw)))
    header = [h.strip() for h in rows[0]]
    runtimes = defaultdict(list)
    for row in rows[1:]:
        # Some committed files have mixed-width rows (see benchmarking/data/MANIFEST.md);
        # skip them rather than let the columns shift.
        if len(row) != len(header):
            continue
        rec = dict(zip(header, row))
        if rec.get("dataset", "").strip() != "tpch":
            continue
        try:
            ms = float(rec["runtime"])
        except (KeyError, ValueError):
            continue
        if ms > 0:
            runtimes[rec["query"].strip()].append(ms)
    return runtimes


def _is_standard(query):
    stem = query.removesuffix(".sql")
    return stem.isdigit() and 1 <= int(stem) <= 22


def derive_reference():
    """Recompute per-pass hours and rep-to-rep noise from origin/cluster."""
    per_pass = {22: [], 37: []}
    print("Reference, derived from legacy_results/cluster/ (4 nodes, TPC-H SF1000, 2 reps):")
    totals = {}
    for variant in VARIANTS:
        q = _load_cluster_tpch(variant)
        std = [k for k in q if _is_standard(k)]
        per_pass[22].append(sum(statistics.mean(q[k]) for k in std) / 3.6e6)
        per_pass[37].append(sum(statistics.mean(v) for v in q.values()) / 3.6e6)
        rel = [abs(q[k][0] - q[k][1]) / statistics.mean(q[k][:2]) for k in std if len(q[k]) >= 2]
        rep1, rep2 = sum(q[k][0] for k in std), sum(q[k][1] for k in std)
        totals[variant] = (rep1 + rep2) / 2
        print(f"  {variant:9s} pass (q1-22) {per_pass[22][-1]:5.2f} h | "
              f"rep noise per query: median {100 * statistics.median(rel):4.1f}%, "
              f"max {100 * max(rel):4.1f}% | pass total {100 * abs(rep1 - rep2) / totals[variant]:4.1f}%")
    print("  overhead vs vanilla (q1-22): " + ", ".join(
        f"{v} {100 * (totals[v] / totals['vanilla'] - 1):+.1f}%" for v in VARIANTS[1:]))
    ref = {n: statistics.mean(v) for n, v in per_pass.items()}
    print(f"  => REF_PASS_HOURS = {{22: {ref[22]:.2f}, 37: {ref[37]:.2f}}}\n")
    return ref


def model(ref_hours, k, configs, reps, nodes, price):
    node_hours_per_pass = ref_hours * REF_NODES * k
    passes = configs * reps
    wall = {n: passes * node_hours_per_pass / n for n in nodes}
    worker_node_hours = passes * node_hours_per_pass * len(nodes)
    driver_node_hours = sum(wall.values())  # one driver node per cluster size
    return wall, (worker_node_hours + driver_node_hours) * price


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--k", type=float, nargs="+", default=[1.0, 1.5, 2.0])
    ap.add_argument("--queries", type=int, choices=[22, 37], default=22)
    ap.add_argument("--configs", type=int, default=4, help="listener configurations (4 = vanilla, bare, cols, rowgroup)")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--nodes", type=int, nargs="+", default=[4, 8, 16])
    ap.add_argument("--price", type=float, default=DEFAULT_PRICE, help="USD per node-hour")
    ap.add_argument("--contingency", type=float, default=0.25, help="fraction added for reruns, staging, AMI build")
    ap.add_argument("--derive", action="store_true", help="recompute the reference from legacy_results/cluster/ first")
    args = ap.parse_args()

    ref = derive_reference() if args.derive else REF_PASS_HOURS
    ref_hours = ref[args.queries]

    print(f"{args.queries} queries x {args.configs} configs x {args.reps} reps, nodes {args.nodes}, "
          f"${args.price}/node-hr, ref pass {ref_hours:.2f} h on {REF_NODES} ref nodes")
    print("Sizes run in parallel, so calendar time is the longest single size.\n")
    for k in args.k:
        wall, cost = model(ref_hours, k, args.configs, args.reps, args.nodes, args.price)
        sizes = "  ".join(f"N{n}={wall[n] / 24:4.1f}d" for n in args.nodes)
        print(f"  k={k:<4g} {sizes}  | longest {max(wall.values()) / 24:4.1f}d | "
              f"${cost:,.0f} (${cost * (1 + args.contingency):,.0f} with {args.contingency:.0%} contingency)")


if __name__ == "__main__":
    main()
