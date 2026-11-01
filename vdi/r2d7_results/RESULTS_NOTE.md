# R2D7 — TPC-DS row-group capture through Spark at SF30 / SF60 / SF100

Answers **R2D7** (dividing strategy and granularity at SF60 and SF100, not only SF30); feeds
§4.4 figures (`zipf_table_divide_compare_normalized`, `zipf_granularity_compare_normalized`).
Hypothesis stated up front (REVISION_EXPERIMENTS.md §4): the *ranking* of dividing strategies
and granularities is stable across scale factors.

Status: **capture complete** (2026-09-27; SF30 15:03–15:20Z, SF60 15:20–16:12Z, SF100 16:12–16:47Z,
q23 retries ~17:10Z). All 99 queries captured at every SF; common set = all 99.

## Decisions (Tapan, 2026-09-26)
- Drill SF30 comparison dropped; all SFs regenerated and run through Spark only. TPC-H dropped.
- All 99 TPC-DS queries attempted; setup failures acceptable.
- AQE left **on** (Spark default). Consequence: when a join side is empty at runtime, AQE never
  runs the other side's scan, so that table's row groups are not recorded for that query.
- query67.sql `select top 100` rewritten to `LIMIT 100` (it failed to parse otherwise).
- SFs compared on one **common query set** (queries completed at every SF), so every SF draws
  the same 1500-query history (`common_completed_sf30_60_100.json`).

## Data
- dsdgen **4.0.0** (`/home/cc/DSGen-software-code-4.0.0/tools/dsdgen`), `-rngseed 19620718`
  (the default), `-parallel 32` at SF30+ (8 at SF1). Chunk concatenation verified
  byte-identical to a non-parallel run at SF1.
- Parquet: pyspark **3.5.5** (parquet-mr 1.13.1), one file per table, `parquet.block.size`
  = 134217728 (128 MiB row groups), snappy, other writer settings default (1 MiB pages,
  dictionary on, PARQUET_1_0). Typed schema from `tpcds.sql`. Row order = dsdgen order
  (chunks unioned in child order, no shuffle/sort). Identical settings at every SF.
- Per-SF details, row counts, row-group counts, bytes: `/mnt/tpcds/parquet/sf<N>/DATAGEN_NOTES.md`.
- Per-SF cardinality (row counts from footers): `/mnt/tpcds/results/sf<N>/tpcds_cardinality.json`.

## Engine and capture
- Spark fork `rowgroup-dev` @ `f0c593da74ac8d00834eecce26ce3845f9b64269`, Scala 2.13.8, plus
  uncommitted fixes, diff sha256 `4821883f616fbb5c04ce5dccf73fbe78223ecee59638a76954c9742af95a7a13`
  (`provenance/spark_fork_uncommitted.diff`):
  1. clear `RowGroupFilter`'s ThreadLocal result before each read (unfiltered scans otherwise
     reported a previous task's, possibly another file's, row groups); record the split's
     row groups from the footer when no filter ran.
  2. one shared accumulator per execution ID (`RowGroupMetricsRegistry.getOrCreate`);
     previously each scan replaced the last, keeping only one table per query.
- parquet-java fork `vod_rg` @ `5d67eec21a2ac522003ff2827dddbeab91ec4cdc` (clean).
- Capture driver `RowGroupCapture` (`spark-lineage-api/listener_versions_new/RowGroupCapture.scala`),
  JAR sha256 `db0154e37177bb3c7d36dc35e1c2913d1189b2db09d2baeddf884ac80a284645`
  (`provenance/spark-rowgroup-capture.jar`). Runs each statement with `collect()`; execution
  IDs taken from the registry, not the final plan (AQE can drop every scan from it).
  Two-statement queries (14, 23, 24, 39) attributed as one query.
- Code: `value-of-data-metric` worktree `spark-scale` @ `e07871a2f95eca9ce7fc9a21acca8d7152305407`
  (branch merged into `main` at `add5396`; branch and worktree deleted 2026-10-08),
  tracked diff sha256 `b38462085de0ad5ac2029e4766280d572c1680c9e424069c5a4696f5a44c8104`,
  untracked files sha256 `7feb41efb1f94eef9d92d9b0a289c72a5da7d8086f604145223b2b938e8a72ed`
  (`provenance/`). Nothing committed.
