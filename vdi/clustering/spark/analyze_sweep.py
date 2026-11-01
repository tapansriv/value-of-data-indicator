"""Analyze the sorting experiment's results (run via `run_phase.sh analyze`).

Sections run when their inputs exist:
  pilot      pilot.jsonl -> per-arm totals for every bytes measure, DPP firing, base vs
             base_rep determinism (the pilot decided ps and the metrics).
  configs    configs_<mode>.jsonl -> utility of every configuration whose group was run,
             from measured bytes only: a query reading one of the configuration's sorted
             tables takes its bytes from the group's run (all of the configuration's tables
             sorted at once); any other query takes the No Sort run's bytes. Nothing is
             estimated; a configuration with a missing or failed measurement gets no number.
             Also: <group>_rep vs <group> determinism, and per (k, c) the paper's
             profiles_combined_<value_iter>.csv (clustering/src/analyze.py's format).
  listener   usage_logs/ -> listener-logged columns vs the SQL-parsed column sets used for
             ranking (they should agree; any difference is reported, not fixed).

Utility is the paper's metric: sum over queries of value(q) * nosort(q) / sorted(q), with
No Sort = sum of value(q). Writes CSVs to results/analysis/ and prints summaries.
"""
import csv
import json
import sys
from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
from workload import P  # noqa: E402  (WORKLOAD=tpcds by default; see workload.py)

VALUES_CSV = P["values_csv"]
COLUMNS_IN_QUERIES = P["columns_in_queries"]
N_QUERIES = len(P["queries"])   # TPC-DS: 99
# task_records_read: rows Spark read from the input. Rows in files and row groups that were
# skipped are never read, so base - layout is the number of rows pruned (Tapan, 2026-10-07:
# tracked alongside task_bytes_read, which also carries the compression change).
METRICS = ["task_bytes_read", "task_records_read", "proc_rchar"]


def load(path):
    """run_id -> query -> latest ok record."""
    out = defaultdict(dict)
    errors = []
    if not path.exists():
        return None, errors
    for line in open(path):
        r = json.loads(line)
        if r["status"] == "ok":
            out[r["run_id"]][r["query"]] = r
        else:
            errors.append((r["run_id"], r["query"], r.get("error", "")[:200]))
    errors = [e for e in errors if e[1] not in out.get(e[0], {})]
    return out, errors


def metric(rec, name):
    if name.startswith("scan:"):
        key = name[5:]
        return sum(s["metrics"].get(key, 0) for s in rec["scans"])
    return rec[name]


def scan_metric_names(runs):
    names = set()
    for qs in runs.values():
        for r in qs.values():
            for s in r.get("scans", []):
                names.update(s["metrics"])
    return sorted(names)


