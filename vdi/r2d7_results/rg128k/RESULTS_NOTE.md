# R2D7 rerun — 128,000-row row groups + row-group-selective queries, SF30 / SF60 / SF100

Rerun of the R2D7 row-group capture behind §4.4 (first run: `/mnt/tpcds/results`, repo
`r2d7_results/`, 2026-09-26/27). Plan: `~/value_of_data/REVISION_R2D7_RG128K.md`. Every judgement
call is logged, in order, in `DECISIONS.md`. Run 2026-10-21, 02:01–07:58Z, on the Chameleon node,
with no pilot gate. **No hard-stop condition was hit.**

Status: **complete.** Parquet at all three SFs, capture 163/163 at every SF, all downstream analyses
and candidate figures. Nothing is committed (see "Code" below).

## What differs from the first run (and nothing else does)

| | first run | this rerun |
|---|---|---|
| Row groups | `parquet.block.size` = 128 MiB (store_sales 29 RGs at SF30) | **exactly 128,000 rows** per row group except each file's last (store_sales 676 at SF30) |
| Pages | ~1 MiB (parquet-mr default size check) | cut at `parquet.page.row.count.limit` = 20,000 rows (side effect, below; not measured) |
| Queries captured | 1–99 | **1–163**: 1–99, the pre-existing 100–131, and new 132–163 |
| VDI query set | `common_completed_sf30_60_100.json` = 1–99 | **`query_set_131.json`** = common ∩ (1–99 ∪ 132–163) = 131 queries |
| Parquet root / results root | `/mnt/tpcds/parquet`, `/mnt/tpcds/results` | `/mnt/tpcds/parquet_rg128k`, `/mnt/tpcds/results_rg128k` |

The following are unchanged: dsdgen 4.0.0 raw text (seed 19620718, reused via `SKIP_GEN=1`, not
regenerated), row order (dsdgen order, no sort or shuffle), snappy, the schema, pyspark 3.5.5 /
parquet-mr 1.13.1 as the writer, and the engine. The engine is Spark fork `1fb30a5e3c` (clean) with
parquet-java `5d67eec2`, verified before capture: spark-sql `8b71ba1f…0256`, parquet-hadoop
`50dcc11f…2b4e`, capture jar `db0154e3…4645` (`provenance/engine_sha256.txt`). The Spark conf is also
unchanged (`local[*]`, driver 48g, AQE on, `reuseExchange=false`, `reuseSubquery=false`, speculation
off, vectorized reader + filter pushdown pinned). So are the column parser (post-`0834aa1`
whole-identifier version), N=1500, history seed 42, 100 trials, zipf + normal, the sweep (seeds
42–46, N=100–2000), and the draws study (2000-draw pool, value seed 20260927).

**Row-group size note.** 128,000 rows matches §6 (`clustering/spark/env.sh`) and the paper text.
DuckDB's true default is 122,880 (60 × 2048), which the July DuckDB/Drill files used. Per the plan,
we did not switch to it.

## Data

- **How the row groups were pinned** (`tpcds_datagen/convert.py`, `RG_ROWS=128000`). parquet-mr
  1.13.1 has no row-count limit, so the writer sets `parquet.block.size=1`,
  `parquet.page.size.row.check.min = max = 128000` and `parquet.writer.max-padding=0`, as both
  `spark.hadoop.*` and write options. `InternalParquetRecordWriter.checkBlockSizeReached` measures
  buffered size only every `row.check` records, and with a 1-byte block size the first check always
  flushes. The settings are recorded in `_convert_meta.json` → `effective_settings`. The pyarrow
  re-chunk fallback was **not** needed.
- **Side effects.** (1) The same min/max also gate the page-size check, so pages are cut by
  `page.row.count.limit` (20,000 rows) rather than at ~1 MiB. This is read off the parquet-mr code
  path; page sizes were not measured. (2) parquet-mr logs a WARN "Too much memory used" dump on
  every row-group flush, which makes `_convert.log` ~16 MB at SF30. File sizes are within ±4% of the
  first run's for every fact table except `inventory` (−28% / −16% / +0.3% at SF30/60/100).