- Spark conf: `local[*]` (40 cores), driver 48g, `spark.speculation=false`,
  vectorized reader + filter pushdown on (pinned), `reuseExchange=false`, `reuseSubquery=false`,
  AQE default (on). Full conf per SF: `sf<N>/capture/spark_conf.txt`; event logs `sf<N>/eventlog`.
- Queries: `spark-lineage-api/benchmarking/tpcds_queries_spark/query{1..99}.sql` (a different
  qgen stream from `tpcds_queries/`; 19 of the 99 reference different columns), so
  `tpcds_columns_in_queries.json` is regenerated from this set per SF.

## Pipeline (per SF, `oracle/scripts/run_spark_sf.sh`)
`capture` → `convert` (cardinality, columns, `spark_rg_to_access.py` → `logs/tpcds_<N>/access.json`)
→ `common` → `vdi` (`generate_oracle_vals.py`, `assign_val_to_de.py`, `graph_comp_oracles.py`
with `--tpcds-only`, seed 42, N=1500, 100 trials) → `sf<N>/figs/`.

## Known caveats
- Column parser matched by substring. **Fixed deliberately 2026-10-07; this changes VDI
  inputs.** Rerun 2026-10-07 on the same Spark capture (no recapture needed: the parser only
  runs in the local `convert` step); the derived outputs (`sf<N>/` columns files, `vdi`, `figs`,
  `sf_comparison.json`, `history_sweep/`, `num_draws/`, `sec44_after/`) were overwritten in place.
  Pre-fix versions are in git at `6bbf534`. The Results section below is post-fix.
  `tpcds_parse_columns_from_query.py` credited a column wherever its name appeared as a
  substring, so the Spark set's columns file had false credits in 78 of 99 queries:
  `d_date` (⊂ `d_date_sk`) 89 credits vs 22 real; `t_time` (⊂ `t_time_sk`) 5 vs 1;
  `i_manufact` (⊂ `i_manufact_id`) 10 vs 2; `i_brand`/`i_class`/`i_category` (⊂ `*_id`) in
  14/75; `ws_net_paid` (⊂ `ws_net_paid_inc_*`) in 66; `p_cost` (⊂ `*_ext_ship_cost`) in
  16/94/95; `s_store_sk` (⊂ `ss_store_sk`) in 44. Only the last two drop a whole table
  (`promotion` from 16/94/95, `store` from 44), so table granularity moves only through those
  four queries; column granularity moves broadly. Row-group granularity does not depend on the
  columns file (it comes from the capture). Fix: match whole identifiers after stripping SQL
  comments; output format unchanged. Removing comments changed nothing in either query set. The
  fixed parser on the July set (`tpcds_queries/{N}_drill2.sql`) matches the clean
  `clustering/value_generation/tpcds_columns_in_queries.json` exactly for queries 1–99. The
  July `oracle/data/tpcds_columns_in_queries.json` (98 of 131 queries wrong, `d_date` 113 vs 26)
  is left as is because it is the source of the frozen `sec44_before/`.
- Figures 3/4 table set drops `lineitem` under `--tpcds-only` (six tables); open question.

## SF1 smoke test (not a result)
99/99 queries captured; every query read ≥1 row group. Every table fits one row group at SF1,
so SF1 says nothing about row-group effects. Referenced tables with no row groups: 16/44/94/95
(parser false positives above), 37/61/69 (AQE-skipped scans; confirmed by an AQE-off rerun in
`sf1/_aqe_off_check`), 61 `store` (row group pruned by statistics: `s_gmt_offset` −5 vs filter −7).
SF1's derived outputs (`sf1/` columns file, `vdi`, `figs`) were **not** rerun after the parser fix
and still carry the substring false credits.

