"""Numbers behind the Sec 4.4 figures, for a before/after comparison.

For one VDI output directory, writes every table's share per series (Fig 3 dividing
strategies at Table granularity; Fig 4 granularities under Equal) as the quartiles the
boxes show, plus the normalized frequency baseline. With --compare, joins several such
CSVs on (series, table) so the July-submission numbers sit next to the rerun's.

  python sec44_summary.py --data-dir ../data --label drill_sf30 --out before.csv
  python sec44_summary.py --data-dir ../../r2d7_results/sf30/vdi --tpcds-only \
      --label spark_sf30 --out after_sf30.csv
  python sec44_summary.py --compare before.csv after_sf30.csv ... --out compare.csv
"""

import os
from argparse import ArgumentParser

import numpy as np
import pandas as pd

from analyze_history_sweep import load_schema, series_shares
from draws_convergence import frequency_baselines

SERIES = {"fig3_full": "table", "fig3_equal": "table", "fig3_cardinality": "table",
          "fig4_table": "table", "fig4_column": "column", "fig4_rowgroup": "rowgroup"}


def summarize(data_dir, tpcds_only, label, num_trials):
    tables, col_to_tbl = load_schema("../data", "../../tpcds_schema", tpcds_only)
    shares = series_shares(data_dir, "zipf", tables, col_to_tbl, num_trials)
    freq = frequency_baselines(data_dir, tables, col_to_tbl)
    rows = []
    for s, gran in SERIES.items():
        for t in tables:
            v = np.asarray(shares[s][t])
            rows.append({"label": label, "series": s, "table": t,
                         "q1": np.percentile(v, 25), "median": np.percentile(v, 50),
                         "q3": np.percentile(v, 75), "mean": v.mean(),
                         "max": v.max(), "frequency": freq[gran][t]})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    p = ArgumentParser()
    p.add_argument("--data-dir")
    p.add_argument("--tpcds-only", action="store_true")
    p.add_argument("--label")
    p.add_argument("--num-trials", type=int, default=100)
    p.add_argument("--compare", nargs="+")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    if a.compare:
        wide = None
        for f in a.compare:
            d = pd.read_csv(f)
            lab = d.label.iloc[0]
            d = d.set_index(["series", "table"])[["median", "q1", "q3", "frequency"]]
            d.columns = [f"{c}_{lab}" for c in d.columns]
            wide = d if wide is None else wide.join(d, how="outer")
        wide.round(4).to_csv(a.out)
    else:
        summarize(a.data_dir, a.tpcds_only, a.label, a.num_trials).to_csv(a.out, index=False)
    print(f"wrote {os.path.abspath(a.out)}")
