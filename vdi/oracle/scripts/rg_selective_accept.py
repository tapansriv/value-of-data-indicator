'''
Acceptance table for the row-group-selective queries 132-163 (REVISION_R2D7_RG128K.md §5.3).

Reads a RowGroupCapture output dir (queries.csv + rg/<N>.csv) and the calibration JSON from
author_rg_selective.py, and reports per authored query: rows returned, row groups of the target
table read / total (from the footer), the base query's reads of the same table, and the checks:
  ok_rows       rows returned >= 1
  ok_prune      target RGs read < base query's target RGs read
  ok_monotone   within a template, level k reads >= level k-1 (and the levels are not all equal)

  rg_selective_accept.py --capture-dir $R/sf30/capture --parquet-dir /mnt/tpcds/parquet_rg128k/sf30 \
      --calib $R/sf30/rg_selective_calibration.json --out $R/sf30/rg_selective_acceptance.json
'''

import csv
import json
import os
import sys
from argparse import ArgumentParser
from collections import defaultdict

import pyarrow.parquet as pq

csv.field_size_limit(sys.maxsize)


def latest_status(capture_dir):
    latest = {}
    with open(os.path.join(capture_dir, "queries.csv")) as fp:
        for row in csv.DictReader(fp):
            latest[(int(row["query"]), int(row["stmt"]))] = row
    out = defaultdict(list)
    for (q, _), row in sorted(latest.items()):
        out[q].append(row)
    return out


def rgs_read(capture_dir, q):
    '''table -> set of row-group start offsets read by query q.'''
    path = os.path.join(capture_dir, "rg", f"{q}.csv")
    per = defaultdict(set)
    if not os.path.exists(path):
        return None
    with open(path) as fp:
        for row in csv.DictReader(fp):
            t = os.path.basename(row["file"]).replace(".parquet", "")
            per[t].add(int(row["row_index_offset"]))
    return per


def main():
    ap = ArgumentParser()
    ap.add_argument("--capture-dir", required=True)
    ap.add_argument("--parquet-dir", required=True)
    ap.add_argument("--calib", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cal = json.load(open(a.calib))["queries"]
    st = latest_status(a.capture_dir)
    totals = {}
    res = []
    for c in cal:
        q, b, t = c["query"], c["base"], c["table"]
        if t not in totals:
            totals[t] = pq.ParquetFile(os.path.join(a.parquet_dir, f"{t}.parquet")).metadata.num_row_groups
        rows = [r for r in st.get(q, [])]
        status = ",".join(r["status"] for r in rows) or "missing"
        returned = sum(int(r["rows_returned"]) for r in rows) if rows and all(r["status"] == "ok" for r in rows) else None
        rd = rgs_read(a.capture_dir, q)
        bd = rgs_read(a.capture_dir, b)
        n = len(rd.get(t, ())) if rd is not None else None
        nb = len(bd.get(t, ())) if bd is not None else None
        res.append({"query": q, "template": c["template"], "level": c["level"], "base": b,
                    "table": t, "predicate": c["predicate"], "status": status,
                    "rows_returned": returned, "rgs_read": n, "total_rgs": totals[t],
                    "frac_read": round(n / totals[t], 4) if n is not None else None,
                    "base_rgs_read": nb, "predicted_rgs": c.get("predicted_rgs"),
                    "ok_rows": returned is not None and returned >= 1,
                    "ok_prune": n is not None and nb is not None and n < nb})
    by_t = defaultdict(list)
    for r in res:
        by_t[r["template"]].append(r)
    for t, rs in by_t.items():
        rs.sort(key=lambda r: r["level"])
        reads = [r["rgs_read"] for r in rs]
        mono = all(x is not None for x in reads) and all(x <= y for x, y in zip(reads, reads[1:])) \
            and len(set(reads)) > 1
        for r in rs:
            r["ok_monotone"] = mono
    for r in res:
        r["accepted"] = r["ok_rows"] and r["ok_prune"] and r["ok_monotone"]
        print(f"q{r['query']} {r['template']}{r['level']} base q{r['base']:<3d} {r['table']:22s} "
              f"{r['status']:4s} rows={r['rows_returned']} rg={r['rgs_read']}/{r['total_rgs']} "
              f"(pred {r['predicted_rgs']}, base {r['base_rgs_read']}) "
              f"{'ACCEPT' if r['accepted'] else 'REJECT ' + ','.join(k for k in ('ok_rows', 'ok_prune', 'ok_monotone') if not r[k])}")
    json.dump(res, open(a.out, "w"), indent=1)
    bad = [r["query"] for r in res if not r["accepted"]]
    print(f"{len(res) - len(bad)}/{len(res)} accepted; rejected: {bad}")


if __name__ == "__main__":
    main()