## Capture outcome
| SF | queries captured | capture wall-clock (sum of statements) | failures |
|---|---|---|---|
| 30 | 99/99 | 982 s | q23 stmt 0 on first pass; ok on retry |
| 60 | 99/99 | 3140 s | none |
| 100 | 99/99 | 2064 s | q23 stmt 1 on first pass; ok on retry |

- Full-scan queries read every row group of the fact table at each SF (e.g. q3/7/28/43/88/96:
  store_sales 29/58/96 = all row groups in the file), so capture scales as expected.
- SF60 took longer than SF100 because q64/q78/q80 ran 5–8 min at SF60 vs ~1–1.5 min at SF30/100.
  Runtime is not a result of this experiment; row groups read are unaffected.
- **q23 is flaky on the fork.** `NullPointerException` in `Decimal.toBigDecimal` (null scalar
  subquery result) — 2 failures in 4 fork runs at SF30 plus 1 at SF100; stock pyspark 3.5.5
  passed 4/4 at SF30 (stock SF100 OOM'd at 40g, inconclusive). Cause not identified. It fails
  loudly (no wrong data), and was retried until both statements succeeded
  (`q23_stock_spark_check/`, `run_logs/sf{30,100}_capture_console_q23retry.log.gz`; earlier failed rows remain in
  `queries.csv`, the connector uses each statement's latest row).
- Referenced tables with no row groups read, every SF: 61/69 and at SF30/60 16's
  call_center/catalog_returns (before the parser fix also 16/44/94/95, all false positives) (AQE-skipped scans, per the AQE-on decision).

## Results (common set of 99 queries, N=1500, seed 42, 100 trials) — `sf_comparison.json`
Figures: `sf<N>/figs/`. Comparison script: `oracle/scripts/compare_sf.py`.

- **Full/Equal at table and column granularity are byte-identical across SFs** — they depend
  only on which columns each query references, not on the data. So Fig 3's Full and Equal boxes
  cannot change with SF; only Cardinality can.
- **Rankings are stable (hypothesis holds).** Spearman of per-table median share, zipf:
  table/cardinality 0.981–0.994, column/cardinality 0.992–0.998, rowgroup/equal 0.950–0.986,
  rowgroup/full 0.964–0.995 (lowest always SF30 vs SF100). Normal: rowgroup/equal 0.894–0.972,
  others ≥ 0.957. (Pre-fix: table/cardinality 0.977–0.992, column/cardinality 0.991–0.997.)
- **Strategy ordering per table** (Full vs Equal vs Cardinality): identical at every SF for 24/24
  tables (table) and 23/23 (column) under zipf; normal differs only for catalog_returns (table;
  store_returns before the parser fix).
- **Granularity ordering per table** (Table vs Column vs Row group, Equal): same at every SF for
  23/24 tables under zipf; differs only for inventory (pre-fix 22/24, also store_returns).
- **VDI vs frequency** (which is larger, per table): no flips at table or column granularity;
  at row-group granularity one flip under zipf (catalog_returns at SF100).
- **Magnitudes at row-group granularity drift with SF**, systematically: Equal splits a query's
  value across the row groups it reads, fact tables gain row groups with SF while dimensions stay
  at one, so dimension shares shrink and fact shares grow. Zipf median share (SF30/60/100):
  date_dim 3.5/2.1/1.3%, store_sales 48.1/50.1/50.6%, customer 0.9/0.6/0.4%.
  Table-level Equal for comparison: date_dim 19.4%, store_sales 16.0% at every SF (pre-fix 19.3/15.7%).
- **inventory** jumps at SF100 (row-group share 0.5/0.6/1.1%, cardinality share 1.6/1.7/2.3%)
  because dsdgen scales it non-linearly: 31.3M / 67.6M / 399.3M rows (2/3/16 row groups).
- Caution for the paper: these SF30 numbers are **not** the paper's SF30 numbers (e.g. date_dim
  table/equal mean 19.3% here (19.2% pre-fix) vs 14.5% mean in the current §4.4 analysis). The query set changed (TPC-DS only, no TPC-H; Spark
  qgen stream with 19 queries touching different columns; 99 vs 91 queries) along with the engine.
