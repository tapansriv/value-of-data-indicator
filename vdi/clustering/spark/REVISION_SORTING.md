# Sorting experiment on Spark — R2D14, R3W1, R3D1 + R2W4, R2D13

Plan for rerunning the §6 "Data Clustering" (sorting) experiment with Spark as the query
engine, and for replacing "2 tables × 2 columns feels reasonable" with a measured sweep.
Decisions below were made with Tapan on 2026-10-07. This copy (`clustering/spark/` on `main`;
developed on branch `sorting-spark`, merged at `c334627` and deleted 2026-10-08) is canonical; how to run it is in `NODE_RUNBOOK.md`.

## Decisions

| Question | Decision |
|---|---|
| Engine | Spark directly — no DuckDB pilot of the sweep. One Chameleon node Tapan already has up, TPC-DS SF30 Parquet already built. |
| Node count | One node is enough: bytes read doesn't depend on node count. Say so in §6; the multi-node argument belongs to placement (runtime). |
| VDI source | SQL-parsed column sets in `clustering/value_generation/tpcds_columns_in_queries.json` (verified clean). Column-level decisions depend only on the SQL text, so Spark makes the same choices as DuckDB. **Spark must run the same query text as the DuckDB run** (`clustering/queries/tpcds/`), not `spark-lineage-api/benchmarking/tpcds_queries_spark/` (a different query-generator stream; 19/99 queries reference different columns). |
| Row-group counter | Not needed. VDI is column-level and decided in advance, so the fork's row-group hook may be bypassed. |
| Layout mechanism | Iceberg (see below), so Spark can skip data using filters that arrive through joins. |
| Sort order | Lexicographic (c1, c2) is the main result, comparable to DuckDB. Z-order is a pilot-only arm, out of interest. |
| Sweeps | Number of tables k until the VOD–Frequent utility gap vanishes; number of columns c ∈ {1, 2, 3} at k = 2. |

## Layout

For each chosen (table, c1, c2):

- An Iceberg table **partitioned by a transform of c1**, so dynamic partition pruning (DPP)
  turns join-derived filters into file skipping. Plain Spark applies Parquet min/max
  statistics only to literal predicates, and TPC-DS fact tables are mostly filtered through
  joins (e.g. `date_dim` → `ss_sold_date_sk`).
- **`WRITE ORDERED BY (c1, c2)`** within partitions, giving tight file-level stats in Iceberg
  manifests and row-group stats in the Parquet files, for literal predicates.

