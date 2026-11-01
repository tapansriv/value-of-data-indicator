"""Frequency share vs VDI median per table (sec44_after/frequency_vs_vdi.csv).

  python frequency_vs_vdi.py ../../r2d7_results ../../r2d7_results/sec44_after/frequency_vs_vdi.csv
"""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.getcwd())
from analyze_history_sweep import load_schema, series_shares
from draws_convergence import frequency_baselines
R = sys.argv[1]; out = sys.argv[2]
SER = {"fig3_full": "table", "fig3_equal": "table", "fig4_column": "column", "fig4_rowgroup": "rowgroup"}
tables, c2t = load_schema("../data", "../../tpcds_schema", True)
rows = []
for sf in [30, 100]:
    d = f"{R}/sf{sf}/vdi"
    sh = series_shares(d, "zipf", tables, c2t, 100); fq = frequency_baselines(d, tables, c2t)
    for s, g in SER.items():
        for t in tables:
            v = np.asarray(sh[s][t]); f = fq[g][t]; med = np.percentile(v, 50)
            rows.append(dict(sf=sf, series=s, table=t, freq=f, vdi_med=med, q1=np.percentile(v, 25),
                             q3=np.percentile(v, 75), ratio=(f / med if med else np.nan), p_vdi_below=(v < f).mean()))
pd.DataFrame(rows).to_csv(out, index=False)
