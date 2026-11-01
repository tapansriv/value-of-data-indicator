# R2D7 rg128k rerun — judgement calls

Plan: `~/value_of_data/REVISION_R2D7_RG128K.md`. One entry per decision, in order made (UTC).

- **2026-10-21 02:0xZ, setup.** Repo was already at `4416586` (= origin/main) and clean, so no pull
  was needed. Engine hashes verified: spark-sql `8b71ba1f…0256`, parquet-hadoop `50dcc11f…2b4e`,
  capture jar `db0154e3…4645`; spark @ `1fb30a5e3c`, parquet-java @ `5d67eec2`, both clean.
- **tmux.** Session `0` (created 02:01Z today, the one this agent runs in) is left alone; long jobs
  run in a new session `rg128k`.
- **Smoke test (SF1) passed, 02:04Z.** `PARQUET_ROOT=/mnt/tpcds/parquet_rg128k RG_ROWS=128000 SKIP_GEN=1 run_sf.sh 8 1`:
  convert 47 s; every non-final row group is exactly 128,000 rows on every table (store_sales
  23 RGs = 22×128,000 + 64,404); verify OK including the new RG_ROWS assertion. The parquet-mr
  trick worked, so the pyarrow re-chunk fallback is **not** used.
- **Default-path check without touching the first run.** Running `verify.py parquet 1` with plain
  defaults would rewrite `/mnt/tpcds/parquet/sf1/_verify.json` (forbidden). Instead: (a) with
  PARQUET_ROOT/RG_ROWS unset, `convert.OUT` and `SPARK_CONF` are byte-identical to `git show HEAD`'s;
  (b) `verify.py parquet 1 --full` (the mode the old file was made with) on a symlink mirror of
  `/mnt/tpcds/parquet/sf1` with RG_ROWS unset gives a `_verify.json` **identical** to the old one.
- **Pre-check rows-returned with DuckDB during conversion.** To calibrate literals without running a
  second heavy JVM next to the converter, row-returned checks for 132–163 are first done with
  duckdb 1.5.6 (memory_limit 6GB, 8 threads) on the new SF30 Parquet; footer-based RG counts come
  from pyarrow. The authoritative acceptance is the Spark run (spark-shell / capture), done after
  conversion finishes.
- **SF30 Parquet, 02:07–02:29Z.** convert 1,284 s, verify OK. Row-group counts are exactly the plan's
  expectation (store_sales 676, catalog_sales 338, web_sales 169, inventory 245, store_returns 68,
  catalog_returns 34, web_returns 17, customer_demographics 16, customer 4, customer_address 2, others 1);
  row counts equal `/mnt/tpcds/parquet/sf30/_verify.json` for 24/24 tables.
- **Order profile (§5.2)** reproduces the plan's table. Extra order-following columns found:
  `cs_ship_date_sk` (4.8%), `cs_catalog_page_sk` (8.8%), `cr_returned_date_sk` (14.4%),
  `cr_catalog_page_sk` (9.9%), `cd_dep_college_count` (constant within most cd RGs). The cd string
  columns (`cd_gender`, `cd_marital_status`, `cd_education_status`) cover their full [min,max] in
  16/16 RGs (cd cycles gender×marital×education every 70 rows), so q7/q26-style string filters
  **cannot** prune customer_demographics.
- **Level rounding.** Fractional levels are rounded half-up to a whole number of RGs at SF30
  (e.g. 1% of web_sales = 1.69 → 2 RGs; 25% of web_returns = 4.25 → 4). Prefix literal for "read k
  RGs" is `min(column in RG k) − 1`.
- **Template C/D/F windows.** "30 days" is implemented as q20's own 31-day d_date window
  (2001-02-03 .. 2001-03-05 inclusive), so the smallest window contains the base window as required;
  larger windows are centred on it. D windows start at the first day of d_month_seq 1205
  (2000-06-01) and cover 1/3/6/12 whole months.
