'''
Row-group pruning per query and table, first R2D7 run (128 MiB row groups) vs the rg128k rerun
(128,000-row row groups). Feeds CHECKPOINT_SF<N>.md / RESULTS_NOTE.md (REVISION_R2D7_RG128K.md §7).

For each captured query and each table it read: row groups read / row groups in the file.
"Prunes" = reads fewer than all of that table's row groups.

  rg128k_checkpoint.py --sf 30 --old-results /mnt/tpcds/results --new-results /mnt/tpcds/results_rg128k \
      --old-parquet /mnt/tpcds/parquet --new-parquet /mnt/tpcds/parquet_rg128k --out $R/sf30/pruning.json
'''

import csv
import glob
import json
import os
import sys
from argparse import ArgumentParser
from collections import defaultdict

import pyarrow.parquet as pq

csv.field_size_limit(sys.maxsize)


def totals(parquet_dir):
    return {os.path.basename(p)[:-8]: pq.ParquetFile(p).metadata.num_row_groups
            for p in glob.glob(os.path.join(parquet_dir, "*.parquet"))}


def latest_ok(capture_dir):
    latest = {}
    with open(os.path.join(capture_dir, "queries.csv")) as fp:
        for row in csv.DictReader(fp):
            latest[(int(row["query"]), int(row["stmt"]))] = row
    by_q = defaultdict(list)
    for (q, _), r in latest.items():
        by_q[q].append(r)
    return {q: rs for q, rs in by_q.items()
            if all(r["status"] == "ok" for r in rs)
            and os.path.exists(os.path.join(capture_dir, "rg", f"{q}.done"))}


def reads(capture_dir, q):
    per = defaultdict(set)
    with open(os.path.join(capture_dir, "rg", f"{q}.csv")) as fp:
        for row in csv.DictReader(fp):
            per[os.path.basename(row["file"])[:-8]].add(int(row["row_index_offset"]))
    return {t: len(s) for t, s in per.items()}


def main():
    ap = ArgumentParser()
    ap.add_argument("--sf", required=True)
    ap.add_argument("--old-results", default="/mnt/tpcds/results")
    ap.add_argument("--new-results", required=True)
    ap.add_argument("--old-parquet", default="/mnt/tpcds/parquet")
    ap.add_argument("--new-parquet", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    oc = os.path.join(a.old_results, f"sf{a.sf}", "capture")
    nc = os.path.join(a.new_results, f"sf{a.sf}", "capture")
    ot, nt = totals(os.path.join(a.old_parquet, f"sf{a.sf}")), totals(os.path.join(a.new_parquet, f"sf{a.sf}"))
    oq, nq = latest_ok(oc), latest_ok(nc)
    out = {"sf": int(a.sf), "old_total_rgs": ot, "new_total_rgs": nt, "queries": {}}
    for q in sorted(nq):
        nr = reads(nc, q)
        orr = reads(oc, q) if q in oq else None
        rows = sum(int(r["rows_returned"]) for r in nq[q])
        runtime = sum(int(r["runtime_ms"]) for r in nq[q])
        out["queries"][q] = {
            "rows_returned": rows, "runtime_ms": runtime,
            "new": {t: [n, nt[t]] for t, n in sorted(nr.items())},
            "old": {t: [n, ot[t]] for t, n in sorted(orr.items())} if orr is not None else None,
            "new_pruned_tables": sorted(t for t, n in nr.items() if n < nt[t]),
            "old_pruned_tables": sorted(t for t, n in orr.items() if n < ot[t]) if orr is not None else None,
        }
    json.dump(out, open(a.out, "w"), indent=1)
    base = [q for q in out["queries"] if q <= 99]
    newly = {q: out["queries"][q]["new_pruned_tables"] for q in base
             if set(out["queries"][q]["new_pruned_tables"]) - set(out["queries"][q]["old_pruned_tables"] or [])}
    print(f"SF{a.sf}: {len(nq)} queries captured in new run; {len(base)} of 1-99")
    print(f"queries 1-99 that prune at least one table in the new run but not (that table) in the old: {len(newly)}")
    for q, ts in newly.items():
        d = out["queries"][q]
        print(f"  q{q}: " + ", ".join(f"{t} {d['new'][t][0]}/{d['new'][t][1]} (old "
                                      f"{d['old'][t][0] if d['old'] and t in d['old'] else '-'}/{ot.get(t)})" for t in ts))


if __name__ == "__main__":
    main()