Partition transform rule, fixed and identical for every strategy. P = min(32, the table's
row-group count in base), so no partition is finer than a base row group and a layout gains
no pruning granularity the base lacks (Tapan, 2026-10-08; P = 32 alone split customer's
4 row groups into 33 partitions of ~13k rows):
- `identity(c1)` if approx NDV(c1) ≤ P
- `truncate(⌈range/P⌉, c1)` for integer **and decimal** columns (keeps range locality; for
  decimals the width is in units of 10^-scale, as Iceberg truncates the unscaled value).
  Truncation aligns to multiples of the width, not to min(c1), so a table gets P + 1 or
  P + 2 partitions, plus one for nulls. Decimals were `bucket` until 2026-10-08 (Tapan:
  hashing gave Random's money-column picks no range locality).
- `bucket(P, c1)` for strings, dates, timestamps (none occur as c1 with NDV > P in the
  current manifest)
- no partitioning for other types (recorded in the build stats)

A complete layout whose stored partition expression no longer matches the rule is rebuilt.

Layouts are written in exact chunks like the base (2026-10-08): rows sorted by (partition,
c1, c2), each partition cut into files of exactly 32 row groups of 128,000 rows; only a
partition's last file is partial. Iceberg's own range-distributed write sized files by
shuffle bytes (~1.9x the zstd Parquet bytes), giving ~14 row groups per file.

**Baseline:** all 24 tables as Iceberg, unpartitioned and unsorted. Row groups hold
**exactly 128,000 rows**, as in the DuckDB run: Iceberg's writer checks the row-group size
only every N records, so a 1-byte size threshold with the check interval pinned to 128,000
flushes at exactly that count (verified in the smoke test). Rows stay in source (dsdgen)
order, cut into contiguous files of exactly 32 row groups, so only a table's last row group
is partial (verified against the source on the node, 2026-10-07). Layouts reuse the
per-table properties, whose target file size is the measured size of 32 row groups.

*Fixed on the node (2026-10-07):* the first SF30 base build wrote straight from Spark's
input splits, giving one file per source row group (9–27 row groups per file) and a partial
row group at the end of every file (1,594 row groups instead of 1,569). Not seen in the
SF0.1 smoke test, where each source fit in one split. Rebuilt with `build-base --rebuild`.
Also on the node: the R2D7 source follows the official DSGen 4.0.0 DDL, which names two
columns differently from `tpcds_schema/` (the DuckDB run, which the queries and column sets
follow): `customer.c_last_review_date char(10)` vs `c_last_review_date_sk integer` (query 30
failed to plan), and `store.s_tax_precentage` (DDL typo; no query uses it). The base build
renames both and casts the first to int (`SCHEMA_FIXES` in `build_iceberg.py`); values and
nulls verified equal to the source. 99/99 queries then plan.
Note also: dsdgen order already clusters some columns in the base — a median row group
spans ≤0.6% of the range of `cs_sold_date_sk`, `inv_date_sk`, `ss_ticket_number`,
`cs_order_number`, `ws_order_number` — so sorting catalog_sales or inventory on date has
little left to gain over the base.
Each layout lives in its own namespace (`<layout>_<mode>`) of a local Hadoop catalog; the
runner binds table names through temp views, which Spark inlines.

Spark settings: `spark.sql.optimizer.dynamicPartitionPruning.reuseBroadcastOnly=false`; keep
filter pushdown on; Iceberg 1.8.1 (`iceberg-spark-runtime-3.5_2.13`); `local[*]`. The
runner records the full conf with every invocation. Queries run with `collect()`: `show()`
adds `LIMIT 21`, which can stop scans early. AQE stays on (Spark's default, as in R2D7)
**except `AQEPropagateEmptyRelation`**, which is excluded: when a join side turns out
empty, that rule cancels running stages, so bytes read depended on timing (smoke test: one
query varied 69% between identical runs, and 20 queries recorded no scans). With it
excluded, 20/20 of those queries read identical bytes across runs. Mention this in §6.

**Listener:** the column/table listener (`LineageAPI.UsageCollector`) is attached to every
query. It only recognized v1 file scans, so on Iceberg tables it logged nothing; it now also
matches DataSource V2 relations, and accepts the `collect` action as well as `head`
(`spark-lineage-api/listener_versions_new/LineageAPI.scala`, 2026-10-07). Its output is
cross-checked against the SQL-parsed column sets, not used for ranking.

## Finding: half of the published budget was spent on no-op tables (2026-10-07)

At SF30 with 128k-row row groups, only **10 of 24 tables span more than one row group**:
store_sales (676), catalog_sales (338), inventory (245), web_sales (169), store_returns (68),
catalog_returns, web_returns (17), customer_demographics (16), customer (4),
customer_address (2). Sorting a single-row-group table cannot skip anything.

The current ranking ignores size, so every published k = 2 configuration sorted exactly
**one** table that could matter:

| Assignment | VOD | Frequent | Random |
|---|---|---|---|
| Constant, V50 | store_sales (+ date_dim) | store_sales (+ date_dim) | store_returns (+ household_demographics) |
| V100, V500, V1000 | web_sales (+ item) | store_sales (+ date_dim) | store_returns (+ household_demographics) |

(Parenthesized tables are single row group: no-ops.)

**Decided (Tapan, 2026-10-07):** restrict every strategy's ranking to tables that span more
than one row group — the only tables that can benefit from row-group or Iceberg file
pruning. Gives the k-sweep a natural upper bound, **K = 10**. Not chosen: a budget in bytes
rewritten (knapsack). `date_dim`, `time_dim` and `household_demographics` don't grow with
scale factor, so this holds at SF60/SF100 too.

New k = 2, c = 2 configurations under the filter:

| Assignment | VOD | Frequent | Random |
|---|---|---|---|
| Constant | store_sales, catalog_sales | same as VOD | web_returns, catalog_sales |
| V50 | store_sales, web_sales | store_sales, catalog_sales | ″ |
| V100 | web_sales, store_sales | ″ | ″ |
| V500, V1000 | web_sales, customer | ″ | ″ |

(Random now draws from the 10 eligible tables, so its picks differ from the published ones.)

With the filter, VOD and Frequent rank identically under Constant at c ≤ 2 (VOD reduces to
LFU, as the paper says).

The sweep grid is k = 1..10 at c = 2, plus c = 1, 2, 3 at k = 2, for 5 assignments × 3
strategies: **180 configurations needing 36 distinct layouts** and 55 distinct sets of
sorted tables (`manifest.json`). Measured directly (see Execution), that is ~4,560 query
runs plus the 99-query No Sort run; k = 2, c = 2 alone is 4 sets, 256 runs.

## Execution: each configuration measured directly (Tapan, 2026-10-08)

As in the paper: a configuration's chosen tables are sorted (all of them at once), the
queries run, and the bytes observed. Nothing is estimated, so nothing needs validating.

- Configurations that sort exactly the same tables on the same columns share one run
  (`make_runs.py configs`): every chosen table bound to its layout at once, executing every
  query that reads at least one of them. k = 2, c = 2: 15 configurations, 4 groups.
- `nosort`: all 99 queries on base, run fresh in the same results file.
- A query that reads none of a configuration's sorted tables is not rerun; its bytes are the
  No Sort run's (its plan never touches a sorted table; verified: the manifest's
  queries_by_table equals the tables each query scanned at runtime, for all 10 eligible
  tables).
- `<group>_rep`: Frequent's groups run twice; sorted layouts must read identical bytes.
- Superseded (2026-10-07 plan, never used for results): measuring one sorted table at a time
  and adding the per-table savings, with a few configurations run directly to check the
  sum. That gave estimates, not measurements. The partial run of it (`layouts_ps.jsonl`,
  76 base queries) was stopped and is not used.

Outputs: `configs_ps.jsonl`; `analysis/configs_ps_<metric>.csv`;
`analysis/paper_ps_k<k>_c<c>/profiles_combined_<0..4>.csv` in the format of
`clustering/src/analyze.py`, plus `workload_value.pdf` (bytes, as in the paper) and
`workload_value_rows.pdf` from `plot_workload_value.py` (that script's plot code).

## Pilot (step 0, about half a day on the node)

On `store_sales`, using the queries that touch it:

| Arm | Layout |
|---|---|
| A | Iceberg baseline (unsorted, unpartitioned) |
| B | Iceberg sorted (c1, c2), unpartitioned |
| C | Iceberg partitioned by transform(c1) + sorted (c1, c2) |
| D | Iceberg partitioned by transform(c1) + Z-order (c1, c2) |

Questions it must answer:
1. **Does DPP fire?** Check `EXPLAIN FORMATTED` for `dynamicpruningexpression`, and Iceberg's
   skipped-file count. (Unverified: Iceberg maps runtime filters through `truncate`/`bucket`.)
2. **Which bytes metric?** Iceberg reads through Spark's DataSource V2 path, not the
   file-scan path. Use Spark's `bytesRead` if populated; otherwise Iceberg's scan metrics, or
   the per-process `rchar` counter in `/proc/<pid>/io`. Pick before the sweep.
3. **Does partitioning pay?** If B ≈ C, drop the partition rule.
4. **Z-order vs lexicographic** (D vs C) — reported for interest; main result stays lexicographic.

### Pilot results (SF30, 2026-10-07) and decisions (Tapan, 2026-10-08)

store_sales on (ss_sold_date_sk, ss_item_sk), 67 queries, vs base. Arms were built with the
earlier range-distributed writer (~14 row groups per file), before exact chunking.

| Arm | task_bytes_read | proc_rchar | DPP fired | size |
|---|---:|---:|---:|---:|
| s (sorted) | +13.4% | +3.1% | 0/67 | 3.82 GB |
| ps (partitioned + sorted) | −36.0% | −38.9% | 56/67 | 3.82 GB |
| pz (partitioned + Z-order) | −34.2% | −38.6% | 56/67 | 4.12 GB |

base 3.07 GB. Determinism base vs base_rep: task_bytes_read and task_records_read identical
in 67/67; proc_rchar within 0.07%; proc_read_bytes depends on the page cache (unusable).
Iceberg scan metrics are computed at planning, before DPP, so they don't see its pruning.

- **Layout mode: ps.** **Metrics: task_bytes_read (paper's measure) and task_records_read
  (rows read; base − layout = rows pruned), both reported.**
- **Base stays in dsdgen order.** Finding: dsdgen writes store_sales grouped by ticket, so
  the per-ticket columns (ticket, customer, cdemo, hdemo, addr, sold_time, store) compress
  very well in base and grow 3–5x once sorted (table +24%). Queries reading them read more
  after sorting (q88, q96 +186% under ps). Reevaluate (e.g. a shuffled base) only if the
  results call for it.
- Sorting alone barely prunes on Spark (scan rows −2.4%): most filters reach store_sales
  through joins, and only partitioning lets DPP use them.

### Assumptions in effect, raised 2026-10-08, not otherwise confirmed

- zstd for base and layouts (Iceberg default in this harness); the DuckDB run's codec is
  unknown. Bytes depend on the codec.
- Spark: `dynamicPartitionPruning.reuseBroadcastOnly=false`, so DPP may run the filtering
  side as a separate subquery; those reads count in task_bytes_read (keep; revisit if
  results look off). AQE on except `AQEPropagateEmptyRelation`. local[*], 48g.
- Inputs: DuckDB query text translated by sqlglot; `tpcds_query_values_custom.csv` columns
  0–4 (Constant, Value 50/100/500/1000; columns 5–6 are unused relics); Random's single
  fixed seed (Tapan: fine).

### Decisions to revisit if the setup needs tweaking (Tapan, 2026-10-08)

Each is the current choice; the alternative is what to try if results call for it.

| Decision | Current | Known effect | Alternative |
|---|---|---|---|
| Partition boundaries | Value-range `truncate`, P = min(32, base row groups) | Skewed columns give uneven partitions, each ending in a partial row group: l029 web_returns (`wr_return_ship_cost`) has 32 row groups vs 17 in base; alignment to multiples of the width adds a partition (l009 customer 5 vs 4). Only Random's k = 2 pair is affected. | Equal-frequency boundaries so every partition is ≥ 1 base row group |
| No Sort order | dsdgen order, as generated | Ticket/order clustering compresses per-ticket columns well; sorting grows them 3–5x (store_sales +24%), so some queries read more after sorting | Randomly shuffled base |
| DPP reads | `reuseBroadcastOnly=false`; DPP subquery reads count in task_bytes_read | A cost the DuckDB run did not have | Revisit if results look much worse than expected |
| Random | One fixed seed | One draw; could be lucky or unlucky | 2–4 more seeds at k = 2 (~20–40 min each) |
| Codec | zstd for base and layouts | DuckDB run's codec unknown; bytes depend on it | Match the DuckDB codec if comparing across engines |
| Decimal partitioning | `truncate` (switched from `bucket`, 2026-10-08) | Range locality for Random's money columns | — (decided) |
| P cap | min(32, base row groups) (2026-10-08) | Small tables no longer split below a row group (except as above) | — (decided) |

## Results contract

- New results go next to the DuckDB ones; never overwrite them. Every result file records
  seed, k, c, strategy, value assignment, the Spark/Iceberg config and table settings.
- Plots regenerate from raw results.
- Utility metric unchanged: Σ value(q) · bytes_plain(q) / bytes_strategy(q).
- Paper: k = 2, c = 2 figure as in §6. The k = 1..10 (c = 2) and c = 1..3 (k = 2)
  configurations, if run, are measured directly as well (55 distinct table sets, ~4,560
  query runs) and go in the cover letter.

## Known issues to carry

- **Published "No Sort" baseline is actually Random.** `clustering/src/rewrite_queries.py`
  wrote `rand_sql` into `tpcds_plain_part/` (since `ca0eb3f`); 27 "plain" queries read Random's
  sorted tables. **Fixed 2026-10-07** and `tpcds_plain_part/` regenerated (27 files lose the
  Random paths; 9 more differ only in sqlglot formatting, verified equivalent). The profiles
  in `clustering/data/plain/` predate the fix. If the DuckDB numbers stay as a cross-engine
  check, rerun the DuckDB plain baseline and the DuckDB configurations too, since the
  eligibility filter changes them (`rank.py --multi-rowgroup-only --out ...`). Optional; not
  part of the node runbook.
- **§6 wording:** "a Parquet file with 32 row groups" — `cluster.py` writes multiple files of
  32 row groups each (store_sales has 676 row groups).
- **Mechanism differs by engine:** DuckDB used sorted row-group stats only; Spark uses
  partitioning + sort. Say so: "each engine gets the layout it can exploit."

## Code state

- `clustering/src/rank.py` refactored (2026-10-07): `rank(value_iter, num_tables, num_cols)`
  plus `--num-tables/--num-cols/--out`. Defaults reproduce `ranked_tbls_{0..6}.json` exactly
  (verified).
- Eligibility filter: `rank(..., multi_rowgroup_only=True)` / `--multi-rowgroup-only`. Off by
  default so the published configurations stay reproducible; **the revision runs must pass
  it**. Row counts come from `clustering/value_generation/tpcds_sf30_row_counts.json`,
  copied from `r2d7_results/sf30/tpcds_cardinality.json`. `run_phase.sh check-source`
  confirms them on the node.
- Harness in `clustering/spark/` (2026-10-07): `translate_queries.py` (99/99 DuckDB queries
  → Spark SQL via sqlglot), `plan_layouts.py` → `manifest.json`, `build_iceberg.py`,
  `make_runs.py`, `runner/` (`SortingRunner`, Scala), `analyze_sweep.py`, `run_phase.sh`.
- Smoke test (laptop, TPC-DS SF0.1 from DuckDB's dsdgen, 4k-row row groups, P = 8): setup,
  build-base, explain (99/99 plan on Spark), build-pilot and pilot (367 executions, 0
  errors) ran end to end; `analyze_sweep.py` sweep/validate paths (since removed)
  exercised on synthetic data. Mechanics confirmed, **not results** (SF0.1 is too small to mean anything):
  Spark task `bytesRead` is populated for Iceberg scans; DPP fires through Iceberg's
  `truncate` partitioning (56/67 store_sales queries for `ps`, 43/67 for `pz`, 0 for `s`);
  the listener logs Iceberg scans and its columns match the SQL-parsed sets for all 99
  queries; `proc_rchar` needs Linux `/proc` (0 on macOS); the AQE fix above.
- Under Constant, VOD and Frequent differ in sort columns for some tables beyond the top
  few (e.g. store_returns): VOD divides each query's value equally among its columns,
  Frequent counts accesses. Existing method, not a bug, but "VOD reduces to LFU under
  Constant" holds for the top tables only.

## Second workload arm: Redbench IMDb — R3D4 (added 2026-10-07)

Tapan decided 2026-10-07 to answer **R3D4** (skewed/real workload) on the *sorting* experiment
rather than placement. Sorting decides over columns — 26 distinct filter columns with a long
tail, so the decision stays discriminating — while placement decides over tables, where 4 of 20
take ~89% of reads, and IMDb is only ~1–1.5 GB as Parquet, too small for a credible storage
hierarchy.

**Where it is.** `redbench_imdb/` in the **main** checkout: `queries/q001..q415.sql` (415
distinct SELECTs), `stream.csv` (24,881 executions in real arrival order with real
`arrival_timestamp` / `exec_ms` / `mbytes_scanned` / `read_tables`), and a README carrying full
provenance, measured skew, and the two Parquet download routes. **It is uncommitted on `main`,
so it is not visible in this worktree yet** — commit and merge forward before the harness can
reach it.

**What it is.** Redbench (VLDB'26, arXiv 2511.13059) replays a real Amazon Redshift access trace
(Redset) onto a benchmark: each real query's scanset is matched to a benchmark query, emitted at
the real arrival timestamp. Real: which tables are touched, order, arrival times, repetition
structure. Synthetic: the SQL text (JOB/CEB over IMDb) and the data. Extracted from their
published `paper_workloads/matching/workload.csv` (OSF) — support benchmark `imdb`,
`join` matching, provisioned cluster 186 / database 8.

**Measured skew.** Top 10 distinct queries = 92.2% of executions; hottest fires 7,825 times; 30
distinct table-sets; 6,405 distinct `exact_repetition_hash`. Table reads: `title` 22.8%,
`keyword` 22.3%, `movie_keyword` 22.3%, `movie_info` 21.9%, tail <2%. Filter columns:
`title.production_year` 30.3%, `keyword.keyword` 29.6%, `movie_info.info` 29.3%, then 23 columns
at ≤1.9%.

**Design — one experiment, not two.** Sweep the correlation ρ between task value and query
frequency, ρ ∈ {1.0, 0.5, 0.0, −0.5}:

- ρ = 1: value aligns with frequency. Both pick the three hot columns. Shows VDI costs nothing
  when frequency is already a good signal.
- ρ ≤ 0: value concentrates in the 23-column tail, which sits on *different* tables. VDI should
  separate from frequency on bytes scanned.

One figure, gap ≈ 0 at ρ=1 widening as ρ falls. Also covers the "When does VDI help?" thesis in
`REVISION_PLAN.md` (R1W3, R1E4, R2W1, R2D5, MW2).

### Four things from this harness that bear on it

1. **Row-group eligibility is the gating check.** The finding above — only 10 of 24 TPC-DS tables
   span >1 row group at SF30 — needs repeating on IMDb Parquet before any k/c budget is set.
   Unverified hypothesis: `keyword` may be a single row group, making the #2 filter column a
   no-op, while the valuable tail sits on `cast_info` / `name` / `movie_companies`, which are
   large. If so that is a *finding* (frequency over-weighting a table where sorting cannot help)
   and it strengthens the ρ ≤ 0 arm. Needs an IMDb row-count file alongside
   `tpcds_sf30_row_counts.json`, and `--multi-rowgroup-only`.
2. **The ρ=1 arm is not automatically a null result.** Per "Code state" above: under Constant,
   VOD and Frequent already differ in sort columns beyond the top few, because VOD divides each
   query's value equally among its columns while Frequent counts accesses. So the honest ρ=1
   claim is "VDI matches frequency on the tables that matter," not "VDI reduces to LFU." State
   it that way.
3. **`translate_queries.py` should carry the IMDb SQL.** It already does DuckDB → Spark SQL via
   sqlglot for 99/99 TPC-DS queries. The IMDb queries are vanilla comma-join SELECTs with
   `LIKE` / `IN` / `MIN()`, so they should need less work than TPC-DS did — but run them through
   the same path rather than hand-editing.
4. **Column sets: do not reuse the TPC-DS parser as-is.** `oracle/scripts/tpcds_parse_columns_from_query.py`
   is TPC-DS-specific and had a substring bug (`d_date` credited inside `d_date_sk`) fixed
   2026-10-07; use the whole-identifier version if any of it is borrowed. The README's column
   shares came from a one-off heuristic regex and are indicative only — re-derive the
   authoritative column sets through the SQL-parsed path validated against the listener, as was
   done for the 99 TPC-DS queries.

### Row-group eligibility, measured 2026-10-07 (local, DuckDB)

IMDb loaded from the CWI CSVs (all 21 tables, clean load, no dropped rows) and exported to
Parquet. Row-group counts below are at **the harness setting `RG_ROWS=128000`**; measured at
DuckDB's 122,880 default and rescaled, the two agree within 4%.

**14 of 21 tables span >1 row group — better substrate than TPC-DS SF30, which was 10 of 24.**

| table | rows | row groups | | table | rows | row groups |
|---|---|---|---|---|---|---|
| `cast_info` | 36,244,344 | **284** | | `aka_name` | 901,343 | 8 |
| `movie_info` | 14,835,720 | **116** | | `aka_title` | 361,472 | 3 |
| `movie_keyword` | 4,523,930 | 36 | | `company_name` | 234,997 | 2 |
| `name` | 4,167,491 | 33 | | `complete_cast` | 135,086 | 2 |
| `char_name` | 3,140,339 | 25 | | `keyword` | 134,170 | **2** |
| `person_info` | 2,963,664 | 24 | | `movie_link` | 29,997 | 1 |
| `movie_companies` | 2,609,129 | 21 | | `info_type` | 113 | 1 |
| `title` | 2,528,312 | 20 | | `role_type`, `kind_type`, `link_type`, `comp_cast_type`, `company_type` | ≤18 | 1 |
| `movie_info_idx` | 1,380,035 | 11 | | | | |

**The earlier hypothesis that `keyword` would be a single row group is wrong** — it has 2, at
134,170 rows just over the 128,000 threshold. But the spirit survives in a sharper, measured
form:

| filter column | filter weight | row groups |
|---|---|---|
| `title.production_year` | 30.3% | 20 |
| `keyword.keyword` | 29.6% | **2** |
| `movie_info.info` | 29.3% | 116 |
| `cast_info.note` | 1.1% | **284** |
| `name.gender` | 1.3% | 33 |
| `movie_companies.note` | 0.6% | 21 |
| `role_type.role` | 1.7% | **1 — no-op** |
| `info_type.info` | 0.6% | **1 — no-op** |

**This is the mechanism for the ρ ≤ 0 arm, and it is now measured rather than assumed.**
Frequency's #2 pick, `keyword.keyword` at 29.6% of filter weight, has only 2 row groups — at
best a 50% skip, and realistically far less. The low-frequency tail contains `cast_info.note`
with **284** row groups, the most skipping headroom in the schema: ~140× more than frequency's
second choice. So when value decorrelates from frequency, VDI can direct sort budget at a table
where sorting actually pays, while frequency spends it where there is almost nothing to skip.

Two consequences for the run:
- **Keep row groups row-count-pinned.** Under a byte-based target (Iceberg's 128 MB default)
  only `cast_info` and `movie_info` would span >1 group and `title` *and* `keyword` would both
  become no-ops, gutting the experiment. `build_iceberg.py` already forces record-count checks
  with `row-group-size-bytes: "1"`, which is the correct choice here — do not relax it.
- **`--multi-rowgroup-only` must exclude 7 tables**, and three of the workload's filtered
  columns (`role_type.role`, `info_type.info`, `kind_type.kind`) are no-ops on tiny dimension
  tables. They carry real filter weight (1.7% / 0.6% / 0.5%), so a value assignment that
  concentrates there would produce a null result for reasons unrelated to VDI. Steer the ρ ≤ 0
  assignment toward the *large* tail tables — `cast_info`, `name`, `movie_companies` — not the
  dimension tables.

Raw numbers: `scratchpad/imdb/rowgroups_rg128k.txt`; Parquet in `scratchpad/imdb/parquet/`.

### Value generation: six named schemes, validated locally 2026-10-07

`gen_values.py` emits **several named value-assignment schemes**, not one. Tapan's call
(2026-10-07): a single assignment derived from runtime smuggles in "long-running means
valuable", which is an assumption about cost rather than worth and is exactly the sort of
unjustified constant R2W4 objects to. The assignment has to be an *axis*.

Each scheme is an organizational story, and together they span alignment with frequency:

| scheme | story | ρ(value, frequency) | value spread |
|---|---|---|---|
| `constant` | no value information at all | 0.000 | 1× |
| `frequency_aligned` | the queries everyone runs are the ones that matter | **+1.000** | 2608× |
| `tiered` | a CDO names a few critical reports, independent of how often they run | −0.016 | 1000× |
| `independent` | value unrelated to frequency, continuous | −0.002 | 90× |
| `rare_critical` | the rarely-run tasks are the valuable ones — quarterly regulatory report, disaster recovery | **−0.937** | 15× |
| `runtime_proxy` | value ∝ real Redshift execution duration — **labelled comparator only** | −0.231 | 240× |

`tiered` uses 1000 / 100 / 1 as in `custom_values.py`, at 3% / 12% / 85%, mirroring the
three-tier split in `clustering/schema/tpcds_query_tiers.json`. `rare_critical` also answers
the R2W1 / R2D5 / MW2 "important data that is rarely used" thread, so one run serves both.

`--rho R` still gives a continuous Gaussian-copula sweep if a smooth x-axis is wanted.

#### Two findings about `runtime_proxy`, which justify not defaulting to it

1. **It is not neutral.** In this real trace execution duration is *anti*-correlated with
   frequency, ρ = **−0.231** — the frequent queries are fast, the rare ones slow. Defaulting to
   it would have quietly encoded a mild "rare is valuable" prior.
2. **It produces no separation at all.** VDI picks exactly what frequency picks, at every k and
   under both column-candidate rules. The experiment would have returned a null result, and the
   cause would have been the value assignment, not VDI.

Why: accumulated value is Σ (task value × executions), and the dominant query shape runs 7,825
times. Mild misalignment cannot overcome that. Separation needs value to differ from frequency
*strongly* — either in rank (`rare_critical`, ρ = −0.937) or in concentration (`tiered`, 1000×
spread on 3% of queries). **That is the paper's thesis stated precisely: VDI's advantage scales
with the degree of decorrelation, and vanishes smoothly as alignment rises.**

#### Simulated `rank.py` divergence (c=2, eligibility filter on, mean over 10 trials)

Row groups covered by the chosen tables, VDI vs Frequency:

| scheme | all-referenced cols, k=2 | k=3 | filter cols only, k=2 | k=3 |
|---|---|---|---|---|
| `constant` | 56 v 56 | 58 v 58 | 22 v 22 | 138 v 138 |
| `frequency_aligned` | 56 v 56 | 58 v 58 | 22 v 22 | 138 v 138 |
| `tiered` | **196 v 56** | **230 v 58** | **62 v 22** | 127 v 138 |
| `independent` | 88 v 56 | 104 v 58 | 33 v 22 | 138 v 138 |
| `rare_critical` | **136 v 56** | **172 v 58** | **136 v 22** | 138 v 138 |
| `runtime_proxy` | 56 v 56 | 58 v 58 | 22 v 22 | 138 v 138 |

`tiered` separates most (3.5× at k=2), then `rare_critical` (2.4×), then `independent` (1.6×).
The aligned schemes correctly show no table-level divergence. **k=2–3 is the discriminating
budget**; by k≥4 both strategies cover every hot table and the methods converge, which is
`REVISION_PLAN.md`'s constants principle turned into evidence and retroactively justifies the
published k=2.

**Read this table as divergence, not as a win.** "Row groups covered" is a pre-validation proxy
for pruning *potential* that exists only to check the arms separate before node time is spent.
It is not the experiment's metric — bytes scanned is, measured on the node. One cell already
shows the difference: `tiered` at filter-only k=3 has VDI covering *fewer* row groups than
frequency (127 v 138). Divergence is a precondition for a result, not the result.

**Recommended headline scheme: `tiered`** — largest separation, and the most defensible story
organizationally. Report the full set as the sweep.

#### Open method question for Tapan: restrict sort columns to filter columns?

`rank.py` ranks over *all referenced* columns, so join keys dominate: only **2 of 6** chosen
sort columns are filter-predicate columns, and `movie_keyword` is sorted on
`[keyword_id, movie_id]`, both join keys. Defensible, since the layout partitions by a c1
transform precisely so DPP fires on join-derived filters. But among the 9 columns of the
dominant query shape the execution-weighted value is nearly tied (≈10% each), so column picks
inside hot tables are close to arbitrary — under `frequency_aligned` that makes VDI choose
`title[id,title]` while Frequency chooses `title[id,production_year]`, dropping the column with
30.1% of filter weight for no principled reason.

Restricting candidates to filter columns removes that artifact and sharpens `rare_critical` at
k=2 to **136 v 22** (6.2×). It is a method change affecting both workloads, so it is Tapan's
call, not a silent fix.

#### Local artifacts in `redbench_imdb/`

`queries/` (415) · `queries_spark/` (415, sqlglot duckdb→spark, 0 errors) · `stream.csv` ·
`imdb_row_counts.json` · `imdb_schema_registry.json` / `_qualified.json` ·
`imdb_columns_in_queries.json` (all referenced, mean 15.1 cols/query) ·
`imdb_filter_columns.json` (filter only, mean 5.4) · `values/` (6 schemes × trials) ·
`build_column_sets.py` · `gen_values.py`

Column keys are qualified `table.column`: IMDb's 108 table-columns share only **38 bare names**
(`id` is in all 21 tables, `movie_id` in 8), so the TPC-DS pipeline's bare-name keys — which
work only because of its `cc_`/`d_` prefixes — would mis-credit value across tables.
**Boundary note:** ranking then yields sort columns named `title.id`, while SQL/Iceberg needs
the bare `id`; one conversion at that boundary.

Column sets come from sqlglot's AST with alias resolution (415/415 parsed, 0 failures, 0
unresolved references), not regex. `translate_queries.py` gained `--expect` (default 99, so the
TPC-DS path is unchanged and was regression-checked).

## Contingencies — deliberately not applied (2026-10-07)

The TPC-DS run uses the published `rank.py` rule unchanged. Revisit these only if results look
weak:

- **Unique columns as c1** (postponed by Tapan). Primary keys tend to win c1 because every join
  references them; a unique c1 prunes almost nothing under partition-on-c1 + sort-(c1,c2).
  Modelled on IMDb `title`: c1=`id` 1.1% rows skipped vs c1=`production_year` 54.1%. TPC-DS
  `manifest.json`: 4/36 layouts have a PK c1 (`c_customer_sk`, `ca_address_sk`×2, `cd_demo_sk`),
  none with any literal predicate. Fix if needed: non-unique c1, identical for all strategies.
- **Shuffle base tables before building layouts** (postponed by Tapan, decided on the Chameleon
  VM). dsdgen emits `store_sales` in `ss_ticket_number` order, so the unsorted base already has
  locality and compresses better than under other orderings — flattering "No Sort" and possibly
  making sorted layouts compress worse than base. Option: random shuffle of base first. Not now.
  The IMDb arm has the same property: ids were assigned in blocks by source list (actors,
  actresses, crew), so base tables carry load-order locality.
- **Filter-column-only candidates** — raised, not decided; would exclude the original
  `*_item_sk` tier columns, so not recommended.
- When reading results, judge DPP by per-scan file counts, not `dpp_in_plan`.

## IMDb arm — decisions and harness status (2026-10-07; SUPERSEDES the value-generation recommendations above)

**Decided (Tapan):**
- **Value assignment uses the original DE-tier method** (as `clustering/schema/de_query_counts.py`
  did for TPC-DS), not the six named schemes and not runtime. Tier 1 = queries touching
  `cast_info.role_id` (numeric; 345 queries, 5.24% of executions). Tier 2 = remaining queries
  touching `name.gender` / `name.name_pcode_nf` (only 11 queries — effectively two tiers). Values
  r : √r : 1 for r ∈ {1, 10, 100, 1000} (r=100 reproduces the original 100/10/1). Also swept:
  narrow `comp` (movie_companies.note), `rare` (person_info.info), and control `hot`
  (title.production_year, 95% of executions — value aligned with frequency).
  Inputs: `redbench_imdb/make_harness_inputs.py` → `redbench_imdb/harness/`.
- **Net utility:** Σ executions(q)·value(q)·plain(q)/bytes(q), frequency not normalized away;
  normalize to No Sort (Σ executions·value) at the end. `analyze_sweep.py --weighting executions`
  is the IMDb default; TPC-DS keeps `distinct`, as published.

**Harness (uncommitted, on top of the node's 77db8ee):** `WORKLOAD=imdb` switch
(`clustering/src/workload.py`) read by rank.py, plan_layouts.py, make_runs.py, build_iceberg.py,
analyze_sweep.py, env.sh, run_phase.sh; runner reads `base_tables` from the plan (default 24).
TPC-DS regression: `manifest.json` byte-identical; run plans identical apart from `base_tables`;
`rank.py` identical on 10 cases; runner compiles. IMDb: `manifest_imdb.json` = 624 configs,
56 layouts; under direct configuration measurement (02f2560) k=2,c=2 is 10 runs / 2,667 query
executions, k=1..4 is 9,191, all k is 63,599 (don't); net utility verified against a hand computation on
all 624 configs. Steps in NODE_RUNBOOK.md ("Second workload").
