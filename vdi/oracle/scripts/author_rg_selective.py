'''
Author the R2D7 row-group-selective TPC-DS queries 132-163 (REVISION_R2D7_RG128K.md §5.3).

8 templates x 4 levels. Each query is an existing query from the Spark qgen stream
(spark-lineage-api/benchmarking/tpcds_queries_spark/queryN.sql) copied verbatim with ONE added
conjunct: a literal range on a column that dsdgen writes in (near) row order. Levels are nested
prefixes (key <= L) or nested windows (BETWEEN a AND b). Literals are calibrated on one SF
(SF30) from the Parquet footers and then fixed: the query text is identical at every SF.

  author_rg_selective.py author --parquet-dir /mnt/tpcds/parquet_rg128k/sf30 \
      --query-dir .../tpcds_queries_spark --calib-out $R/sf30/rg_selective_calibration.json
  author_rg_selective.py predict --parquet-dir /mnt/tpcds/parquet_rg128k/sf60 \
      --calib $R/sf30/rg_selective_calibration.json --out $R/sf60/rg_selective_predicted.json

`predict` reports, for each authored query, how many of the target table's row groups have a
footer [min, max] that intersects the added predicate (an upper bound on what a statistics-based
scan reads; the capture gives the measured value).
'''

import datetime
import json
import math
import os
from argparse import ArgumentParser

import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq

AUTHORED = "2026-10-21"
FIRST = 132

# template key -> base query, target table/column, anchor line (stripped) after which the
# conjunct is inserted, kind, levels. Prefix levels are numbers of row groups to read at SF30
# (or fractions of the target's row groups); window levels are described per kind.
TEMPLATES = [
    dict(key="A", base=3, table="store_sales", column="ss_ticket_number", qual="store_sales.",
         anchor="AND dt.d_moy = 11", kind="prefix", levels=[0.01, 0.05, 0.10, 0.25]),
    dict(key="B", base=12, table="web_sales", column="ws_order_number", qual="",
         anchor="AND      ws_sold_date_sk = d_date_sk", kind="prefix",
         levels=[0.01, 0.05, 0.10, 0.25]),
    dict(key="C", base=20, table="catalog_sales", column="cs_sold_date_sk", qual="",
         anchor="AND      cs_sold_date_sk = d_date_sk", kind="date_window_days",
         base_window=("2001-02-03", "2001-03-05"), levels=[30, 90, 180, 365]),
    dict(key="D", base=22, table="inventory", column="inv_date_sk", qual="",
         anchor="AND d_month_seq BETWEEN 1205 AND 1205 + 11", kind="month_window",
         month_seq=1205, levels=[1, 3, 6, 12]),
    dict(key="E", base=84, table="store_returns", column="sr_ticket_number", qual="",
         anchor="AND sr_cdemo_sk = cd_demo_sk", kind="prefix", levels=[1, 0.10, 0.25, 0.50]),
    # F: cr_order_number follows the sale date, and q91 keeps only Dec-1999 returns, so a key
    # prefix/window calibrated on SF30 lands on other dates at SF60/100 (0 rows). A window on
    # cr_returned_date_sk containing q91's month is SF-invariant (DECISIONS.md, 2026-10-21).
    dict(key="F", base=91, table="catalog_returns", column="cr_returned_date_sk", qual="",
         anchor="AND ca_gmt_offset = -7", kind="date_window_days",
         base_window=("1999-12-01", "1999-12-31"), levels=[31, 90, 180, 365], align="end"),
    dict(key="G", base=30, table="web_returns", column="wr_order_number", qual="",
         anchor="AND wr_returning_addr_sk = ca_address_sk", kind="prefix",
         levels=[1, 3, 0.25, 0.50]),
    dict(key="H", base=26, table="customer_demographics", column="cd_demo_sk", qual="",
         anchor="AND d_year = 2000", kind="prefix", levels=[1, 2, 0.25, 0.50]),
]


