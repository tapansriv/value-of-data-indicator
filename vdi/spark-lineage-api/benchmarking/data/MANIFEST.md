# Benchmarking result-data manifest

> **2026-09-27: the five non-`main` branches below have been archived into
> `legacy_results/<branch>/` on `main`** (see `legacy_results/README.md`). Read
> `origin/<branch>:<path>` in this document as
> `legacy_results/<branch>/spark-lineage-api/benchmarking/<path>` for files the
> branch added or modified; files it left untouched are in `main`'s history at the
> merge base. `inventory.csv` has a `current_location` column with the exact
> mapping. The body below is the 2026-09-13 inventory, unchanged.

Inventory of every CSV under `spark-lineage-api/benchmarking/` across the six
branches that independently accumulated listener-overhead results.

Compiled 2026-09-13 by read-only inspection (`git show` / `git ls-tree` / `git log`)
from a worktree on branch `spark-scale`. Nothing was checked out, moved, or edited.
Machine-readable companion: `inventory.csv` (one row per path x branch, with blob
SHA, byte size, data-row count, header, and distinct `dataset`/`variant`/`configuration`
values).

Branch heads inspected:

| Branch | Head | Date | Subject |
|---|---|---|---|
| `origin/main` | `e07871a2` | 2026-09-13 | updating files from the last few months |
| `origin/cluster` | `c9f28263` | 2026-02-24 | updated legend |
| `origin/node1_tpcds` | `6db4ac56` | 2025-10-27 | finished tpcds runs |
| `origin/node1_tpcds_unmod_spark` | `9e96655d` | 2025-12-03 | finished tpcds unmod |
| `origin/node1_tpch` | `00336318` | 2025-10-27 | Modifying node1 for tpch |
| `origin/node2_tpch_unmod_spark` | `2d1d89b4` | 2025-12-10 | saving last run results |

Local `main`, `cluster`, `node1_tpcds` are identical to their origin refs.

---

## 1. Conclusions first

### 1.1 The 4-node TPC-H 1TB data EXISTS. It is on `cluster`, and only on `cluster`.

`REVISION_SCALEUP.md` §1.3 states the 4-node data point "is not in this working
copy" and that there is "no generating script". Both halves of that are true of
`main`, and both are **false of `cluster`**.

- **Generating script:** `origin/cluster:spark-lineage-api/benchmarking/scripts/plot_spark_internal_tpch.py`.
  Line 123 writes `figs/tpch_node4_1tb.pdf`; the same script also writes
  `figs/tpch_overhead_scatter.pdf`. The string `tpch_node4_1tb` appears nowhere
  else in any branch except a prose mention in `main:REVISION_SCALEUP.md`.
- **Raw inputs:** the four top-level files the script reads on `cluster`:
  - `spark_internal_listener_vanilla_results.csv`  (blob `56858297`)
  - `spark_internal_listener_bare_results.csv`     (blob `9398875b`)
  - `spark_internal_listener_cols_results.csv`     (blob `24fa5c04`)
  - `spark_internal_listener_rowgroup_results.csv` (blob `17f3896e`)

  The script filters `dataset == 'tpch'` and query numbers 1–22, averages over
  reps, and divides runtime by 60 000 (so the runtime column is milliseconds).
- **`nowrite` and `register` also have the same TPC-H run** on `cluster`
  (blobs `03ecf248`, `b2c15b98`) — the plot script simply does not read them.
  All six variants are available for a 4-node TPC-H figure, not just four.
- **The figure PDF** `figs/tpch_node4_1tb.pdf` exists only on `cluster`.

**Shape of the TPC-H portion, identical in all six variant files:** 74 data rows
= 37 queries (`1.sql`–`37.sql`) x exactly **2 repetitions** each. Queries 1–22 are
all present with 2 reps each. Measured q1–22 runtimes (ms) range from 101 654
(nowrite) to 2 488 975 (cols) — i.e. roughly 1.7 to 41.5 minutes per query.

**Provenance of those rows.** Commit `7eea784` (2025-11-11, "cleaned up files")
deleted the six files; commit `fa422157` (2025-11-16, "finished tpch on cluster")
recreated each of them with exactly 75 lines (header + 74 rows) and zero deletions.
The TPC-H portion has been byte-frozen since. So it is **one clean run**, not an
accumulation across commits.

**Caveat on "4 nodes" — read this before citing the number.** No committed file
records a node count. The evidence chain is:

