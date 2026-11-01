# §4.4 as submitted (July 2026) — frozen "before" snapshot

The dividing-strategy and granularity figures (Fig 3, Fig 4) and their numbers as they
stood in the PVLDB #926 July submission, kept so the R2D7 Spark rerun
(`../sec44_after/`) can be compared against them. Nothing here is regenerated from the
Spark data.

**Source data:** `oracle/data/` (Drill-based, TPC-H + TPC-DS, SF30, 128 queries, N=1500,
history seed 42, 100 Zipf(2.0) task-value draws), last changed in commit `89352c9`
(2026-02-19). It is left untouched in place. The 2026-09-13 history sweep verified its
N=1500 point to be byte-identical to these files.

| Path | What |
|---|---|
| `submitted_figs/` | The exact PDFs `\includegraphics`'d by the submitted `metric.tex` (copied from `vod_paper2/vdi_figures/new/`). Plotted **before** the 2026-09-13 baseline fix (raw access fraction as the red line in Fig 3, TPC-H `customer` baseline under the Customer label, pre-revision table set). |
| `drill_figs_fixed_baseline/` | The same data re-rendered with the current `graph_comp_oracles.py` (normalized baseline, key lookup, revision table set, y-limit 0.70). Same numbers as the submission, corrected drawing. |
| `sec44_numbers_drill_sf30.csv` | Per series × table: quartiles, mean, max of the share over the 100 draws, and the normalized frequency baseline for that granularity (`oracle/scripts/sec44_summary.py`). |

Anchors that match the prior analysis (`oracle/HISTORY_SWEEP_RESULTS.md`): `date_dim`
median 14.4% (Full) / 14.6% (Equal); `store_sales` Cardinality max 0.961.

Regenerate:
```
cd oracle/scripts
python graph_comp_oracles.py --distro zipf --data-dir ../data --fig-dir <out>
python sec44_summary.py --data-dir ../data --label drill_sf30 --out <csv>
```
