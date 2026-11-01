# Sorting on Spark + Iceberg, TPC-DS SF30 — results (2026-10-07/08, Chameleon node)

Reviewer items R2D14, R3W1, R3D1: §6 "Data Clustering" rerun with Spark executing every
query. Setup, decisions and open choices: `../REVISION_SORTING.md` (see "Execution",
"Pilot results", "Decisions to revisit"). Copied from `/mnt/tpcds/vdi_sort/results/`; the
Spark event logs, listener usage logs and console/driver logs stay on the node.

## Headline: k = 2 tables, c = 2 columns, measured directly

Each configuration's chosen tables are sorted at once, the queries that read them run, and
the bytes are observed; a query reading none of them takes the No Sort run's bytes.
Utility = Σ value(q) · NoSort(q) / sorted(q); No Sort = Σ value(q).

**task_bytes_read** (the paper's measure)

| Assignment | VOD | Frequent | Random | No Sort | VOD vs Freq | VOD vs Random |
|---|---:|---:|---:|---:|---:|---:|
| Constant | 384.907 | 384.907 | 91.243 | 99 | +0.00% | +321.85% |
| Value 50 | 518.207 | 441.907 | 148.243 | 156 | +17.27% | +249.57% |
| Value 100 | 765.273 | 501.907 | 208.243 | 216 | +52.47% | +267.49% |
| Value 500 | 2562.462 | 981.907 | 688.243 | 696 | +160.97% | +272.32% |
| Value 1000 | 5032.129 | 1581.907 | 1288.243 | 1296 | +218.11% | +290.62% |

**task_records_read** (rows read; base − layout = rows pruned)

| Assignment | VOD | Frequent | Random | No Sort | VOD vs Freq | VOD vs Random |
|---|---:|---:|---:|---:|---:|---:|
| Constant | 430.475 | 430.475 | 99.003 | 99 | +0.00% | +334.81% |
| Value 50 | 640.967 | 487.475 | 156.003 | 156 | +31.49% | +310.87% |
| Value 100 | 973.874 | 547.475 | 216.003 | 216 | +77.88% | +350.86% |
| Value 500 | 3425.367 | 1027.475 | 696.003 | 696 | +233.38% | +392.15% |
| Value 1000 | 6754.440 | 1627.475 | 1296.003 | 1296 | +315.03% | +421.17% |

**Total bytes read over the 99 queries** (unweighted): No Sort 97.90 GB; Frequent 52.92 GB
(all assignments); VOD 52.92 (Constant), 70.53 (Value 50, 100), 101.06 GB (Value 500,
1000); Random 108.05 GB.

What drives it:
- Frequent (= VOD under Constant): store_sales + catalog_sales on (date, item). 64 queries
  read less (median 3.5x less; q98 25x, q20 and q08 ~21x, via DPP on date partitions);
  15 read more (compression penalty, below).
- VOD at Value 500/1000: web_sales on (sold_time, web_page) + customer. q90 (value 1000)
  reads 4.7x less (137 MB → 29 MB; 43.4M → 6.7M rows) and contributes 4,741 of 5,032.
  36 other queries read slightly more (median ratio 0.95), so total bytes end +3% over
  No Sort: VOD trades some workload-wide I/O for the valuable query.
- Random: web_returns + catalog_sales on money columns. No query reads less, 43 read more;
  utility is below No Sort.
- Compression penalty: dsdgen writes fact tables grouped by ticket/order, so per-ticket
  columns compress very well in No Sort and grow 3–5x when re-sorted.

Checks: 435/435 query executions ok, no retries. Frequent's group run twice
(`g_l006+l025_ps_rep`): task_bytes_read and task_records_read identical in 80/80 queries.
Listener-logged columns equal the SQL-parsed sets for 99/99 queries. The analysis
re-run with the code at `27b997f` (WORKLOAD switch merged) reproduces every CSV byte for
byte.

## Run

| Run | Queries | UTC (2026-10-08) |
|---|---:|---|
| nosort | 99 | 01:38–01:59 |
| g_l003+l029_ps (Random) | 44 | 01:59–02:13 |
| g_l006+l025_ps (Frequent; VOD Constant) | 80 | 02:13–02:27 |
| g_l009+l034_ps (VOD Value 500, 1000) | 54 | 02:27–02:39 |
| g_l025+l034_ps (VOD Value 50, 100) | 78 | 02:39–02:54 |
| g_l006+l025_ps_rep (repeat) | 80 | 02:54–03:08 |

Code: branch `sorting-spark` at `02f2560` when the run started (`a161d0f` added only a doc
table); the branch was merged into `main` at `c334627` and deleted 2026-10-08, so every SHA
here is reachable from `main`. Spark 3.5.5 (rowgroup-dev fork, `f0c593da`, Scala 2.13.8), Iceberg 1.8.1
(`9ce0fcf`), Java 17.0.20.1, `local[*]`, driver 48g, `spark.speculation=false`,
`dynamicPartitionPruning.reuseBroadcastOnly=false`, AQE on except
`AQEPropagateEmptyRelation`. Full Spark conf: `configs_ps.jsonl.meta.jsonl`.

Data: TPC-DS SF30, dsdgen 4.0.0, seed 19620718 (`/mnt/tpcds/parquet/sf30`, R2D7's
generation; see its DATAGEN_NOTES.md). Base: 24 Iceberg tables, unpartitioned, dsdgen
order, zstd, files of exactly 32 row groups of 128,000 rows; `customer.c_last_review_date`
→ `c_last_review_date_sk` (int) and `store.s_tax_precentage` → `s_tax_percentage`.

Layouts (ps: Iceberg partition on a transform of c1, rows sorted by (c1, c2), exact chunking;
P = min(32, base row groups); integer and decimal c1 use value-range `truncate`):

| Layout | Table | Sort columns | Partition | Partitions | Files | Row groups (base) |
|---|---|---|---|---:|---:|---:|
| l025 | store_sales | ss_sold_date_sk, ss_item_sk | truncate(58) | 33 | 38 | 687 (676) |
| l006 | catalog_sales | cs_sold_date_sk, cs_item_sk | truncate(58) | 34 | 34 | 361 (338) |
| l034 | web_sales | ws_sold_time_sk, ws_web_page_sk | truncate(2700) | 33 | 33 | 185 (169) |
| l009 | customer | c_current_addr_sk, c_first_name | truncate(54000) | 5 | 5 | 5 (4) |
| l003 | catalog_sales | cs_ext_ship_cost, cs_ext_discount_amt | truncate(46150) | 33 | 39 | 357 (338) |
| l029 | web_returns | wr_return_ship_cost, wr_return_tax | truncate(79876) | 18 | 18 | 32 (17) |

## Files

| File | What it is |
|---|---|
| `configs_ps.jsonl` (+ `.meta.jsonl`) | **The k = 2 results**: one record per query execution (bytes, rows, runtime, per-scan metrics, DPP flag, bindings) |
| `analysis/configs_ps_<metric>.csv` | Utility, totals and group per configuration |
| `analysis/paper_ps_k2_c2/profiles_combined_<0..4>.csv` | Per-query bytes/rows/runtime per strategy, `clustering/src/analyze.py` format, plus `measured_*` (measured in the group run vs taken from No Sort) |
| `analysis/paper_ps_k2_c2/workload_value.pdf`, `workload_value_rows.pdf` | The paper's figure (bytes) and a rows version, from `../plot_workload_value.py` |
| `build_stats.jsonl` | Every table build, append-only; the **last** record per namespace is the table that exists. Earlier records are superseded builds |
| `base_props.json` | Per-table Iceberg write properties (`base_props.pre-chunked.json`: before the base was rebuilt with exact chunking) |
| `explain.jsonl` | EXPLAIN of all 99 queries on base: 99/99 plan (q30 after the schema fix) |
| `pilot.jsonl`, `analysis/pilot_*.csv` | Pilot (store_sales s / ps / pz arms vs base). Arms built with the earlier writer (~14 row groups per file); used only to choose ps and the metrics |
| `analysis/listener_vs_static.csv` | Listener vs SQL-parsed columns (empty: no differences) |
| `layouts_ps.jsonl` | **Superseded, not used**: the one-table-at-a-time run, stopped after 76 base queries (6 errors are the interrupt) |
| `plans/` | The runner plans that produced each file |