- Only `cluster` run scripts pass `--master spark://controller:7077`
  (`run_test_{vanilla,bare,cols,nowrite,register,rowgroup}.sh`,
  `test_tpch_split_*.sh`, `run_vanilla_debug.sh`). Every other branch's scripts
  pass no `--master` at all, i.e. single-node `local[*]`. So `cluster` is
  unambiguously the distributed-Spark branch.
- Scale factor: `cluster` scripts read `DATA_PATH_TPCH="/mnt/tpch_1tb/data"` and
  `DATA_PATH_TPCDS="/mnt/tpcds_1tb/parquet"` — consistent with 1TB.
  (`test_tpch_split_*.sh` on `cluster` point at `/mnt/tpch/data`, unsuffixed.)
- "4 nodes" comes only from commit subjects `8f7ef34` / `052e761`
  (2026-01-23, "4 node data") and `9169822` (2026-02-15, "updated plots for 4 node
  cluster data"), plus the figure filename.
- Those three commits touched **only** the figure PDFs and the plot script — no
  CSV changed. The CSV content they plot dates from 2025-11-16, two months earlier.

So: node count = **4 per commit messages and filename; UNKNOWN from file contents**.
Executor config in the `cluster` scripts is `--executor-memory 45g --executor-cores 30
--conf spark.task.cpus=30`, with no `--num-executors`, so the cluster size cannot
be recovered from the scripts either. If the paper states "4 nodes", that claim
currently rests on commit messages alone — confirm against the Chameleon
reservation before the final submission.

### 1.2 Distinct data vs. duplicates

- 77 distinct CSV paths, 393 (path, branch) instances, **129 distinct blobs**.
- 62 of those 129 blobs appear on more than one branch (byte-identical copies).
- By kind: **69 result blobs**, 24 query-ID-map blobs (`queryIdMap*.csv`,
  `queryName,queryID`), 36 progress-log blobs (`*_queries_started.csv`, a single
  `query` column — these are crash-recovery logs, **not** results).
- Everything under `data/skylake_node/` and `data/storage_1_node/` is byte-identical
  on all six branches (34 of the 69 result blobs), except
  `data/storage_1_node/spark_mod_internal_listener/final_spark_vanilla.csv`
  (`98f71d0a`), which exists only on `main`.
- **All genuine cross-branch divergence lives in the six top-level
  `spark_internal_listener_<variant>_results.csv` files** (and their companion
  `*_queries_started.csv` logs). Those six filenames account for 27 distinct blobs
  across the branches.

### 1.3 Coverage (dataset x nodes x Spark build)

| Dataset | Nodes | Spark build | Covered? | Where |
|---|---|---|---|---|
| TPC-H | 1 | modified (custom) | yes | `main` top-level CSVs; consolidated in `data/all_results.csv` as `single_node_mod_spark` |
| TPC-H | 1 | unmodified | yes | `node2_tpch_unmod_spark` top-level CSVs; in `all_results.csv` as `unmod_spark` |
| TPC-DS | 1 | modified | yes | `node1_tpcds` top-level CSVs; in `all_results.csv` as `single_node_mod_spark` |
| TPC-DS | 1 | unmodified | yes | `node1_tpcds_unmod_spark` top-level CSVs; in `all_results.csv` as `unmod_spark` |
| TPC-H | 4 (claimed) | modified | yes, 2 reps | `cluster` top-level CSVs — **not in `all_results.csv`** |
| TPC-DS | 4 (claimed) | modified | partial, badly uneven | `cluster` top-level CSVs — **not in `all_results.csv`** |
| TPC-H | 4 | unmodified | **NO** | nowhere |
| TPC-DS | 4 | unmodified | **NO** | nowhere |
| either | 8 / 16 | either | **NO** | nowhere (this is the R2D16 work, not yet run) |
| TPC-H/DS | 1 | both, 10GB | yes, 9 reps | `data/storage_1_node/` (identical on all branches) |

`rowgroup` is absent from both unmodified-Spark cells by design — it requires the
instrumented Spark build.

### 1.4 Single most important gap

**There is no unmodified-Spark baseline at 4 nodes.** The single-node story has a
clean mod-vs-unmod pair (that is exactly what `all_results.csv`'s two
`configuration` values are). The 4-node story does not: `cluster` has all six
*listener variants* but only on the instrumented build, so the 4-node figure can
show listener-vs-`vanilla`-listener overhead but cannot show the cost of the
instrumented engine itself at scale. Since R2D14/R3W1/R3D1 are specifically about
Spark-as-the-engine credibility, and R2D16 asks for 8/16 nodes, this baseline gap
will propagate into every larger-cluster run unless it is fixed now.

Runner-up gap: the 4-node TPC-DS data on `cluster` is unusable as it stands — 131
distinct queries with repetition counts scattered across {3,4,5,6,7,11,12,13,14,15,16,17,19,20}
(vanilla file), accumulated over ~15 commits from 2025-12-07 to 2026-01-21 with
mid-run and post-kill commits. It cannot be averaged safely without deciding a
per-query rep cap.

---

## 2. Where every result set lives

Abbreviations: **M** = `main`, **C** = `cluster`, **D1** = `node1_tpcds`,
**DU** = `node1_tpcds_unmod_spark`, **H1** = `node1_tpch`,
**HU** = `node2_tpch_unmod_spark`.

### 2.1 Top-level `spark_internal_listener_<variant>_results.csv` — the divergent set

Schema `query,dataset,runtime` (runtime in ms), or `,query,dataset,runtime` with a
leading pandas index column. See §4.1 on the mixed-width rows.

| Variant | Branch | Blob | Bytes | Rows | tpch rows | tpcds rows |
|---|---|---|---|---|---|---|
| vanilla | M | `6b0cd42c` | 2334 | 112 | 112 | 0 |
| vanilla | C | `56858297` | 30775 | 1436 | 74 | 1362 |
| vanilla | D1 | `6c145660` | 3822 | 158 | 0 | 158 |
| vanilla | DU | `fa2ff779` | 16758 | 698 | 0 | 698 |
| vanilla | HU | `880ed5a9` | 2448 | 131 | 131 | 0 |
| vanilla | H1 | — | — | — | **file absent** | |
| bare | M | `5001f707` | 13129 | 535 | 535 | 0 |
| bare | C | `9398875b` | 5875 | 252 | 74 | 178 |
| bare | D1 | `2753d8b1` | 14815 | 518 | 0 | 518 |
| bare | DU | `13848177` | 11988 | 475 | 0 | 475 |
| bare | HU | `3c35daa9` | 2132 | 108 | 108 | 0 |
| bare | H1 | — | — | — | **file absent** | |
| cols | M | `8cd3a130` | 2135 | 108 | 108 | 0 |
| cols | C | `24fa5c04` | 5902 | 253 | 74 | 179 |
| cols | D1 | `b812ea3a` | 10773 | 382 | 0 | 382 |
| cols | DU | `d0706554` | 11343 | 449 | 0 | 449 |
| cols | HU | `d971c936` | 2153 | 109 | 109 | 0 |
| cols | H1 | — | — | — | **file absent** | |
| nowrite | M | `39a2b428` | 2232 | 113 | 113 | 0 |
| nowrite | C | `03ecf248` | 5873 | 252 | 74 | 178 |
| nowrite | D1 | `601edb2b` | 9812 | 366 | 0 | 366 |
| nowrite | DU | `4b30599d` | 11912 | 472 | 0 | 472 |
| nowrite | HU | `d681b2b5` | 2132 | 108 | 108 | 0 |
| nowrite | H1 | — | — | — | **file absent** | |
| register | M | `922b48f6` | 2216 | 112 | 112 | 0 |
| register | C | `b2c15b98` | 6072 | 260 | 74 | 186 |
| register | D1 | `2be48b65` | 9775 | 368 | 0 | 368 |
| register | DU | `d3e289f0` | 11538 | 457 | 0 | 457 |
| register | HU | `8d5a81a9` | 2131 | 108 | 108 | 0 |
| register | H1 | — | — | — | **file absent** | |
| rowgroup | M | `309064ae` | 2208 | 121 | 121 | 0 |
| rowgroup | C | `17f3896e` | 22465 | 1039 | 74 | 965 |
| rowgroup | D1 | `783c5e74` | 12476 | 474 | 0 | 474 |
| rowgroup | DU, H1, HU | — | — | — | **file absent** | |

Row and tpch/tpcds counts above are after the misalignment correction of §4.1
(3-field rows are read as `query,dataset,runtime`).

Reading of each branch:

- **`cluster`** — distributed Spark (`--master spark://controller:7077`), 1TB data
  paths, instrumented build. TPC-H = 37 queries x 2 reps, frozen since 2025-11-16.
  TPC-DS = uneven accumulation, see §1.4. Node count claimed 4 (§1.1).
- **`main`** — the single-node **TPC-H, modified Spark** source. Verified: its
  `cols`/`nowrite`/`register` files reproduce the corresponding
  `single_node_mod_spark`/`tpch` slices of `data/all_results.csv` exactly
  (108/108, 113/113, 112/112 rows). Scale factor: `main`'s `run_test_tpch.sh` and
  `test_tpch_split_*.sh` use `/mnt/tpch_1tb/data`; its `run_test_*.sh` use
  `/mnt/data_1tb/{tpch,tpcds}`; `run_listeners_r1to9.sh` and `run_vanilla.sh` use
  `/home/cc/{tpch,tpcds}` with no size marker. Which script produced which rows is
  **UNKNOWN**; the figure name `tpch_mod_node1_1tb.pdf` implies 1TB.
- **`node1_tpcds`** — single-node **TPC-DS, modified Spark**. Fully reproduces the
  `single_node_mod_spark`/`tpcds` slice of `all_results.csv` (all six variants,
  0 rows uncovered).
- **`node1_tpcds_unmod_spark`** — single-node **TPC-DS, unmodified Spark**. Fully
  reproduces the `unmod_spark`/`tpcds` slice (no `rowgroup`, as expected).
- **`node2_tpch_unmod_spark`** — **TPC-H, unmodified Spark**. Fully reproduces the
  `unmod_spark`/`tpch` slice. Despite the branch name, nothing in it indicates two
  nodes: no `--master` flag anywhere, and `all_results.csv` labels this data
  `unmod_spark` with no node qualifier. Node count = **UNKNOWN**, most likely 1.
- **`node1_tpch`** — has **no** `spark_internal_listener_*_results.csv` at all.
  Its only result file is `tpch_bare_results.csv` (25 rows, 14 distinct queries,
  blob `f4703e95` — identical on M, H1, HU). Its six `*_queries_started.csv`
  progress logs do differ from other branches, but those carry no runtimes. So
  this branch contributes **no unique runtime data**.

### 2.2 `data/all_results.csv` (`main` only, blob `3382a50b`, 287 171 B, 5459 rows)

Schema `,query,dataset,runtime,variant,configuration`. 159 distinct query values.
`configuration` takes exactly two values; there is **no 4-node configuration in it**.

| configuration | dataset | vanilla | bare | cols | nowrite | register | rowgroup |
|---|---|---|---|---|---|---|---|
| `single_node_mod_spark` | tpcds | 115 | 351 | 382 | 366 | 368 | 345 |
| `single_node_mod_spark` | tpch | 98 | 137 | 108 | 113 | 112 | 83 |
| `unmod_spark` | tpcds | 494 | 475 | 449 | 472 | 456 | — |
| `unmod_spark` | tpch | 102 | 108 | 109 | 108 | 108 | — |

(Row counts. Distinct-query counts per cell range 36–43 for tpch and 121–122 for
tpcds; see `inventory.csv` and §1.3.)

Verified reproducibility from branch sources, after the §4.1 correction:
**every row is accounted for except 32**, all in `single_node_mod_spark`/`tpch`/`bare`
(137 rows: 80 from `main`'s `spark_internal_listener_bare_results.csv`, 25 from
`tpch_bare_results.csv`, **32 from no committed CSV on any of the six branches**).
Example unaccounted rows: `(1.sql, 1271315)`, `(2.sql, 862670)`, `(5.sql, 10103550)`.

### 2.3 `data/storage_1_node/` — identical on all six branches

Per its committed `README`: 1 node at TACC, **10GB** TPC-H and TPC-DS on a separate
mounted drive, whole workload run **9 times** per listener implementation.
`spark_mod_internal_listener/` = all listeners on modified Spark;
`spark_vanilla_internal_listener/` = all listeners except `rowgroup` on
out-of-the-box Spark. Schema `query,dataset,runtime`.

| File (under `data/storage_1_node/`) | Blob | Bytes | Rows | Distinct queries |
|---|---|---|---|---|
| `spark_mod_internal_listener/spark_internal_listener_vanilla_results.csv` | `a62a1b35` | 33221 | 1521 | 169 |
| `spark_mod_internal_listener/spark_internal_listener_bare_results.csv` | `1bba8c91` | 32050 | 1467 | 163 |
| `spark_mod_internal_listener/spark_internal_listener_cols_results.csv` | `047122c7` | 32055 | 1467 | 163 |
| `spark_mod_internal_listener/spark_internal_listener_nowrite_results.csv` | `9f8dd098` | 27330 | 1264 | 163 |
| `spark_mod_internal_listener/spark_internal_listener_register_results.csv` | `f4a841c9` | 32067 | 1467 | 163 |
| `spark_mod_internal_listener/spark_internal_listener_rowgroup_results.csv` | `cd2fe003` | 33229 | 1521 | 169 |
| `spark_mod_internal_listener/final_spark_mod_data.csv` | `501c6382` | 19465 | 163 | 163 |
| `spark_mod_internal_listener/final_spark_vanilla.csv` (**`main` only**) | `98f71d0a` | 19465 | 163 | 163 |
| `spark_vanilla_internal_listener/spark_internal_listener_vanilla_results.csv` | `0feec192` | 33183 | 1521 | 169 |
| `spark_vanilla_internal_listener/spark_internal_listener_bare_results.csv` | `4045e355` | 32025 | 1467 | 163 |
| `spark_vanilla_internal_listener/spark_internal_listener_cols_results.csv` | `1582ee91` | 32059 | 1467 | 163 |
| `spark_vanilla_internal_listener/spark_internal_listener_nowrite_results.csv` | `5192a8cc` | 32032 | 1467 | 163 |
| `spark_vanilla_internal_listener/spark_internal_listener_register_results.csv` | `935664c0` | 32068 | 1467 | 163 |
| `spark_vanilla_internal_listener/final_spark_vanilla.csv` | `5d77a0c0` | 16791 | 163 | 163 |

Plus 9 `queryIdMap_{1..9}.csv` (query-name to Spark execution ID, one per rep) and
`check.py`. No `rowgroup` under `spark_vanilla_internal_listener/`, as the README says.

Note `final_spark_mod_data.csv` and the `main`-only `final_spark_vanilla.csv` in the
same directory are different blobs of identical byte length (19465) with identical
headers — see §4.2.

### 2.4 `data/skylake_node/` — identical on all six branches

Older data, moved into this subdirectory by `7778de0` (2025-09-16). Schema per file
is `query,dataset,run_number,<variant>_time`; `r1to9` in the filenames and 1089 rows
= 121 queries x **9 repetitions**. `custom_spark/` = instrumented build,
`plain_spark/` = stock build.

| File (under `data/skylake_node/`) | Blob | Bytes | Rows |
|---|---|---|---|
| `all_results_combined.csv` | `c8c19aa9` | 15907 | 365 |
| `experiment_comparison_stats.csv` | `52f6973d` | 31461 | 121 |
| `final_results_5_21.csv` | `26c71289` | 52183 | 1089 |
| `custom_spark/final_results_custom_spark_8_26.csv` | `9973b052` | 58891 | 1089 |
| `custom_spark/vanilla_results_r1to9.csv` | `f5c2801d` | 26952 | 1089 |
| `custom_spark/listener_bare_results_r1to9.csv` | `337687b1` | 26952 | 1089 |
| `custom_spark/listener_full_results_r1to9.csv` | `40900c7d` | 26953 | 1089 |
| `custom_spark/listener_nowrite_results_r1to9.csv` | `1a774c48` | 26957 | 1089 |
| `custom_spark/listener_register_results_r1to9.csv` | `2c9dd0ef` | 26957 | 1089 |
| `custom_spark/listener_rg_results_r1to9.csv` | `e521605d` | 26958 | 1089 |
| `plain_spark/final_results_plain_spark.csv` | `7b84bbcf` | 52534 | 1089 |
| `plain_spark/vanilla_results_r1to9.csv` | `cd6792f8` | 26952 | 1089 |
| `plain_spark/listener_bare_results_r1to9.csv` | `4dc9e689` | 26954 | 1089 |
| `plain_spark/listener_full_results_r1to9.csv` | `f7058b55` | 26953 | 1089 |
| `plain_spark/listener_nowrite_results_r1to9.csv` | `1df57046` | 26957 | 1089 |
| `plain_spark/listener_register_results_r1to9.csv` | `449c9cd9` | 26958 | 1089 |
| `spark_internal_timing/spark_internal_listener_rowgroup_results.csv` | `e80fdd87` | 23842 | 1089 |
| `spark_internal_timing/e2e_timing.csv` | `b692477c` | 68 | 2 |

Plus `spark_internal_timing/query_maps/queryIdMap_{1..9}.csv` and two `join.py`.

Node count and scale factor: **UNKNOWN**. There is no README in this directory. The
directory name suggests a single Skylake node; the commit that created it
(`7778de0`, subject "1 node storage 10gb dataset") is the same commit that
introduced `storage_1_node`, so the subject may describe the other directory.
`plain_spark/listener_rg_results_r1to9.csv` does not exist — consistent with
`rowgroup` requiring the instrumented build.

`custom_spark/listener_rg_results_r1to9.csv` has header column
`listener_register_time`, not a rowgroup-specific name — a likely copy-paste in the
harness. The values differ from `listener_register_results_r1to9.csv` (different
blob), so the data is distinct; only the column label is suspect.

### 2.5 Small / partial files

| Path | On | Blob | Bytes | Rows | Notes |
|---|---|---|---|---|---|
| `data/internal_bare_partial_oct_4.csv` | D1, DU | `9fff9435` | 578 | 22 | tpcds only; partial run, 2025-10-04 |
| `data/vanilla_partial_oct4.csv` | D1, DU | `6f956b67` | 641 | 25 | tpcds only; partial run |
| `data/tpcds_vanilla_b1_r2.csv` | D1, DU | `7ef71d01` | 620 | 24 | tpcds only; "batch 1 rep 2" |
| `data/spark_internal_listener_bare_results.csv` | D1, DU | `68d52e41` | 4233 | 167 | tpcds only, 110 distinct queries |
| `data/spark_internal_listener_vanilla_results.csv` | D1, DU | `004085db` | 12518 | 531 | tpcds only, 91 distinct queries |
| `data/tpch_vanilla_query38_results.csv` | M, C, H1, HU | `530baf66` | 82 | 3 | one query, 3 reps |
| `tpch_bare_results.csv` | M, H1, HU | `f4703e95` | 516 | 25 | tpch, 14 distinct queries; 25 of these rows appear in `all_results.csv` |
| `tpcds_results.csv` | C only | `0da3289a` | 3993 | 99 | header `,query,vanilla_time_sec,listener_time_sec,percent_diff,diff_sec` — **no `dataset` column**, pre-aggregated, provenance UNKNOWN |

### 2.6 Non-result files (do not treat as data)

- `*_queries_started.csv` (36 distinct blobs): single `query` column, crash-recovery
  progress logs written before each query. Row counts differ from the matching
  result files on every branch; the difference is the count of queries that started
  and did not produce a runtime row.
- `queryIdMap*.csv` (24 distinct blobs): `queryName,queryID` — Spark execution-ID
  maps, needed to join row-group accumulator output back to queries.

---

## 3. Variant glossary

From `spark-lineage-api/compile.sh` and `listener_versions_new/` (identical mapping
on all six branches).

| Variant in CSVs | Source file | JAR | Meaning |
|---|---|---|---|
| `vanilla` | `LineageAPI_vanilla.scala` | `spark-vanilla.jar` | no listener; baseline |
| `bare` | `LineageAPI_bare.scala` | `spark-bare-listener.jar` | listener attached, does nothing |
| `register` | `LineageAPI_bare_just_register.scala` | `spark-listener-just-register.jar` | listener registration only |
| `nowrite` | `LineageAPI_nowrite.scala` | `spark-query-api-no-write.jar` | collects usage, does not persist |
| `cols` (a.k.a. full) | `LineageAPI.scala` | `spark-lineage-api.jar` | column-level usage, persisted |
| `rowgroup` | `LineageAPI_rgs.scala` | `spark-rowgroup.jar` | row-group-level; needs instrumented Spark |

Note the naming skew: in `data/skylake_node/` the `cols` variant is filed under
`listener_full_*`, and `rowgroup` under `listener_rg_*`.

---

## 4. Conflicts

### 4.1 Same path, different content across branches

Thirteen paths collide. Six are result files (§2.1 has the full breakdown); the
other seven are progress logs and query maps.

| Path | Distinct blobs | How they differ |
|---|---|---|
| `spark_internal_listener_vanilla_results.csv` | 5 (M, C, D1, DU, HU) | disjoint runs: M = tpch single-node mod, C = 4-node 1TB, D1 = tpcds single-node mod, DU = tpcds unmod, HU = tpch unmod. Not versions of one file. |
| `spark_internal_listener_bare_results.csv` | 5 (M, C, D1, DU, HU) | same split |
| `spark_internal_listener_cols_results.csv` | 5 (M, C, D1, DU, HU) | same split |
| `spark_internal_listener_nowrite_results.csv` | 5 (M, C, D1, DU, HU) | same split |
| `spark_internal_listener_register_results.csv` | 5 (M, C, D1, DU, HU) | same split |
| `spark_internal_listener_rowgroup_results.csv` | 3 (M, C, D1) | same split; absent on the two unmod branches by design, and absent on H1 |
| `spark_{vanilla,bare,cols,nowrite,register,rowgroup}_queries_started.csv` | 4–6 each | progress logs, per-branch by construction |
| `queryIdMap_1.csv` | 4 (M=HU `1ba7933b`, D1 `c870e10a`, DU `616e1c7f`, H1 `9dade85d`) | 95 / 428 / 432 / 93 rows; per-run execution-ID maps |
| `queryIdMap_2.csv` | 1 (M, H1, HU identical) | no conflict |

**The important consequence:** these are not merge conflicts and must not be
resolved by picking a winner. Each branch's copy is a distinct experiment. Any
consolidation has to add a `configuration` column (as `all_results.csv` already
does) rather than overwrite.

**Structural defect in six blobs — mixed row widths.** These files were appended to
by two different writers: some rows carry a leading pandas index, some do not.
The header is `,query,dataset,runtime` (4 fields) but a subset of rows have 3.
A naive `pd.read_csv` shifts those rows one column left, putting the query name in
the index column and a runtime value into `dataset`.

| Branch | Variant | Blob | 4-field rows | 3-field rows |
|---|---|---|---|---|
| main | vanilla | `6b0cd42c` | 65 | 47 |
| node1_tpcds | bare | `2753d8b1` | 491 | 27 |
| node1_tpcds | cols | `b812ea3a` | 308 | 74 |
| node1_tpcds | nowrite | `601edb2b` | 169 | 197 |
| node1_tpcds | register | `2be48b65` | 146 | 222 |
| node1_tpcds | rowgroup | `783c5e74` | 289 | 185 |

`data/Final analysis.ipynb` documents a "column correction (misalignment fix)" in
its first cell, so this was known and handled when `all_results.csv` was built.
Any new consumer must apply the same correction. Reading these files naively
silently drops 27–222 rows per file into a garbage `dataset` value.

### 4.2 Other content conflicts

- `data/storage_1_node/spark_mod_internal_listener/final_spark_vanilla.csv`
  (`98f71d0a`, `main` only) and `final_spark_mod_data.csv` (`501c6382`, all
  branches) sit in the same directory, have the same header
  (`query,dataset,register_mean,bare_mean,rowgroup_mean,full_mean,vanilla_mean,nowrite_mean`),
  the same 163 rows and the same 19465-byte length, but are different blobs. Which
  of the two backs any published number is **UNKNOWN**. The file named
  `final_spark_vanilla.csv` living under `spark_mod_internal_listener/` is itself
  suspicious given the sibling directory `spark_vanilla_internal_listener/` has a
  file of the same name (`5d77a0c0`, 16791 B, different column set — no
  `rowgroup_mean`).
- Scale-factor conflict on the 1-node data: `data/storage_1_node/README` says
  **10GB**, but `scripts/stacked_bars.py` writes its TPC-H figure to
  `figs/tpch_node1_30gb.pdf` — **30GB**. The script takes its input file as
  `sys.argv[1]`, so the committed code does not say which dataset produced that
  figure. Do not cite either number without resolving this.

---

## 5. Referenced but absent

### 5.1 `all_results.csv`'s own inputs are gone (highest-value gap after the baseline)

`data/Final analysis.ipynb` builds `all_results.csv` from 23 per-variant CSVs under
two directories that **exist on no branch**:

```
data/tpcds_results/combined_tpcds.csv
data/tpcds_results/final_results_single_node/spark_internal_listener_{vanilla,bare,register,nowrite,cols,rowgroup}_results.csv
data/tpcds_results/unmod_spark/spark_internal_listener_{vanilla,bare,register,nowrite,cols}_results.csv
data/tpch_results/final_results_single_node/{vanilla,bare,register,nowrite,cols,rowgroup}_tpch.csv
data/tpch_results/unmod_spark/spark_internal_listener_{vanilla,bare,register,nowrite,cols}_results.csv
```

It also writes `combined_results_single_node.csv` and `summary_results.csv`, neither
of which is committed anywhere.

Mitigation: §2.2 shows those inputs are **recoverable from the branch top-level
files** for all cells except 32 rows of `single_node_mod_spark`/`tpch`/`bare`. The
mapping is: `tpcds_results/final_results_single_node/` = `node1_tpcds` top-level,
`tpcds_results/unmod_spark/` = `node1_tpcds_unmod_spark` top-level,
`tpch_results/unmod_spark/` = `node2_tpch_unmod_spark` top-level,
`tpch_results/final_results_single_node/` = `main` top-level (partially).

**Provenance discrepancy:** notebook cell 47 sets
`combined_u['configuration'] = "single_node_unmod_spark"`, but the committed
`all_results.csv` contains the value `unmod_spark`. So the committed notebook is
**not** the exact code that produced the committed `all_results.csv`. Treat the
notebook as indicative, not authoritative.

### 5.2 Other missing inputs

| Script | Reads | Status |
|---|---|---|
| `scripts/analyze_overheads.py` | `../data/custom_spark/final_results_custom_spark_8_26.csv` | **broken path** — the file lives at `../data/skylake_node/custom_spark/...` since `7778de0` (2025-09-16). The script was never updated. |
| `scripts/count_logs.py` | `../tpcds_rgs/*/usage_logs/*.parquet`, `../tpch_rgs/*/usage_logs/*.parquet` | **absent on all six branches.** These are the raw row-group usage logs the listener writes. Zero paths matching `tpcds_rgs` or `tpch_rgs` exist in any branch. |
| `scripts/{scatter_pct_diff,compare_vanillas,stacked_bars}.py` | input files via `sys.argv` | which file backs each of `figs/{rg_vs_vanilla,tbl_vs_vanilla,mod_spark_comp,tpch_node1_30gb}.pdf` is **UNKNOWN** — not recorded in code or commit messages. |

### 5.3 Figures without committed raw data on the branch that holds them

`figs/tpch_node4_1tb.pdf` and `figs/tpch_overhead_scatter.pdf` exist only on
`cluster`. `figs/{tpch_mod_node1_1tb,tpch_node1_30gb,tpch_single_node_mod_spark,unmod_vs_mod_scatter}.pdf`
exist only on `main`. `figs/spark_internal_tpch.pdf` exists only on `cluster`.
The eight figures common to all branches
(`grouped_bars_tpcds{,_small,_large}.pdf`, `grouped_bars_tpch.pdf`,
`mod_spark_comp.pdf`, `rg_vs_col.pdf`, `rg_vs_vanilla.pdf`, `tbl_vs_vanilla.pdf`)
are byte-identical everywhere. **No script in any branch has an active `savefig`
for `figs/rg_vs_col.pdf` or for any `figs/grouped_bars_*.pdf`.** The closest is
`scripts/stacked_bars.py` (identical on all six branches), whose only `rg_vs_col`
reference is the commented-out line `# plt.savefig("../figs/storage_rg_vs_col.pdf")`
— a different filename — and whose four `plot_grouped(..., "../figs/grouped_bars_*.pdf")`
calls are all commented out, leaving only `tpch_node1_30gb.pdf` live. Those five
figures are committed with no reproducible generator.

---

## 6. Suggested consolidation (not performed)

Nothing in this pass modified or moved any file. If a consolidation is wanted:

1. Extend `all_results.csv`'s `configuration` vocabulary with a fourth value for the
   `cluster` data (e.g. `node4_mod_spark`) and append the six `cluster` top-level
   files, applying the §4.1 width correction and filtering `runtime != -1` and
   duplicates the way the notebook does.
2. Keep the 4-node TPC-DS rows out, or cap reps per query, until §1.4 is settled.
3. Do not delete any branch copy — each is the only record of its run, and several
   are the only surviving source for slices of `all_results.csv`.
4. Resolve the three UNKNOWNs that affect published claims before the final
   submission: the 4-node node count (§1.1), the 10GB-vs-30GB single-node scale
   factor (§4.2), and which of the two `final_spark_*.csv` files backs the
   `storage_1_node` numbers (§4.2).
