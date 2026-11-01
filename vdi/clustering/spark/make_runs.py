"""Write the SortingRunner plan for one phase of the experiment.

  explain   EXPLAIN-only pass over all 99 queries on `base` (do this first)
  pilot     base (99 queries), a repeat of base on the pilot queries (determinism), and
            the pilot table under modes s, ps, pz
  configs   the paper's setup, measured directly: for the selected configurations (--k,
            --c), every distinct set of sorted tables is one run with all of its tables
            bound to their layouts at once, executing every query that reads at least one
            of them. Plus `nosort`, all 99 queries on `base`, and a repeat of each group
            used by --repeat-strategy (determinism of the sorted layouts). A query that
            reads none of a configuration's sorted tables is not rerun; its bytes are the
            No Sort run's. Nothing is estimated.

Run IDs: nosort, g_<layout>+<layout>..._<mode>, and <group>_rep for the repeats.
Configurations map to groups through group_id(), which analyze_sweep.py uses too.
"""
import json
import sys
from argparse import ArgumentParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from workload import P  # noqa: E402  (WORKLOAD=tpcds by default; see workload.py)

ALL_QUERIES = P["queries"]          # TPC-DS: "01".."99"
BASE_TABLES = len(json.load(open(P["row_counts_json"])))   # TPC-DS: 24


def group_id(config, mode):
    """One run per distinct set of sorted tables (layout ids), whatever the strategy."""
    return f"g_{'+'.join(sorted(config['layouts'].values()))}_{mode}"


def select_configs(m, ks, cs):
    def ok(v, allowed):
        return allowed == "all" or v in {int(x) for x in allowed.split(",")}
    return [c for c in m["configs"] if ok(c["k"], ks) and ok(c["c"], cs)]


def group_runs(m, configs, mode):
    """group id -> run (bindings: every sorted table at once; queries: those reading any)."""
    groups = {}
    for c in configs:
        gid = group_id(c, mode)
        if gid not in groups:
            qs = sorted({q for t in c["tables"] for q in m["queries_by_table"][t]})
            groups[gid] = {"run_id": gid,
                           "bindings": {t: f"{lid}_{mode}" for t, lid in c["layouts"].items()},
                           "queries": qs}
    return groups


def main():
    ap = ArgumentParser()
    ap.add_argument("phase", choices=["explain", "pilot", "configs"])
    ap.add_argument("--manifest", default=str(P["manifest"]))
    ap.add_argument("--mode", default="ps", help="layout mode")
    ap.add_argument("--k", default="2", help="configs: tables sorted, comma-separated or all")
    ap.add_argument("--c", default="2", help="configs: columns per table, comma-separated or all")
    ap.add_argument("--repeat-strategy", default="frequency",
                    help="configs: rerun this strategy's groups as <group>_rep ('' for none)")
    ap.add_argument("--print-layouts", action="store_true",
                    help="configs: print the layout ids the selection needs, comma-separated")
    ap.add_argument("--catalog", default="vdi")
    ap.add_argument("--query-dir", default=str(P["query_dir"]))
    ap.add_argument("--results", required=True, help="results directory")
    ap.add_argument("--out", required=True, help="plan json to write")
    args = ap.parse_args()

    m = json.load(open(args.manifest))
    res = Path(args.results)
    runs, explain = [], False

    if args.phase == "explain":
        explain = True
        runs.append({"run_id": "base", "bindings": {}, "queries": ALL_QUERIES})
        out = res / "explain.jsonl"
    elif args.phase == "pilot":
        p = m["pilot"]
        runs.append({"run_id": "base", "bindings": {}, "queries": ALL_QUERIES})
        runs.append({"run_id": "base_rep", "bindings": {}, "queries": p["queries"]})
        for mode in p["modes"]:
            runs.append({"run_id": f"{p['layout']}_{mode}",
                         "bindings": {p["table"]: f"{p['layout']}_{mode}"},
                         "queries": p["queries"]})
        out = res / "pilot.jsonl"
    else:
        configs = select_configs(m, args.k, args.c)
        if not configs:
            raise SystemExit(f"no configurations with k in {args.k} and c in {args.c}")
        if args.print_layouts:
            print(",".join(sorted({lid for c in configs for lid in c["layouts"].values()})))
            return
        groups = group_runs(m, configs, args.mode)
        runs.append({"run_id": "nosort", "bindings": {}, "queries": ALL_QUERIES})
        runs.extend(groups[g] for g in sorted(groups))
        rep = sorted({group_id(c, args.mode) for c in configs
                      if args.repeat_strategy and c["strategy"] == args.repeat_strategy})
        runs.extend(dict(groups[g], run_id=f"{g}_rep") for g in rep)
        out = res / f"configs_{args.mode}.jsonl"
        print(f"configs: {len(configs)} configurations -> {len(groups)} groups; "
              f"repeats: {rep}")

    plan = {"catalog": args.catalog, "query_dir": args.query_dir, "base_tables": BASE_TABLES,
            "usage_path": str(res / "usage_logs"), "out": str(out),
            "explain": explain, "runs": runs}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(plan, f, indent=2)
    n = sum(len(r["queries"]) for r in runs)
    print(f"{args.phase}: {len(runs)} runs, {n} query executions -> {args.out}")


if __name__ == "__main__":
    main()