- **Template F changed: `cr_order_number <= L` → `cr_returned_date_sk BETWEEN a AND b`.** q91 keeps only
  Dec-1999 returns, and cr_order_number follows the sale date: Dec-1999 returns sit only in
  catalog_returns RGs 7–13 at SF30 (peak RG 9). A prefix returns 0 rows at the 1-RG and 3-RG levels;
  "widen until rows" would push every level ≥ 8 RGs. A cr_order_number window centred on RG 9 was
  calibrated first (`sf30/rg_selective_overrides_UNUSED_cr_order_window.json`), then rejected because
  order-number↔date scales with SF: the same literals at SF60/100 select ~1998 orders → 0 rows.
  Swapping the base doesn't help: every other catalog_returns stream query (5,16,40,49,72,75,77,78,
  80,81,83) is date-filtered too, except q64 (very heavy) and q16/q40 (anti/outer join → ≥1 row
  trivially). So F keeps base q91 with a window on `cr_returned_date_sk` (already a q91 column) that
  **ends** on 1999-12-31 and extends backward 31/90/180/365 days. This is SF-invariant and contains
  q91's month, so every level returns q91's rows. Centred and forward windows were tried; they gave
  equal RG counts for levels 1–2 (each RG's return-date span is ~300 days); backward gives 7/8/11/13
  of 34 RGs at SF30 (footer prediction). The plan's "~1 RG, 10%" targets aren't reachable on
  this column; acceptance (rows ≥ 1, < base, monotone) is what is checked.
- **Parser check (132–163)**: parsed columns = base's columns + the target column for A,B,E,F(old),G;
  for C,D,F,H the target column was already a base column (join key), so the sets are identical.
- **DuckDB pre-check SF30**: all 32 return ≥ 1 row (min: q152–155 6 rows = q91's 6; q148 52; q132 80).
- **Convert-log volume (side effect, harmless).** With `parquet.block.size=1`, parquet-mr's
  `InternalParquetRecordWriter.flushRowGroupToStore` logs WARN "Too much memory used" plus the full
  column-store dump on every row-group flush (buffered size > 3 × block size). `_convert.log` is
  16 MB at SF30 (vs 16 KB for the first run). Data is unaffected; logs kept as is.
- **SF60 / SF100 Parquet.** SF60 02:29–03:12Z (convert 2,582 s), SF100 03:12–04:24Z (convert 4,308 s); verify OK
  (incl. the RG_ROWS assertion) and row counts identical to the first run's Parquet for 24/24 tables at both.
  DuckDB pre-check at SF60: all 32 authored queries return ≥ 1 row.
- **Spark acceptance SF30 (04:25–04:27Z): 32/32 accepted.** RowGroupCapture (same jar/conf) on the 8 bases +
  132–163 in a scratch query dir (`sf30/acceptance/`): every authored query ran, returned ≥ 1 row, and read
  strictly fewer target RGs than its base (each base reads all target RGs); levels strictly increase. Measured
  RG counts equal the footer predictions exactly for all 32. No base swaps beyond template F's column change.
- **Capture started 04:27Z** (`run_scripts/capture_all.sh`: PARQUET_ROOT=/mnt/tpcds/parquet_rg128k,
  RESULTS=/mnt/tpcds/results_rg128k, QUERIES=1-163; SF30→60→100). Stop thresholds (§5.4, read literally as
  10× the first run's event log): SF30 1.95 GB, SF60 2.44 GB, SF100 3.71 GB, or a driver OOM.
- **q23 flake recurs (SF30 stmt 0, 04:32Z):** the same `NullPointerException ... Decimal.toBigDecimal()`
  as the first run (RESULTS_NOTE "q23 is flaky on the fork"). Same handling as the first run: retry q23
  until both statements succeed (the capture is resumable; no `.done` marker was written). Retries run
  after the SF100 capture so no two heavy JVMs overlap, then `convert` is rerun for the affected SF.
- **SF30 capture 04:27–04:44Z, SF60 04:44–05:23Z.** SF60 163/163 clean (q23 passed first try). Event logs:
  SF30 481 MiB (2.5× first run), SF60 922 MiB (3.8×). Peak driver RSS 45.5 / 51.9 GB, min host available
  15.1 / 8.7 GB. 32/32 authored queries accepted at SF60 too.
- **SF100 event-log watch (05:35Z).** At q10, SF100's event log is 1.21 GB. Through q10 SF30/SF60 had
  25%/29% of their totals, which projects SF100 to ~3.8–4.8 GB, at or past the 10× line (3.71 GB). Growth is
  super-linear in SF (SF100/SF60 = 4.3× over q1–10; q9 alone: 96 MB at SF30, 230 MB at SF60), consistent with the
  named-accumulator O(tasks × row groups) effect in §5.4. Per the plan this is a hard-stop condition **when it is
  crossed**; nothing is changed pre-emptively (event logging stays on, same engine and conf).
- **SF100 capture 05:23–06:34Z: 163/163 clean.** Event log 2.72 GB (2,722,021,779 B; 7.3× the first run's
  371 MB, under the 3.71 GB line — the 05:35Z projection was pessimistic, the late queries are light). Peak
  driver RSS 50.9 GB, min host available 9.9 GB; no OutOfMemoryError in any driver log. No hard stop.
- **q23 SF30 retry 06:35Z:** both statements ok on the first retry; `convert 30` rerun → 163/163 completed.
  32/32 authored queries accepted at SF30, SF60 and SF100 on the main capture.
- **Paper-figure flags.** The first run's `paper_figs/sf<N>/` PDFs have no recorded command. Used
  `graph_comp_oracles.py --distro zipf --tpcds-only --ylim 1.0 --tables <select_display_tables.py DISPLAY SET>`.
- **Downstream started ~06:40Z** (`run_scripts/downstream.sh`): sweep, draws pools and vdi per SF concurrently.
  `draws_convergence.py` got an opt-in `--query-set` (default unchanged) so the pools use query_set_131.json.
