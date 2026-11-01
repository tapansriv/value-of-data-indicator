'''
R2D7: are Sec 4.4's dividing-strategy and granularity conclusions stable across scale factors?

Reads each SF's assign_val_to_de.py output (/mnt/tpcds/results/sf<N>/vdi) and reports, per
distribution:
  - whether Full/Equal table and column values are identical across SFs (they depend only on
    which columns each query references, not on the data, so they should be);
  - per-table median share of total value for each dividing strategy and granularity, and the
    frequency baseline, at each SF;
  - Spearman rank correlation of those per-table shares between every pair of SFs;
  - how often, per table, the ordering of strategies (Full/Equal/Cardinality) and of
    granularities (Table/Column/Row group) agrees between SFs.
'''

import itertools
import json
import os
from argparse import ArgumentParser

import numpy as np
from scipy.stats import spearmanr


def load(path):
    with open(path) as fp:
        return json.load(fp)


def col_table_map():
    cols_in_tbls = load("../../tpcds_schema/tpcds_columns_in_tables.json")
    return {c: ("tpcds.customer" if t == "customer" else t)
            for t, cols in cols_in_tbls.items() for c in cols}


def shares_by_table(per_trial, to_table=None):
    '''{trial: {key: value}} -> {table: [share of trial total, per trial]}'''
    out = {}
    for trial in sorted(per_trial, key=int):
        vals = per_trial[trial]
        agg = {}
        for k, v in vals.items():
            if isinstance(v, dict):         # row groups: {table: {rg: value}}
                v = sum(v.values())
            t = to_table[k] if to_table else k
            agg[t] = agg.get(t, 0) + v
        total = sum(agg.values())
        for t, v in agg.items():
            out.setdefault(t, []).append(v / total if total else 0.0)
    return out


def medians(d):
    return {t: float(np.median(v)) for t, v in d.items()}


def summarize(sf_dir, distro, c2t):
    d = lambda name: load(os.path.join(sf_dir, "vdi", name))
    s = {}
    for divide in ["full", "equal", "cardinality"]:
        s[f"table/{divide}"] = medians(shares_by_table(d(f"data_val_tbls_{distro}_{divide}.json")))
        s[f"column/{divide}"] = medians(shares_by_table(d(f"data_val_cols_{distro}_{divide}.json"), c2t))
    s["rowgroup/equal"] = medians(shares_by_table(d(f"data_val_rgs_tbls_{distro}_equal.json")))
    s["rowgroup/full"] = medians(shares_by_table(d(f"data_val_rgs_tbls_{distro}_full.json")))
    # frequency baseline (one "trial")
    for gran, name, mapping in [("table", "boris_data_val_tbls.json", None),
                                ("column", "boris_data_val_cols.json", c2t),
                                ("rowgroup", "boris_data_val_rgs_tbls.json", None)]:
        s[f"{gran}/frequency"] = medians(shares_by_table({"0": d(name)}, mapping))
    return s


def order(vals):
    return tuple(sorted(vals, key=lambda k: -vals[k]))


if __name__ == "__main__":
    parser = ArgumentParser(description="Compare Sec 4.4 VDI results across scale factors")
    parser.add_argument("--sfs", default="30,60,100")
    parser.add_argument("--results", default="/mnt/tpcds/results")
    parser.add_argument("--out", default="/mnt/tpcds/results/sf_comparison.json")
    parser.add_argument("--min-share", type=float, default=0.001,
                        help="Ignore tables whose median share is below this at every SF "
                             "when checking per-table orderings (ties at ~0 are noise)")
    args = parser.parse_args()
    sfs = args.sfs.split(",")
    c2t = col_table_map()

    report = {}
    for distro in ["zipf", "normal"]:
        r = report[distro] = {}
        dirs = {sf: os.path.join(args.results, f"sf{sf}") for sf in sfs}

        # 1. data-independent values must match exactly
        ident = {}
        for name in [f"data_val_tbls_{distro}_full.json", f"data_val_tbls_{distro}_equal.json",
                     f"data_val_cols_{distro}_full.json", f"data_val_cols_{distro}_equal.json"]:
            blobs = [open(os.path.join(dirs[sf], "vdi", name), "rb").read() for sf in sfs]
            ident[name] = all(b == blobs[0] for b in blobs)
        r["identical_across_sfs"] = ident

        summ = {sf: summarize(dirs[sf], distro, c2t) for sf in sfs}
        r["median_share"] = summ

        # 2. Spearman across SF pairs, per (granularity/strategy)
        rho = {}
        for key in summ[sfs[0]]:
            tables = sorted(set.union(*(set(summ[sf][key]) for sf in sfs)))
            for a, b in itertools.combinations(sfs, 2):
                x = [summ[a][key].get(t, 0.0) for t in tables]
                y = [summ[b][key].get(t, 0.0) for t in tables]
                rho.setdefault(key, {})[f"sf{a}_vs_sf{b}"] = round(float(spearmanr(x, y)[0]), 4)
        r["spearman_table_ranking"] = rho

        # 3. per-table orderings of strategies / granularities
        def agreement(keys):
            tables = sorted(t for t in summ[sfs[0]][keys[0]]
                            if any(summ[sf][k].get(t, 0) >= args.min_share
                                   for sf in sfs for k in keys))
            same, differ = 0, {}
            for t in tables:
                orders = {sf: order({k: summ[sf][k].get(t, 0.0) for k in keys}) for sf in sfs}
                if len(set(orders.values())) == 1:
                    same += 1
                else:
                    differ[t] = {sf: list(o) for sf, o in orders.items()}
            return {"tables": len(tables), "same_order_at_every_sf": same, "differ": differ}

        r["strategy_order"] = {g: agreement([f"{g}/full", f"{g}/equal", f"{g}/cardinality"])
                               for g in ["table", "column"]}
        r["granularity_order"] = agreement(["table/equal", "column/equal", "rowgroup/equal"])
        r["vdi_vs_frequency_sign"] = {}
        for g in ["table", "column", "rowgroup"]:
            signs = {}
            for sf in sfs:
                eq, fr = summ[sf][f"{g}/equal"], summ[sf][f"{g}/frequency"]
                signs[sf] = {t: ("freq>vdi" if fr.get(t, 0) > eq.get(t, 0) else "vdi>=freq")
                             for t in eq if max(eq.get(t, 0), fr.get(t, 0)) >= args.min_share}
            tables = sorted(set.intersection(*(set(s) for s in signs.values())))
            flips = {t: {sf: signs[sf][t] for sf in sfs} for t in tables
                     if len({signs[sf][t] for sf in sfs}) > 1}
            r["vdi_vs_frequency_sign"][g] = {"tables": len(tables), "flips": flips}

    with open(args.out, "w") as fp:
        json.dump(report, fp, indent=2, sort_keys=True)
    print(f"wrote {args.out}")
