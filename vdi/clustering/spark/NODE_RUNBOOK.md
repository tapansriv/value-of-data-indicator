# Node runbook: sorting experiment on Spark + Iceberg

Run from `value-of-data-metric/clustering/spark/` on `main` (developed on branch `sorting-spark`,
merged at `c334627` and deleted 2026-10-08). Every step
is `./run_phase.sh <step>`. Long steps go in tmux. Steps marked **STOP** end with a
report to Tapan; wait for an answer before continuing.

A smoke test of steps 1–4 passed on a laptop with TPC-DS SF0.1 and 4k-row row groups
(2026-10-07; see REVISION_SORTING.md → Code state). Nothing has run at SF30 yet.

## 1. Environment (minutes)

1. Check `env.sh` against the node:
   - `SPARK_HOME`: the `rowgroup-dev` fork, Scala 2.13 (`$SPARK_HOME/bin/spark-submit --version`).
     Java 17. Only the column/table listener is used; the fork's Parquet row-group hook
     is bypassed (Iceberg has its own reader), and that is intended.
   - `SOURCE_DIR`: TPC-DS **SF30** Parquet, one `<table>.parquet` (file or directory) per
     table, all 24 tables. Look for `/home/cc/tpcds_30gb` and `/mnt/tpcds/parquet/sf30`.
     If both exist, ask Tapan which to use.
   - `WORK`: a directory on a mounted 1.8 TB disk. If no disk is mounted, **ask Tapan
     which device to use before formatting or mounting anything**
     (`../../spark-lineage-api/INSTRUCTIONS.md` has the commands).
   - `mvn` and `python3` with `pyarrow` available (`python3 -c "import pyarrow"`).
2. `./run_phase.sh setup` — downloads the Iceberg 1.8.1 runtime jar, builds the runner
   jar, prints versions and free disk.
3. `./run_phase.sh check-source` — must print `OK: row counts match`. The rankings
   assume these SF30 row counts (`../value_generation/tpcds_sf30_row_counts.json`).
   On a mismatch, **STOP**.

## 2. Baseline (tens of minutes; tmux)

`./run_phase.sh build-base` — 24 unsorted, unpartitioned Iceberg tables in namespace
`base`, row groups of exactly 128,000 rows, exactly 32 row groups per file, rows in source
order. The last log line
must be `multi-row-group tables match the manifest (10)`. If it prints a WARNING
instead, **STOP**: the ranking's eligibility filter assumed a different set of tables.

## 3. Query check (minutes)

`./run_phase.sh explain` — plans all 99 queries without running them. Expect 99/99
`ok` in `$RESULTS/explain.jsonl`. If a query fails, report the error. Don't edit
`queries_spark/` without asking: the query text must stay equivalent to the DuckDB run.

## 4. Pilot (hours; tmux) — **STOP afterwards**

1. `./run_phase.sh build-pilot` — `store_sales` sorted on (`ss_sold_date_sk`,
   `ss_item_sk`), Frequent's first choice, in three modes:
   - `s`: sorted only
   - `ps`: partitioned by a transform of `ss_sold_date_sk` + sorted
   - `pz`: partitioned + Z-order
2. `./run_phase.sh pilot` — the 99-query baseline, a repeat of base on the 67 store_sales
   queries (determinism), and the three arms on those 67 queries.
3. `./run_phase.sh analyze` — writes `$RESULTS/analysis/pilot_*.csv` and prints a summary.

**Report to Tapan, then wait:**
- For each arm, % change in bytes vs base under each measure: `task_bytes_read` (Spark
  task input metrics), `proc_rchar` (JVM read syscalls), and the Iceberg scan metrics
  (`scan:*`; `skippedDataFiles` and `totalFileSize` are the interesting ones).
- In how many of the 67 queries DPP fired (`dpp_in_plan`) for `ps`/`pz` vs `s`. If it
  never fires for `ps`, check `EXPLAIN FORMATTED` of query 03 and report what the scan
  shows. Do not try to fix it.
- Determinism: max |base_rep − base| per measure. Expect exactly 0 for
  `task_bytes_read`: `AQEPropagateEmptyRelation` is excluded in `run_phase.sh` for this
  reason. Any nonzero difference is a finding; report which queries.
- How `task_bytes_read` (Spark task metrics; populated for Iceberg in the smoke test) and
  `proc_rchar` (all JVM reads, including metadata) compare.
- Build time and size per layout (`$RESULTS/build_stats.jsonl`) and median query runtime.

Done 2026-10-07; Tapan decided **ps** and **task_bytes_read + task_records_read**
(REVISION_SORTING.md → Pilot results).

## 5. Configurations, measured directly (tmux)

Each selected configuration's tables are sorted at once and the queries that read them run;
see REVISION_SORTING.md → Execution. K and C select configurations (comma-separated or
`all`); MODE is `ps`.