- **Verification.** `verify.py` (with `RG_ROWS` set) asserts that every non-final row group has
  exactly 128,000 rows and the last has 1–128,000. It **passed at SF1/30/60/100**. Row counts equal
  the first run's Parquet for 24/24 tables at every SF. Row-content edge comparison against the raw
  text also passed, as in the first run.
- **Defaults reproduce the first run.** With `PARQUET_ROOT`/`RG_ROWS` unset, `convert.py`'s
  `SPARK_CONF` and paths are byte-identical to HEAD. `verify.py parquet 1 --full` on a symlink mirror
  of `/mnt/tpcds/parquet/sf1` gives a `_verify.json` identical to the first run's.
- Per-SF notes: `/mnt/tpcds/parquet_rg128k/sf<N>/DATAGEN_NOTES.md` (now prints the real writer
  settings) and `ROWGROUPS.md` (old vs new per table).

### Row groups per table, first run (128 MiB) → rerun (128,000 rows)

Tables not listed have 1 row group in both runs at every SF.

| table | SF30 | SF60 | SF100 |
|---|---:|---:|---:|
| store_sales | 29 → **676** | 58 → **1351** | 96 → **2250** |
| catalog_sales | 23 → 338 | 46 → 676 | 77 → 1125 |
| web_sales | 11 → 169 | 21 → 338 | 36 → 563 |
| inventory | 2 → 245 | 3 → 529 | 16 → 3120 |
| store_returns | 4 → 68 | 8 → 135 | 13 → 225 |
| catalog_returns | 3 → 34 | 5 → 68 | 8 → 113 |
| web_returns | 2 → 17 | 3 → 34 | 4 → 57 |
| customer_demographics | 1 → 16 | 1 → 16 | 1 → 16 |
| customer | 1 → 4 | 1 → 8 | 1 → 16 |
| customer_address | 1 → 2 | 1 → 4 | 1 → 8 |
| item | 1 → 1 | 1 → 1 | 1 → 2 |

## Which columns follow row order (§5.2, `sf30/order_profile.csv`)

The table below gives the median per-row-group [min,max] width as a share of the column's range,
from SF30 footers. It reproduces the plan's laptop estimate. `store_sales.ss_ticket_number` 0.15%,
`catalog_sales.cs_sold_date_sk` 0.22% (p90 0.54%), `cs_order_number` 0.30%, `web_sales.ws_order_number`
0.59%, `inventory.inv_date_sk` 0.38%, `sr_ticket_number` 1.5%, `cr_order_number` 3.0%,
`wr_order_number` 5.9%, `cd_demo_sk` 6.7%, `c_customer_sk` 30%. Also order-following:
`cs_ship_date_sk` 4.8%, `cs_catalog_page_sk` 8.8%, `cr_returned_date_sk` 14.4%, `cr_catalog_page_sk`
9.9%, and `cd_dep_college_count` (constant within most cd row groups). Every `*_item_sk` and
`ss_sold_date_sk` spans ≥ 50%. **`customer_demographics`' string columns cannot prune.** gender ×
marital × education cycle every 70 rows, so all 16 row groups cover every value of `cd_gender`,
`cd_marital_status` and `cd_education_status`.

## Queries 132–163 (§5.3)

8 templates × 4 nested levels. Each query is a Spark-stream query copied verbatim with one added
conjunct and a header comment. The literals were calibrated once on SF30 footers, and the text is
identical at every SF (`oracle/scripts/author_rg_selective.py`; calibration
`sf30/rg_selective_calibration.json`). The parsed columns of each query equal its base's, plus the
target column where it is new (A, B, E, G). For C, D, F and H the target column is already one of
the base's join keys.