def rg_stats(path, column):
    md = pq.ParquetFile(path).metadata
    j = md.schema.names.index(column)
    mins, maxs = [], []
    for i in range(md.num_row_groups):
        st = md.row_group(i).column(j).statistics
        mins.append(st.min)
        maxs.append(st.max)
    return np.array(mins), np.array(maxs)


def n_rgs(level, total):
    '''A level is an absolute row-group count (int >= 1) or a fraction of the table.'''
    if isinstance(level, int):
        return level
    return max(1, int(math.floor(level * total + 0.5)))


def rgs_hit(mins, maxs, lo, hi):
    '''Row groups whose [min, max] intersects [lo, hi] (None = unbounded).'''
    ok = np.ones(len(mins), bool)
    if lo is not None:
        ok &= maxs >= lo
    if hi is not None:
        ok &= mins <= hi
    return [int(i) for i in np.nonzero(ok)[0]]


def date_sk(dd, d):
    sk = dd["sk"][dd["date"].index(datetime.date.fromisoformat(d))]
    return int(sk)


def load_date_dim(parquet_dir):
    t = pq.read_table(os.path.join(parquet_dir, "date_dim.parquet"),
                      columns=["d_date_sk", "d_date", "d_month_seq"])
    return {"sk": t["d_date_sk"].to_pylist(), "date": t["d_date"].to_pylist(),
            "month_seq": t["d_month_seq"].to_pylist()}