1. `./run_phase.sh build-configs ps K C` — builds the layouts those configurations need
   (skips complete ones; rebuilds any whose partitioning no longer matches the rule).
2. `./run_phase.sh configs ps K C` — `nosort` (99 queries), one run per distinct set of
   sorted tables, and a repeat of Frequent's groups. Resumable; appends to
   `$RESULTS/configs_ps.jsonl`, so later K/C selections reuse the same No Sort run.
3. `./run_phase.sh analyze ps` — utilities for every configuration whose group ran.
4. `./run_phase.sh plot ps K C` — `workload_value.pdf` (bytes) and
   `workload_value_rows.pdf` (rows) from `analysis/paper_ps_kK_cC/`.

k = 2, c = 2 (the paper's setting): 15 configurations, 4 groups, 435 query runs including
No Sort and the repeat, about 1.5 h. Started 2026-10-08.

**Report:**
- Utility per value assignment for VOD, Frequent, Random and No Sort, under both metrics,
  and the VOD-vs-Frequent and VOD-vs-Random gaps.
- Determinism of the repeated group: any query whose bytes or rows differ is a finding.
- Any configuration skipped for a missing or failed measurement (no number is computed).
- Listener cross-check (`listener_vs_static.csv`).
- Errors, retries, and anything skipped.

## Reference

- **Resuming.** Rerun the same step. Builds skip tables marked `vdi.complete=true`;
  runs skip (run, query) pairs already recorded as `ok`. Failed queries are retried.
- **Outputs** (`$RESULTS`): `build_stats.jsonl`, `base_props.json`, `explain.jsonl`,
  `pilot.jsonl`, `configs_<MODE>.jsonl` (one JSON line per
  query: bytes measures, runtime, per-scan metrics, DPP flag, layout bindings),
  `*.meta.jsonl` (Spark conf, versions, host per invocation), `usage_logs/` (the
  listener's output), `eventlog/`, `analysis/`.
- **Runtime** is recorded but not the metric. Bytes do not depend on the OS page cache;
  runtime does. Don't drop caches.
- **Memory.** `DRIVER_MEM` in `env.sh` (default 48g; local mode runs executors in the driver).
- **Utility** (unchanged from the paper): Σ value(q) · bytes_nosort(q) / bytes(q); No Sort = Σ value(q).

## Second workload: Redbench IMDb (R3D4) — `WORKLOAD=imdb`

Same harness, separate state: with `WORKLOAD=imdb`, `env.sh` puts the warehouse, results and
plans under `$WORK/imdb/`, and `run_phase.sh` uses `manifest_imdb.json`. Nothing touches the
TPC-DS catalog. With `WORKLOAD` unset everything is exactly the TPC-DS setup (regression-checked
2026-10-07 against 02f2560: identical `manifest.json`; identical plans for every phase apart from
a new `base_tables` key; all 62 `analyze` output files byte-identical).

**Do not run IMDb measurement phases while TPC-DS measurement phases are running** — bytes are
deterministic, but runtime and contention are not, and both share `local[*]`.

Prerequisite: `redbench_imdb/` (workload, `harness/` inputs, `queries_spark/`) present in this
checkout. Disk: source + base ~3.7 GB under `$WORK/imdb`, plus one Iceberg copy per layout
built (≤ ~10 GB for every layout in the manifest), plus ~5 GB of CSV scratch, deletable after
loading.

```bash
export WORKLOAD=imdb                     # in the tmux shell, for every step below
source ./env.sh
./run_phase.sh setup                     # REQUIRED once: rebuilds the runner jar (base_tables)
"$ANALYSIS_PYTHON" ../../redbench_imdb/load_imdb_parquet.py --out "$SOURCE_DIR"   # needs duckdb
./run_phase.sh check-source              # must print "OK: row counts match" (21 tables)
./run_phase.sh build-base                # 21 unsorted Iceberg tables
./run_phase.sh explain                   # must be 415/415 ok
./run_phase.sh build-pilot && ./run_phase.sh pilot && ./run_phase.sh analyze
./run_phase.sh build-configs ps 2 2 && ./run_phase.sh configs ps 2 2 && ./run_phase.sh analyze ps
```

Cost of `configs` (measured directly, one run per distinct set of sorted tables):

| selection | runs | query executions |
|---|---|---|
| k=2, c=2 (default) | 10 | 2,667 |
| k=1..4, c=2 | 35 | 9,191 |
| k=2, c=1..3 | 27 | 6,986 |
| k=all (1..14), c=2 | 169 | 63,599 — too many; don't |

**Stop after the pilot and report per-query runtime** before going beyond k=2, c=2.
`analyze` defaults to `--weighting executions` for IMDb (net utility: each query weighted by how
often it ran in the Redset trace; normalize to No Sort); `paper_*/profiles_combined_*.csv` gain
an `executions` column. `plot` still assumes TPC-DS (`profiles_combined_{0..4}.csv`, unweighted)
— not yet adapted for IMDb.