| tmpl | queries | base → target | added predicate (levels) |
|---|---|---|---|
| A | 132–135 | q3 → store_sales | `ss_ticket_number <=` 7/34/68/169 RGs at SF30 (1/5/10/25%) |
| B | 136–139 | q12 → web_sales | `ws_order_number <=` 2/8/17/42 RGs (1/5/10/25%) |
| C | 140–143 | q20 → catalog_sales | `cs_sold_date_sk BETWEEN` 31/90/180/365-day windows centred on q20's 2001-02-03..03-05 |
| D | 144–147 | q22 → inventory | `inv_date_sk BETWEEN` 1/3/6/12 months from d_month_seq 1205 (2000-06-01) |
| E | 148–151 | q84 → store_returns | `sr_ticket_number <=` 1/7/17/34 RGs (~1 RG, 10/25/50%) |
| F | 152–155 | q91 → catalog_returns | `cr_returned_date_sk BETWEEN` 31/90/180/365-day windows ending 1999-12-31 (**changed from the plan**) |
| G | 156–159 | q30 → web_returns | `wr_order_number <=` 1/3/4/9 RGs, inside the CTE |
| H | 160–163 | q26 → customer_demographics | `cd_demo_sk <=` 1/2/4/8 RGs |

**Template F deviates from the plan** (DECISIONS.md has the full reasoning). q91 keeps only
Dec-1999 returns, and `cr_order_number` follows the sale date. So a `cr_order_number` prefix returns
0 rows at small levels, and a SF30-calibrated `cr_order_number` window lands on 1998 orders at
SF60/100. Every other catalog_returns stream query is date-filtered too, so swapping the base does
not help. A window on `cr_returned_date_sk` is SF-invariant and keeps q91's rows at every level, at
the cost of coarser pruning: no level reads ~1 RG, and the smallest reads ~18–21%.

**Acceptance: 32/32 at SF30, SF60 and SF100**, on the main capture. Every authored query ran and
returned ≥ 1 row. Each read strictly fewer target row groups than its base (each base reads all of
them), and the levels strictly increase. The measured counts equal the footer predictions exactly
at SF30. Full per-query, per-SF table: `authored_queries_by_sf.md`. Fraction of the target table
read:

| tmpl | SF30 | SF60 | SF100 | rows (SF30/60/100) |
|---|---|---|---|---|
| A store_sales | 1.0 / 5.0 / 10.1 / 25.0% | 0.5 / 2.5 / 5.0 / 12.5% | 0.3 / 1.5 / 3.0 / 7.5% | 80–100 / 100 / 100 |
| B web_sales | 1.2 / 4.7 / 10.1 / 24.9% | 0.6 / 2.4 / 5.0 / 12.4% | 0.4 / 1.4 / 3.0 / 7.5% | 100 |
| C catalog_sales | 1.2 / 3.0 / 9.2 / 20.1% | 1.0 / 3.0 / 8.9 / 20.0% | 1.1 / 2.9 / 8.9 / 20.0% | 100 |
| D inventory | 2.0 / 5.7 / 10.6 / 20.4% | 2.3 / 5.7 / 10.6 / 20.6% | 1.9 / 5.4 / 10.4 / 20.3% | 100 |
| E store_returns | 1.5 / 10.3 / 25.0 / 50.0% | 0.7 / 5.2 / 12.6 / 25.2% | 0.4 / 3.1 / 7.6 / 15.1% | 52–100 / 90–100 / 100 |
| F catalog_returns | 20.6 / 23.5 / 32.4 / 38.2% | 19.1 / 20.6 / 29.4 / 36.8% | 17.7 / 19.5 / 27.4 / 36.3% | 6 / 10 / 30 |
| G web_returns | 5.9 / 17.6 / 23.5 / 52.9% | 2.9 / 8.8 / 11.8 / 26.5% | 1.8 / 5.3 / 7.0 / 15.8% | 100 |
| H customer_demographics | 6.25 / 12.5 / 25 / 50% | same | same | 100 |

Key prefixes select the same absolute number of tickets/orders at every SF, so their fraction falls
∝ 1/SF while rows returned stay similar. Date windows are SF-invariant in fraction. `customer_demographics`
has the same 1,920,800 rows at every SF.

## Capture outcome

