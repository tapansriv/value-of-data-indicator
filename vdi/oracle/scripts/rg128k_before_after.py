'''
Before/after for the R2D7 rg128k rerun: first run (128 MiB row groups, queries 1-99) vs rerun
(128,000-row row groups, query set 1-99 + 132-163), per SF, from sec44_summary.py outputs and
compare_sf.py's sf_comparison.json.

  rg128k_before_after.py --old ../../r2d7_results --new /mnt/tpcds/results_rg128k \
      --out-csv $R/before_after_first_run.csv --out-md $R/before_after_first_run.md
'''

import json
import os
from argparse import ArgumentParser

import pandas as pd

SERIES = ["fig3_full", "fig3_equal", "fig3_cardinality", "fig4_column", "fig4_rowgroup"]
SHOW = ["date_dim", "store_sales", "tpcds.customer", "store", "catalog_sales", "web_sales",
        "inventory", "customer_demographics", "household_demographics", "item", "catalog_returns",
        "store_returns", "web_returns"]


def main():
    ap = ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--sfs", default="30,60,100")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-md", required=True)
    a = ap.parse_args()
    sfs = a.sfs.split(",")
    rows = []
    for sf in sfs:
        o = pd.read_csv(os.path.join(a.old, "sec44_after", f"sec44_numbers_spark_sf{sf}.csv"))
        n = pd.read_csv(os.path.join(a.new, "sec44_after", f"sec44_numbers_spark_sf{sf}.csv"))
        m = o.merge(n, on=["series", "table"], suffixes=("_old", "_new"), how="outer")
        m["sf"] = int(sf)
        rows.append(m)
    df = pd.concat(rows)
    df = df[["sf", "series", "table", "median_old", "median_new", "mean_old", "mean_new",
             "frequency_old", "frequency_new"]]
    df.to_csv(a.out_csv, index=False)

    L = ["# Before/after: first R2D7 run vs rg128k rerun\n",
         f"Old: `{os.path.abspath(a.old)}` (128 MiB RGs, 99 queries). New: `{os.path.abspath(a.new)}` "
         "(128,000-row RGs, query_set_131). zipf, N=1500, seed 42, 100 trials. Median share of total "
         "value, in %. Full CSV: `before_after_first_run.csv`.\n"]
    for s in SERIES:
        L.append(f"## {s}\n")
        L.append("| table | " + " | ".join(f"SF{sf} old | SF{sf} new" for sf in sfs) + " |")
        L.append("|---|" + "---:|" * (2 * len(sfs)))
        for t in SHOW:
            cells = []
            for sf in sfs:
                r = df[(df.sf == int(sf)) & (df.series == s) & (df.table == t)]
                if len(r):
                    cells += [f"{100 * r.median_old.iloc[0]:.2f}" if pd.notna(r.median_old.iloc[0]) else "–",
                              f"{100 * r.median_new.iloc[0]:.2f}" if pd.notna(r.median_new.iloc[0]) else "–"]
                else:
                    cells += ["–", "–"]
            L.append(f"| {t} | " + " | ".join(cells) + " |")
        L.append("")

    oc = json.load(open(os.path.join(a.old, "sf_comparison.json")))
    nc = json.load(open(os.path.join(a.new, "sf_comparison.json")))
    for distro in ("zipf", "normal"):
        L.append(f"## Cross-SF stability ({distro})\n")
        L.append("| metric | first run | rerun |")
        L.append("|---|---|---|")
        for key in sorted(nc[distro]["spearman_table_ranking"]):
            ov = oc[distro]["spearman_table_ranking"].get(key, {})
            nv = nc[distro]["spearman_table_ranking"][key]
            fmt = lambda d: f"{min(d.values()):.3f}–{max(d.values()):.3f}" if d else "–"
            L.append(f"| Spearman {key} | {fmt(ov)} | {fmt(nv)} |")
        for g in ("table", "column"):
            o_, n_ = oc[distro]["strategy_order"][g], nc[distro]["strategy_order"][g]
            L.append(f"| strategy order same at every SF ({g}) | {o_['same_order_at_every_sf']}/{o_['tables']} "
                     f"{sorted(o_['differ'])} | {n_['same_order_at_every_sf']}/{n_['tables']} {sorted(n_['differ'])} |")
        og, ng = oc[distro]["granularity_order"], nc[distro]["granularity_order"]
        L.append(f"| granularity order differs across SFs | {sorted(og['differ'])} | {sorted(ng['differ'])} |")
        for g in ("table", "column", "rowgroup"):
            o_, n_ = oc[distro]["vdi_vs_frequency_sign"][g], nc[distro]["vdi_vs_frequency_sign"][g]
            L.append(f"| VDI vs frequency flips ({g}) | {sorted(o_['flips'])} of {o_['tables']} | "
                     f"{sorted(n_['flips'])} of {n_['tables']} |")
        L.append(f"| Full/Equal identical across SFs | {all(oc[distro]['identical_across_sfs'].values())} | "
                 f"{all(nc[distro]['identical_across_sfs'].values())} |")
        L.append("")
    open(a.out_md, "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
