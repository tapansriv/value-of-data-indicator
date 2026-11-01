# R2D7 results — TPC-DS row-group capture through Spark, SF1/30/60/100

Raw outputs of the R2D7 scale-factor run (Chameleon node, 2026-09-26/27). Start with
**`RESULTS_NOTE.md`**: settings, decisions, caveats and results. Paths in the notes of the
form `/mnt/tpcds/results/<x>` correspond to `r2d7_results/<x>` here. The TPC-DS raw text
(178 GB) and Parquet (61 GB) are not in git; `sf<N>/datagen/` records how to regenerate
them exactly (dsdgen 4.0.0, seed 19620718) and how they were verified.

**Second run (2026-10-21):** `rg128k/` holds the rerun with 128,000-row row groups and the
32 authored row-group-selective queries 132–163. See `rg128k/README.md`.

Code that produced this: `tpcds_datagen/`, `spark-lineage-api/listener_versions_new/RowGroupCapture.scala`,
`oracle/scripts/{run_spark_sf.sh,run_capture_all.sh,spark_rg_to_access.py,gen_cardinality.py,compare_sf.py}`.
The Spark fork changes it ran on are in `provenance/spark_fork_uncommitted.diff`.

## Layout

| Path | What |
|---|---|
| `RESULTS_NOTE.md` | the results note: settings, decisions, capture outcome, results |
| `BUILD_NOTES.md` | Thrift / parquet-java / Spark fork build and verification |
| `sf_comparison.json` | cross-SF comparison (`compare_sf.py`): per-table median shares, Spearman, orderings |
| `common_completed_sf30_60_100.json` | the common query set used for every SF (all 99) |
| `provenance/` | exact code diffs, capture JAR, untracked-file tarball as run |
| `q23_stock_spark_check/` | query 23 on stock pyspark 3.5.5 vs the fork (flaky decimal NPE) |
| `run_logs/` | chained capture log, per-SF VDI logs, and the SF30/SF100 q23 retry console logs (gzipped) |
| `sf<N>/capture/queries.csv` | per statement: status, runtime, rows returned, execution IDs, row-group entries, error |
| `sf<N>/capture/rg/<q>.csv` | every row group read: statement, file, ordinal, row index offset, row count |
| `sf<N>/capture/driver.log.gz`, `spark_conf.txt` | Spark driver log and the full Spark conf |
| `sf<N>/eventlog/*.gz` | Spark event logs (physical plans, stages, which scans ran). `zcat` or load into a history server |
| `sf<N>/logs/tpcds_<q>/access.json` | per-query row groups in the shape `assign_val_to_de.py` reads |
| `sf<N>/logs/capture_summary.json` | per query: row groups, tables read, referenced tables with nothing read |
| `sf<N>/tpcds_cardinality.json`, `tpcds_columns_in_queries.*` | per-SF cardinality; columns each query references |
| `sf<N>/values/`, `sf<N>/vdi/`, `sf<N>/figs/` | task values, VDI outputs (with `manifest.json`), §4.4 figures |
| `SEC44_RERUN_NOTE.md` | §4.4 rerun: before/after, query-history sweep, number-of-draws study — start here for §4.4 |
| `sec44_before/` | frozen July-submission §4.4 figures and numbers (Drill data in `oracle/data/`, untouched) |
| `sec44_after/` | §4.4 figures per SF at `--ylim 1.0`, per-table numbers, `before_after_compare.csv` |
| `history_sweep/sf<N>/` | R2D8/R2D13 sweep, N=100–2000 × seeds 42–46: rank stability, claims, plots |
| `num_draws/` | convergence in the number of task-value draws (MCSE, ordering reproducibility) |
| `sf<N>/datagen/` | dsdgen/Parquet notes, row-count verification, conversion logs |
| `sf1/_capture_attempt1_planwalk_bug/` | first SF1 capture, before the execution-ID fix (7 queries lost all row groups) |
| `sf1/_aqe_off_check/` | q37/61/69 at SF1 with AQE off, showing the scans AQE skips |

SF1 is a smoke test only (every table is one row group there). The SF30 event log directory
also holds the SF30 query-23 retry; each SF's capture directory is resumable, so `queries.csv`
keeps earlier failed attempts and the connector uses each statement's latest row.

## Auditing entry points
- Did a query run and read what it should? `sf<N>/capture/queries.csv` → `sf<N>/logs/capture_summary.json`
  (`referenced_tables_with_no_row_groups` lists the known parser false positives and AQE-skipped scans).
- Row-group level detail: `sf<N>/capture/rg/<q>.csv`, checked against Parquet footers by
  `spark_rg_to_access.py` (offset, row count and ordinal must all match).
- Query plans: `sf<N>/eventlog/` (`SparkListenerSQLExecutionStart` carries each physical plan).
- Figures regenerate from `sf<N>/vdi/` with
  `graph_comp_oracles.py --tpcds-only --data-dir <sf>/vdi --fig-dir <out>` (run from `oracle/scripts`).