| SF | captured | wall-clock (incl. convert) | Σ statement runtime (latest attempt): 1–99 / 100–131 / 132–163 | first run Σ (1–99) | event log | peak driver RSS / min host avail |
|---|---|---|---|---|---|---|
| 30 | 163/163 (q23 retried) | 04:27–04:44Z, 17.2 min | 932 / 51 / 43 s | 963 s | 481 MiB (2.5× first run's 194 MiB) | 45.5 GB / 15.1 GB |
| 60 | 163/163 | 04:44–05:23Z, 39.2 min | 2189 / 66 / 83 s | 3140 s | 922 MiB (3.8× of 243 MiB) | 51.9 GB / 8.7 GB |
| 100 | 163/163 | 05:23–06:34Z, 70.8 min | 3949 / 98 / 181 s | 2130 s | 2.53 GiB (7.0× of 370 MiB) | 50.9 GB / 9.9 GB |

- **Event logs grow super-linearly with SF.** That fits the named-accumulator effect in plan §5.4,
  where each task-end event carries the row-group map. q9 (15 store_sales scans) alone is 96 MB at
  SF30 and 230 MB at SF60. SF100 stayed under the 10× stop line (3.71 GB). At q10 its projection was
  3.8–4.8 GB, but the late queries are light (DECISIONS.md). There was no OutOfMemoryError in any
  driver log. RSS above the 48 GB heap is JVM off-heap. **Host headroom was under 10 GB at SF60/100**,
  so a larger SF on this build and node would be risky.
- **q23 is still flaky on the fork.** It failed once (SF30 stmt 0, the same `Decimal.toBigDecimal`
  NPE as the first run) and was retried once, after SF100, with both statements ok. SF60 and SF100
  passed on the first try. The earlier failed row remains in `sf30/capture/queries.csv`; the
  converter uses the latest row per statement.
- **Referenced tables with no row groups read** (the AQE-on decision, as in the first run): 61 and 69
  at every SF, plus 16 at SF30/60.
- SF100's 1–99 runtime (3949 s) is higher than the first run's (2130 s), while SF60 is lower. Runtime
  is not a result of this experiment, and row groups read are unaffected.

### Pruning outside the authored queries (`sf<N>/pruning.json`, `CHECKPOINT_SF30.md`)

- **Queries 1–99 still read every row group of every table they touch.** The exceptions are runtime
  effects, not footer statistics. q16 at SF30/60 skips the trailing `catalog_sales` row groups (SF30
  321/338, SF60 661/676; their `cs_ship_date_sk` min ≥ 2452602) and part of `catalog_returns`. q16
  has no literal on these columns, the first run also read only part of `catalog_sales` (10/23,
  41/46), and at SF100 q16 reads everything in both runs. The cause was not identified. q69 at SF60
  reads `customer_demographics` 8/16 and `web_sales` 8/338; q69 is one of the AQE-skipped queries.
  `customer_demographics` and `customer` do **not** prune in any original query, contrary to the
  plan's expectation (see the order profile above).
- **Queries 100–131: no fact table ever prunes.** 112–115 skip `customer` row groups (SF30 1/1/2/3 of
  4; SF100 1/1/2/3 of 16). At SF100 only, 100–111 skip one of `item`'s two row groups, because
  `*_item_sk < N` prunes `item` itself. That is item (b) of the plan, now closed: they were captured,
  and they prune exactly as predicted.

## Results (query_set_131, N=1500, seed 42, 100 trials) — `sf_comparison.json`, `sec44_after/`

Before/after tables against the first run: `before_after_first_run.md` (CSV `before_after_first_run.csv`).

- **Full and Equal at table and column granularity are still byte-identical across SFs** (they
  depend only on referenced columns). They *do* change against the first run, because the query set
  changed (131 queries, 32 of them authored). Zipf median, table/Equal: `date_dim` 19.42 → **20.72%**,
  `store_sales` 16.04 → **11.96%**, `item` 12.54 → 14.82%, `store` 6.20 → 4.08%, `customer` 4.36 → 4.50%.
  Table/Full: `date_dim` 18.17 → 19.18%, `store_sales` 14.13 → 11.22%.
- **Rankings across SF are stable, and more so at row-group granularity.** Spearman of per-table
  median share, zipf, first run → rerun: rowgroup/equal 0.950–0.986 → **0.962–0.990**, rowgroup/full
  0.964–0.995 → 0.989–0.997, rowgroup/frequency 0.956–0.990 → 0.993–0.998, table/cardinality
  0.981–0.994 → 0.992–0.998, column/cardinality 0.992–0.998 → 0.990–0.997. Normal: rowgroup/equal
  0.894–0.972 → 0.978–0.995.
- **Strategy ordering per table** (Full/Equal/Cardinality) is the same at every SF for 22/23 tables
  under zipf. It differs only for `catalog_returns` (SF30 Full > Cardinality > Equal; SF60/100
  Cardinality first). Normal: 24/24 (the first run had zipf 24/24 and normal 23/24, `catalog_returns`).
- **Granularity ordering per table** (Equal) under zipf differs across SF only for `catalog_returns`;
  the first run's exception was `inventory`. Under normal it differs for `customer_demographics` and
  `web_returns`.
- **VDI vs frequency.** There are no flips at table or column granularity. At row-group granularity
  there is one flip, `inventory` at SF100 (zipf and normal); the first run's was `catalog_returns`
  at SF100.
- **Row-group magnitudes no longer drift with SF for `store_sales`.** The rerun's row-group shares
  at SF30/60/100 are **40.4 / 40.8 / 40.6%**, against 48.1 / 50.1 / 50.6% in the first run. Dimension
  shares still shrink with SF, from a lower start: `date_dim` 1.34 / 1.00 / 0.64% (first run
  3.48 / 2.11 / 1.29%). Tables whose row-group count grows with SF gain share: `customer`
  1.27 / 1.69 / 2.21% (4 → 16 RGs), `inventory` 3.23 / 3.43 / 4.01%, `customer_demographics` falls
  1.81 / 1.33 / 0.92%. With 128,000-row groups, every table above 128k rows now has several row
  groups, so Equal's split across row groups no longer favours the facts only.
- **Cardinality** (zipf, table): `store_sales` 56.8 → **42.1%** at every SF; `catalog_returns`
  1.0 → 2.2–2.5%; `inventory` 1.7–2.3 → 3.6–4.1%.

### Query-history sweep (R2D8/R2D13) — `history_sweep/sf<N>/`, raw points in `sweep/`

- **All-tables ranking vs N=2000, per-seed minimum ρ:** N=250 **0.957–0.958** at every SF (first run
  0.951), N=500 0.986–0.989 (first run 0.965–0.976), N=1500 0.994. The supporting sentence ("at 250
  queries ρ ≥ 0.95 at every seed and SF") now holds with more margin.
- **On the 6 fixed figure tables** (`FIGURE_TABLES_TPCDS`, the same set as in the first run): ρ is
  0.771 at N=100, 0.886 at N=250 and 0.943 from N=500 (one adjacent swap). The first run had 0.943
  from N=250. So **for the figure tables, N=250 is no longer enough at every seed; N=500 is.**
- **§4.4 quantities vs N=2000:** the `date_dim` Full and Equal shares stay within ±0.005 from N=500
  onward, and the frequency share from N=1000. The access fraction still moves by up to 0.0087 at
  N=1500, so the script's "all within ±0.005 from N=X" line only holds from N=2000 (first run: N=1500).
- **Prose claims:** every ordering claim holds at all 30 points (5 seeds × 6 N) at every SF. The July
  "date_dim 15–18%" range claim fails at 30/30 (the first run held it at 1/30; date_dim is now
  ~19–21%).
- **Box spread does not come from history size:** the mean 95% CI half-width is 0.0047–0.0049 at
  every N (first run 0.0047–0.0048).

### Number of task-value draws — `num_draws/`

The same method and criteria as the first run (`SEC44_RERUN_NOTE.md` §3), on the same 6 figure tables.

| | first run | rerun (SF30 / 60 / 100) |
|---|---|---|
| C1: MCSE of every displayed median ≤ 0.5 pp at K=100 | fails for 3/30 (store_sales Card 1.35, RG 1.25, Col 0.60 pp) | **fails for 3/30**: store_sales RG 1.90/1.85/1.81, Cardinality 1.87/1.87/1.83, Column 0.63/0.62/0.63 pp; worst of the rest 0.50/0.49/0.48 |
| C1 at K=1000 | passes (0.44 pp) | **still fails for 2/30**: store_sales Cardinality and RG 0.61–0.65 pp (rest ≤ 0.20) |
| C2: orderings with gap ≥ 1 pp reproduced in ≥ 95% at K=100 | passes, worst 98.2–99.1% (43 orderings) | **passes**, worst 100 / 99.95 / 100% (43/43/44 orderings) |
| C3: ρ ≥ 0.95 vs pool in ≥ 95% | passes (100%) | passes (100%) |
| MCSE ∝ K^slope | −0.51 | −0.508 / −0.511 / −0.509 |
| independent blocks / bootstrap | 0.91–0.94 | 0.94 / 0.93 / 0.94 |
| paper's seed-42 draws, max abs z | 2.79 | **3.33 / 3.39 / 3.31** |
| MCSE as % of box IQR at K=100 | 7.5–9.6% | 7.8–10.0% |

Conclusion: 100 draws still supports every ordering and ranking the figures argue. The
`store_sales` Cardinality and Row-Group medians are noisier than before, at about ±3.7–3.8 pp
(2 × MCSE) at K=100. Even K=1000 no longer gets them under 0.5 pp. The paper's seed-42 draws sit
further from the pool medians (|z| up to ~3.4). This is worth checking before quoting those two
numbers.

### Candidate paper figures — `paper_figs/`

`select_display_tables.py` picks **date_dim, item, store_sales, customer, store, catalog_returns,
inventory** (7 tables). The script forces date_dim, store_sales, store and customer and adds item,
catalog_returns and inventory to cover every pattern. Figures: `paper_figs/sf<N>/zipf_{table_divide,granularity}_compare_normalized.pdf`
(`graph_comp_oracles.py --distro zipf --tpcds-only --ylim 1.0 --tables <set>`; the first run's flags
for these were not recorded) and `paper_figs/convergence/convergence_sf<N>.{pdf,png}` + summary CSVs.
Full-set figures at `--ylim 1.0`: `sec44_after/figs_sf<N>/`. Per-SF numbers:
`sec44_after/sec44_numbers_spark_sf<N>.csv`.

## Known caveats (carried forward where they still hold)

- **AQE on**: when a join side is empty at runtime, the other side's scan never runs, so its row
  groups are not recorded (61, 69, and 16 at SF30/60). This still holds. Partial reads in q16/q69 are
  runtime effects too.
- **q23 flakiness** on the fork: still present (1 failure in 3 SFs). It fails loudly and was retried.
- **Column parser**: the post-`0834aa1` whole-identifier parser is used throughout. The first run's
  substring false-credit caveat does not apply to these outputs.
- **`--tpcds-only` drops `lineitem`** from the figure table set (open question from the first run).
  The display set is now produced by rule (above).
- **Template F** prunes coarsely (≥ 17.7% of `catalog_returns` at its smallest level). It is the only
  template whose levels miss the plan's ~1 RG / 10% targets.
- **This SF30 is not the first run's SF30, and neither is the paper's.** The query set changed
  (131 queries, 32 authored and row-group-selective) along with the row-group size. §4.4 text needs
  updating (`REVISION_R2D7_RG128K.md` §11): "99 TPC-DS queries" → 131; "store_sales's 29 at SF30" →
  676; and the R2D14 sentence "Because TPC-DS queries read every row group…" must be rewritten.
  Queries 1–99 still read every row group; only the authored ones prune.
- Page sizes under the RG_ROWS writer were not measured. If page-level statistics matter later,
  check them.

## Wall-clock per stage (UTC, 2026-10-21)

| stage | time | note |
|---|---|---|
| setup, script parameters, SF1 smoke test | 02:01–02:07 | smoke convert+verify 53 s |
| Parquet SF30 / SF60 / SF100 | 02:07–02:29 / –03:12 / –04:24 (**2 h 17 min**) | convert 1284 / 2582 / 4308 s (first run 1088 / 2472 / 4217 s), verify 6 / 19 / 26 s |
| profile + author + DuckDB pre-check | during conversion | light jobs only (pyarrow footers, DuckDB 6 GB cap) |
| Spark acceptance, SF30 | 04:25–04:27 (2 min) | 8 bases + 32 authored |
| capture + convert, SF30 / 60 / 100 | 04:27–04:44 / –05:23 / –06:34 (**2 h 07 min**) | 17.2 / 39.2 / 70.8 min |
| q23 retry SF30 + reconvert | 06:35–06:37 | |
| query set + VDI (3 SFs concurrently) | 06:37–06:43 (5.4 min) | 146 / 222 / 323 s |
| compare_sf, figures, summaries | 06:43 (25 s) | |
| history sweep (3 SFs concurrently) | 06:43–07:53 (70 min) | 1882 / 2834 / 4186 s |
| draws pools (concurrently with sweep) | 06:43–07:36 | 1476 / 2158 / 3200 s |
| draws analysis, display set, paper figures | 07:53–07:58 (5 min) | draws 208 s |
| **end to end** | **02:01–07:58, ~6 h** | plan estimate ~6 h concurrent |

## Code (`~/value_of_data/value-of-data-metric` @ `4416586`, uncommitted)

Tracked diff sha256 `c76eef58…7a29` (`provenance/value-of-data-metric_tracked.diff`). Untracked
files: `provenance/value-of-data-metric_untracked.tgz`. Every edit is an opt-in parameter whose
default reproduces the first run:

- `tpcds_datagen/convert.py`: `PARQUET_ROOT` (default `/mnt/tpcds/parquet`) and `RG_ROWS` (default
  unset = 128 MiB). `WRITER_CONF` is applied as `spark.hadoop.*` and as write options, and recorded
  in `effective_settings`.
- `tpcds_datagen/verify.py`: honours `PARQUET_ROOT` (via `convert.OUT`); with `RG_ROWS` set it
  asserts exact row-group sizes.
- `tpcds_datagen/make_notes.py`: honours `PARQUET_ROOT`; prints the real writer settings when
  `RG_ROWS` is set (the old 128 MiB sentence otherwise).
- `tpcds_datagen/run_sf.sh`: honours `PARQUET_ROOT`.
- `oracle/scripts/run_spark_sf.sh`: `PARQUET_ROOT`, `RESULTS`, `QUERY_DIR`, `QUERIES` (default
  `1-99`, used by capture's default range and convert's `--queries`); `RESULTS` is passed into the
  `common` heredoc.
- `oracle/scripts/run_capture_all.sh`: SF-list argument (default 30 60 100), `RESULTS`/`QUERIES` passthrough.
- `oracle/scripts/draws_convergence.py`: `--query-set` (default: `<results>/common_completed_sf30_60_100.json`).
- New: `oracle/scripts/{rg_order_profile.py, author_rg_selective.py, rg_selective_accept.py,
  rg128k_checkpoint.py, rg128k_before_after.py}` and
  `spark-lineage-api/benchmarking/tpcds_queries_spark/query132–163.sql` (1–131 untouched).
- Run scripts (not in the repo): `run_scripts/{acceptance.sh, capture_all.sh, downstream.sh,
  checkpoint_md.py, eventlog_by_query.py}`.

## Layout of `/mnt/tpcds/results_rg128k`

`DECISIONS.md` (every judgement call) · `CHECKPOINT_SF30.md` · `authored_queries_by_sf.md` ·
`before_after_first_run.{md,csv}` · `sf_comparison.json` · `query_set_131.json` ·
`common_completed_sf30_60_100.json` (all 163) · `sf<N>/{capture,eventlog,logs,values,vdi,figs}`, as in
the first run · `sf<N>/{pruning.json, rg_selective_acceptance.json}` · `sf30/{order_profile.csv,
rg_selective_calibration.json, acceptance/}` · `sf{60,100}/rg_selective_predicted.json` ·
`sec44_after/` · `history_sweep/` · `sweep/` (raw points) · `num_draws/` · `draws_pool/` (large) ·
`paper_figs/` · `capture_monitor.log` (driver RSS / event-log every 30 s) · `capture_all.log`,
`downstream.log`, `logs_downstream/` · `provenance/`.

Bring-back target (plan §10, laptop pulls): `value-of-data-metric/r2d7_rg128k_results/`, laid out
like `r2d7_results/`. Raw Parquet, event logs and `draws_pool/` stay on the node. `r2d7_results/`
was not touched.