def write_csv(path, rows, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {path}")


def pct(a, b):
    return 100.0 * (a - b) / b if b else float("nan")


def pilot(res, out_dir, m):
    runs, errors = load(res / "pilot.jsonl")
    if runs is None:
        return
    p = m["pilot"]
    qs = p["queries"]
    arms = ["base", "base_rep"] + [f"{p['layout']}_{mode}" for mode in p["modes"]]
    names = METRICS + [f"scan:{n}" for n in scan_metric_names(runs)]
    print(f"\n== PILOT: {p['table']} {p['sort_cols']} ({len(qs)} queries)")
    if errors:
        print(f"  {len(errors)} unresolved errors: {errors[:5]}")
    rows = []
    for arm in arms:
        have = [q for q in qs if q in runs.get(arm, {})]
        dpp = sum(runs[arm][q]["dpp_in_plan"] for q in have)
        for n in names:
            tot = sum(metric(runs[arm][q], n) for q in have)
            base_tot = sum(metric(runs["base"][q], n) for q in have if q in runs.get("base", {}))
            rows.append([arm, n, len(have), dpp, tot, round(pct(tot, base_tot), 2)])
    write_csv(out_dir / "pilot_totals.csv", rows,
              ["arm", "metric", "queries", "dpp_queries", "total", "pct_vs_base"])
    for arm in arms:
        line = [f"{r[1]}={r[5]:+.1f}%" for r in rows if r[0] == arm and r[1] in METRICS]
        dpp = next((r[3] for r in rows if r[0] == arm), 0)
        print(f"  {arm:12s} dpp in {dpp}/{len(qs)} queries; " + ", ".join(line))

    # Determinism: base vs base_rep, per query.
    det = []
    for q in qs:
        if q in runs.get("base", {}) and q in runs.get("base_rep", {}):
            det.append([q] + [round(pct(metric(runs["base_rep"][q], n),
                                        metric(runs["base"][q], n)), 4) for n in METRICS])
    write_csv(out_dir / "pilot_determinism.csv", det, ["query"] + METRICS)
    for i, n in enumerate(METRICS):
        worst = max((abs(d[i + 1]) for d in det if d[i + 1] == d[i + 1]), default=float("nan"))
        print(f"  determinism {n}: max |base_rep - base| = {worst:.4f}%")

    per_q = [[q, arm] + [metric(runs[arm][q], n) for n in METRICS] + [runs[arm][q]["dpp_in_plan"]]
             for q in qs for arm in arms if q in runs.get(arm, {})]
    write_csv(out_dir / "pilot_per_query.csv", per_q, ["query", "arm"] + METRICS + ["dpp"])


def query_values():
    vals = {}
    for row in csv.DictReader(open(VALUES_CSV)):
        vals[row["query_id"].split(".")[0]] = {k: float(row[k]) for k in P["value_iters"]}
    return vals


def execution_weights(weighting):
    """Per-query weight in the utility. "distinct": every query counts once (the published
    TPC-DS analysis). "executions": net utility -- each query counts as many times as it ran
    in the trace (Tapan, 2026-10-07, for the Redbench IMDb workload); No Sort is weighted the
    same way, so normalizing to No Sort stays meaningful."""
    if weighting == "distinct":
        return lambda q: 1.0
    path = P["query_executions"]
    assert path, "--weighting executions needs query_executions in the workload profile"
    ex = {k.split(".")[0]: float(v) for k, v in json.load(open(path)).items()}
    return lambda q: ex.get(q, 0.0)


def configs_report(res, out_dir, m, mode, names, weighting="distinct"):
    from make_runs import group_id
    runs, errors = load(res / f"configs_{mode}.jsonl")
    if runs is None:
        return
    print(f"\n== CONFIGS (mode {mode}): measured directly")
    if errors:
        print(f"  {len(errors)} unresolved errors (run, query): {errors[:10]}")
    nosort = runs.get("nosort", {})
    if len(nosort) < N_QUERIES:
        print(f"  No Sort run incomplete: {len(nosort)}/{N_QUERIES} queries ok; no utilities computed")
        return
    vals = query_values()
    w = execution_weights(weighting)
    names_v = {c["value_iter"]: c["value_name"] for c in m["configs"]}

    # Determinism of the sorted layouts: every <group>_rep against its group.
    for rid in sorted(r for r in runs if r.endswith("_rep")):
        g = runs.get(rid[:-4], {})
        common = sorted(set(g) & set(runs[rid]))
        for n in names:
            diffs = [(q, metric(runs[rid][q], n) - metric(g[q], n)) for q in common]
            nz = [d for d in diffs if d[1] != 0]
            print(f"  determinism {rid[:-4]} ({len(common)} queries) {n}: "
                  f"{len(nz)} differ" + (f", e.g. {nz[:5]}" if nz else " (identical)"))

    complete, incomplete = [], []
    for c in m["configs"]:
        gid = group_id(c, mode)
        if gid not in runs:
            continue
        need = sorted({q for t in c["tables"] for q in m["queries_by_table"][t]})
        missing = [q for q in need if q not in runs[gid]]
        (incomplete if missing else complete).append((c, gid, need, missing))
    for c, gid, _, missing in incomplete:
        print(f"  {c['id']}: {len(missing)} queries not measured in {gid} {missing[:8]}; skipped")
    if not complete:
        return

    def query_rows(c, gid, need, n):
        """q -> (sorted measurement, nosort measurement, measured in the group run?)"""
        g = runs[gid]
        return {q: (metric(g[q], n) if q in need else metric(nosort[q], n),
                    metric(nosort[q], n), q in need) for q in nosort}

    for n in names:
        rows, util = [], {}
        for c, gid, need, _ in complete:
            qr = query_rows(c, gid, need, n)
            v = vals_for(vals, c["value_iter"])
            u = sum(w(q) * v[q] * ns / sb for q, (sb, ns, _) in qr.items() if sb > 0)
            zero = [q for q, (sb, _, _) in qr.items() if sb <= 0]
            util[c["id"]] = u
            rows.append([c["id"], c["value_name"], c["strategy"], c["k"], c["c"], gid,
                         ";".join(f"{t}:{'+'.join(cs)}" for t, cs in c["tables"].items()),
                         len(need), round(u, 4), round(sum(w(q) * x for q, x in v.items()), 4),
                         sum(x[0] for x in qr.values()), sum(x[1] for x in qr.values()),
                         ",".join(zero)])
        tag = n.replace(":", "_")
        write_csv(out_dir / f"configs_{mode}_{tag}.csv", rows,
                  ["config", "value_name", "strategy", "k", "c", "group", "tables",
                   "queries_measured", "utility", "utility_nosort", "sorted_total",
                   "nosort_total", "queries_with_zero_measure"])
        # Summary per (k, c): VOD / Frequent / Random / No Sort per value assignment.
        kcs = sorted({(c["k"], c["c"]) for c, *_ in complete})
        for k, cc in kcs:
            print(f"  [{n}] k={k}, c={cc}: utility (No Sort = sum of values)")
            print(f"    {'assignment':11s} {'VOD':>10s} {'Frequent':>10s} {'Random':>10s} "
                  f"{'No Sort':>10s} {'VOD/Freq':>9s} {'VOD/Rand':>9s}")
            for vi in m["params"]["value_iters"]:
                ids = {s: f"v{vi}_{s}_k{k}_c{cc}" for s in ("value", "frequency", "random")}
                if not all(i in util for i in ids.values()):
                    continue
                u = {s: util[i] for s, i in ids.items()}
                ns = sum(w(q) * x for q, x in vals_for(vals, vi).items())
                print(f"    {names_v[vi]:11s} {u['value']:10.3f} {u['frequency']:10.3f} "
                      f"{u['random']:10.3f} {ns:10.3f} {pct(u['value'], u['frequency']):+8.2f}% "
                      f"{pct(u['value'], u['random']):+8.2f}%")

    # The paper's per-value-assignment CSVs (clustering/src/analyze.py's format), one
    # directory per (k, c) where all three strategies are complete for every assignment.
    byid = {c["id"]: (c, gid, need) for c, gid, need, _ in complete}
    for k, cc in sorted({(c["k"], c["c"]) for c, *_ in complete}):
        ids = [f"v{vi}_{s}_k{k}_c{cc}" for vi in m["params"]["value_iters"]
               for s in ("value", "frequency", "random")]
        if not all(i in byid for i in ids):
            continue
        d = out_dir / f"paper_{mode}_k{k}_c{cc}"
        for vi in m["params"]["value_iters"]:
            v = vals_for(vals, vi)
            cols = {}
            for s, short in (("value", "vod"), ("frequency", "freq"), ("random", "random")):
                c, gid, need = byid[f"v{vi}_{s}_k{k}_c{cc}"]
                for n, pre in (("task_bytes_read", "bytes"), ("task_records_read", "rows"),
                               ("runtime_ms", "t")):
                    cols[f"{pre}_{short}"] = {q: r[0] for q, r in query_rows(c, gid, need, n).items()}
                cols[f"measured_{short}"] = {q: q in need for q in nosort}
            rows = []
            for q in sorted(nosort):
                rows.append([f"{q}.sql"]
                            + [cols[f"{pre}_{short}"][q] for short in ("vod", "freq", "random")
                               for pre in ("bytes", "t", "rows")]
                            + [metric(nosort[q], "task_bytes_read"), metric(nosort[q], "runtime_ms"),
                               metric(nosort[q], "task_records_read"), v[q]]
                            + [cols[f"measured_{short}"][q] for short in ("vod", "freq", "random")])
            header = ["query_id", "bytes_vod", "t_vod", "rows_vod", "bytes_freq", "t_freq",
                      "rows_freq", "bytes_random", "t_random", "rows_random", "bytes_plain",
                      "t_plain", "rows_plain", "value", "measured_vod", "measured_freq",
                      "measured_random"]
            if weighting == "executions":
                # net utility: a consumer must weight each row by executions; TPC-DS
                # (distinct) output keeps the original columns exactly.
                rows = [r + [w(r[0].split(".")[0])] for r in rows]
                header = header + ["executions"]
            write_csv(d / f"profiles_combined_{vi}.csv", rows, header)


def vals_for(vals, value_iter):
    return {q: vals[q][value_iter] for q in vals}


def listener(res, out_dir):
    path = res / "usage_logs"
    if not path.exists():
        return
    try:
        import pyarrow.dataset as ds
    except ImportError:
        print("\n== LISTENER: pyarrow not installed; skipped")
        return
    t = ds.dataset(str(path), format="parquet").to_table(
        columns=["tableName", "columnName", "dataTaskId"]).to_pylist()
    logged = defaultdict(set)
    for r in t:
        q = r["dataTaskId"].split("_", 1)[1].rsplit(":", 1)[1]
        logged[q].add((r["tableName"], r["columnName"]))
    static = {k.split(".")[0]: {(tb, c) for tb, cs in v.items() for c in cs}
              for k, v in json.load(open(COLUMNS_IN_QUERIES)).items()}
    rows = []
    for q in sorted(static):
        if q in logged and logged[q] != static[q]:
            rows.append([q, sorted(static[q] - logged[q]), sorted(logged[q] - static[q])])
    print(f"\n== LISTENER: {len(logged)} queries logged; {len(rows)} differ from the SQL-parsed sets")
    write_csv(out_dir / "listener_vs_static.csv", rows, ["query", "static_only", "listener_only"])


def main():
    ap = ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--mode", default="ps")
    ap.add_argument("--metric", default="task_bytes_read,task_records_read",
                    help="comma-separated: task_bytes_read | task_records_read | proc_rchar | "
                         "scan:<Iceberg/Spark scan metric>")
    ap.add_argument("--weighting", choices=["distinct", "executions"], default=P["weighting"],
                    help="utility per distinct query, or net utility weighted by executions "
                         "(default from the workload: tpcds distinct, imdb executions)")
    args = ap.parse_args()
    m = json.load(open(args.manifest))
    res = Path(args.results)
    out_dir = res / "analysis"
    pilot(res, out_dir, m)
    configs_report(res, out_dir, m, args.mode, args.metric.split(","), args.weighting)
    listener(res, out_dir)


if __name__ == "__main__":
    main()