def calibrate(t, parquet_dir, dd, overrides):
    path = os.path.join(parquet_dir, f"{t['table']}.parquet")
    mins, maxs = rg_stats(path, t["column"])
    total = len(mins)
    out = []
    for k, lev in enumerate(t["levels"], 1):
        ov = overrides.get(f"{t['key']}{k}")
        if t["kind"] == "prefix":
            want = n_rgs(lev, total)
            lit = int(ov["hi"]) if ov else int(mins[want]) - 1 if want < total else int(maxs.max())
            pred = f"{t['qual']}{t['column']} <= {lit}"
            lo, hi, comment = None, lit, ""
            desc = f"{lev:g} of RGs" if isinstance(lev, float) else f"{lev} RG(s)"
        elif t["kind"] == "date_window_days":
            b0 = datetime.date.fromisoformat(t["base_window"][0])
            b1 = datetime.date.fromisoformat(t["base_window"][1])
            span = (b1 - b0).days + 1                      # 31 days inclusive
            days = max(lev, span)
            extra = days - span
            # centred on the base window, or (align="end") extended backward from its end
            if t.get("align") == "end":
                d0 = b1 - datetime.timedelta(days=days - 1)
            else:
                d0 = b0 - datetime.timedelta(days=extra // 2)
            d1 = d0 + datetime.timedelta(days=days - 1)
            lo, hi = date_sk(dd, d0.isoformat()), date_sk(dd, d1.isoformat())
            pred = f"{t['column']} BETWEEN {lo} AND {hi}"
            comment = f" -- {d0.isoformat()} .. {d1.isoformat()} ({days} days)"
            desc = f"{days} days"
        elif t["kind"] == "month_window":
            m0, m1 = t["month_seq"], t["month_seq"] + lev - 1
            ds = [d for d, m in zip(dd["date"], dd["month_seq"]) if m0 <= m <= m1]
            d0, d1 = min(ds), max(ds)
            lo, hi = date_sk(dd, d0.isoformat()), date_sk(dd, d1.isoformat())
            pred = f"{t['column']} BETWEEN {lo} AND {hi}"
            comment = f" -- {d0.isoformat()} .. {d1.isoformat()} (d_month_seq {m0}..{m1})"
            desc = f"{lev} month(s)"
        if ov and ov.get("lo") is not None:            # window override for a prefix template
            lo = int(ov["lo"])
            pred = f"{t['qual']}{t['column']} BETWEEN {lo} AND {hi}"
            desc += f" (window override: {ov.get('why', '')})"
        hit = rgs_hit(mins, maxs, lo, hi)
        out.append({"query": None, "template": t["key"], "level": k, "level_spec": desc,
                    "base": t["base"], "table": t["table"], "column": t["column"],
                    "predicate": pred, "comment": comment, "lo": lo, "hi": hi,
                    "predicted_rgs": len(hit), "total_rgs": total,
                    "predicted_frac": round(len(hit) / total, 4),
                    "predicted_rg_range": [hit[0], hit[-1]] if hit else None})
    return out


def write_query(qdir, n, cal, t):
    src = open(os.path.join(qdir, f"query{t['base']}.sql")).read()
    lines = src.split("\n")
    idx = [i for i, l in enumerate(lines) if l.strip() == t["anchor"]]
    if len(idx) != 1:
        raise RuntimeError(f"query{t['base']}: anchor {t['anchor']!r} found {len(idx)} times")
    i = idx[0]
    a = lines[i]
    indent = a[:len(a) - len(a.lstrip())]
    kw = a.strip().split()[0]                       # "AND"
    pad = a.strip()[len(kw):len(a.strip()) - len(a.strip()[len(kw):].lstrip())]
    new = f"{indent}{kw}{pad}{cal['predicate']}{cal['comment']}"
    lines.insert(i + 1, new)
    header = (f"-- R2D7 rg-selective: base query{t['base']}, target {t['table']}, "
              f"level {cal['level']}/4, authored {AUTHORED}")
    path = os.path.join(qdir, f"query{n}.sql")
    open(path, "w").write(header + "\n" + "\n".join(lines))
    return path


def main():
    ap = ArgumentParser()
    ap.add_argument("mode", choices=["author", "predict"])
    ap.add_argument("--parquet-dir", required=True)
    ap.add_argument("--query-dir")
    ap.add_argument("--calib-out")
    ap.add_argument("--calib")
    ap.add_argument("--out")
    ap.add_argument("--overrides", default=None,
                    help="JSON {'<template><level>': {'hi': .., 'lo': .., 'why': ..}} applied to prefix levels")
    ap.add_argument("--dry-run", action="store_true", help="author: calibrate only, write no SQL")
    a = ap.parse_args()

    if a.mode == "author":
        dd = load_date_dim(a.parquet_dir)
        overrides = json.load(open(a.overrides)) if a.overrides else {}
        allcal = []
        n = FIRST
        for t in TEMPLATES:
            for cal in calibrate(t, a.parquet_dir, dd, overrides):
                cal["query"] = n
                if not a.dry_run:
                    cal["file"] = write_query(a.query_dir, n, cal, t)
                allcal.append(cal)
                n += 1
        for c in allcal:
            print(f"q{c['query']} {c['template']}{c['level']} base q{c['base']:<3d} {c['table']:22s} "
                  f"{c['predicate']}{c['comment']}  -> {c['predicted_rgs']}/{c['total_rgs']} RGs "
                  f"({100 * c['predicted_frac']:.1f}%) {c['predicted_rg_range']}")
        if a.calib_out:
            os.makedirs(os.path.dirname(a.calib_out), exist_ok=True)
            json.dump({"calibrated_on": os.path.abspath(a.parquet_dir), "authored": AUTHORED,
                       "overrides": overrides, "queries": allcal}, open(a.calib_out, "w"), indent=1)
    else:
        cal = json.load(open(a.calib))["queries"]
        out = []
        cache = {}
        for c in cal:
            key = (c["table"], c["column"])
            if key not in cache:
                cache[key] = rg_stats(os.path.join(a.parquet_dir, f"{c['table']}.parquet"), c["column"])
            mins, maxs = cache[key]
            hit = rgs_hit(mins, maxs, c["lo"], c["hi"])
            out.append({"query": c["query"], "table": c["table"], "predicate": c["predicate"],
                        "predicted_rgs": len(hit), "total_rgs": len(mins),
                        "predicted_frac": round(len(hit) / len(mins), 4)})
            print(f"q{c['query']} {c['table']:22s} {c['predicate']:45s} {len(hit)}/{len(mins)} "
                  f"({100 * len(hit) / len(mins):.2f}%)")
        if a.out:
            os.makedirs(os.path.dirname(a.out), exist_ok=True)
            json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
