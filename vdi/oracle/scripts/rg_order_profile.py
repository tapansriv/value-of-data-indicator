'''
Which columns follow row order? From Parquet footer statistics only (no data scan).

For every table with more than one row group and every integer/date column, each row group's
[min, max] width as a fraction of the column's full range (global max - global min). A column
written in row order has narrow per-row-group windows, so a range predicate on it skips row
groups; one that spans ~100% of its range in every row group cannot prune.

String columns listed in --string-cols are profiled as the share of row groups whose
[min, max] covers the column's global [min, max] (1.0 = no row group can be skipped on an
equality filter on any value).

Usage: rg_order_profile.py --parquet-dir /mnt/tpcds/parquet_rg128k/sf30 --out order_profile.csv
'''

import csv
import datetime
import glob
import os
from argparse import ArgumentParser

import numpy as np
import pyarrow.parquet as pq


def as_num(v):
    if isinstance(v, datetime.date):
        return v.toordinal()
    return v


def profile(path, string_cols):
    pf = pq.ParquetFile(path)
    md = pf.metadata
    table = os.path.basename(path)[:-len(".parquet")]
    rows = []
    if md.num_row_groups < 2:
        return rows
    for j in range(md.num_columns):
        col = md.schema.column(j)
        name = col.name
        lt = str(col.logical_type)
        is_int = col.physical_type in ("INT32", "INT64") and "Decimal" not in lt
        is_str = name in string_cols
        if not (is_int or is_str):
            continue
        mins, maxs, ok = [], [], True
        for i in range(md.num_row_groups):
            st = md.row_group(i).column(j).statistics
            if st is None or not st.has_min_max:
                ok = False
                break
            mins.append(st.min)
            maxs.append(st.max)
        if not ok:
            rows.append({"table": table, "column": name, "kind": "int" if is_int else "string",
                         "row_groups": md.num_row_groups, "note": "no min/max statistics"})
            continue
        if is_int:
            lo, hi = as_num(min(mins)), as_num(max(maxs))
            rng = hi - lo
            w = np.array([(as_num(b) - as_num(a)) / rng if rng else 0.0
                          for a, b in zip(mins, maxs)])
            rows.append({"table": table, "column": name, "kind": "date" if "Date" in lt else "int",
                         "row_groups": md.num_row_groups, "global_min": lo, "global_max": hi,
                         "median_width_frac": round(float(np.median(w)), 6),
                         "p90_width_frac": round(float(np.percentile(w, 90)), 6),
                         "max_width_frac": round(float(w.max()), 6),
                         "full_cover_share": "", "note": ""})
        else:
            lo, hi = min(mins), max(maxs)
            cover = np.mean([a == lo and b == hi for a, b in zip(mins, maxs)])
            rows.append({"table": table, "column": name, "kind": "string",
                         "row_groups": md.num_row_groups, "global_min": lo, "global_max": hi,
                         "median_width_frac": "", "p90_width_frac": "", "max_width_frac": "",
                         "full_cover_share": round(float(cover), 4), "note": ""})
    return rows


if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--parquet-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--string-cols",
                    default="cd_gender,cd_marital_status,cd_education_status,cd_credit_rating")
    a = ap.parse_args()
    sc = set(a.string_cols.split(","))
    out = []
    for p in sorted(glob.glob(os.path.join(a.parquet_dir, "*.parquet"))):
        out += profile(p, sc)
    fields = ["table", "column", "kind", "row_groups", "global_min", "global_max",
              "median_width_frac", "p90_width_frac", "max_width_frac", "full_cover_share", "note"]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    narrow = sorted((r for r in out if r["kind"] in ("int", "date") and r.get("median_width_frac") != ""
                     and r["median_width_frac"] < 0.5), key=lambda r: (r["table"], r["median_width_frac"]))
    print(f"{len(out)} columns profiled -> {a.out}")
    print("columns with median width/range < 50% (order-following):")
    for r in narrow:
        print(f"  {r['table']:24s} {r['column']:28s} RGs={r['row_groups']:4d} "
              f"median={100*r['median_width_frac']:.2f}% p90={100*r['p90_width_frac']:.2f}%")
    for r in out:
        if r["kind"] == "string":
            print(f"  {r['table']:24s} {r['column']:28s} share of RGs covering full [min,max]: {r['full_cover_share']}")
