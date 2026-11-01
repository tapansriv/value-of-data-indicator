# Redbench IMDb workload — R3D4 skewed/real workload

The skewed-workload answer to **R3D4** ("a real workload trace is preferred, or at least a
workload with realistic distribution skews"). Chosen 2026-10-07; to be used with the
**sorting** experiment (see `clustering/spark/REVISION_SORTING.md`; branch `sorting-spark` was merged into `main` at
`c334627` and deleted 2026-10-08).

## Provenance

Redbench replays a **real Amazon Redshift access trace** (Redset) onto an existing benchmark.
It takes each real query's scanset — the set of tables it read — matches it to a benchmark
query with a similar scanset, and emits that query at the real arrival timestamp.

- Paper: *Redbench: Workload Synthesis From Cloud Traces*, Wehrstein, Heinrich, Stoian, Krid,
  Stemmer, Kipf, Binnig, El-Hindi — VLDB'26, Experiment/Analysis/Benchmark track.
  https://arxiv.org/abs/2511.13059 · code https://github.com/DataManagementLab/Redbench (Apache 2.0)
- Underlying trace: Redset, 200 provisioned + 200 serverless Redshift clusters over three months
  of 2024. https://github.com/amazon-science/redset (CC BY-NC 4.0). Published with
  van Renen et al., *Why TPC Is Not Enough*, PVLDB 17, p. 3694.
- These files were extracted from Redbench's **published** workload,
  https://osf.io/fgny3/files → `paper_workloads/matching/workload.csv` (28 MB), whose
  `used_config.json` records: support benchmark `imdb`, `matching_method: "join"`,
  provisioned cluster **186**, database **8**, window **2024-05-01 → 2024-06-01**.

**What is real and what is not.** Real: which tables are touched, the order, the arrival
timestamps, the repetition structure. Synthetic: the SQL text itself (JOB/CEB queries over
IMDb) and the underlying data. State this explicitly in the paper — VDI is driven by *which
data is accessed and how often*, which is precisely the layer Redbench makes real.

## Contents

- `queries/q001.sql … q415.sql` — the 415 distinct SELECT statements, numbered by first
  appearance in the stream.
- `stream.csv` — 24,881 executions in real arrival order:
  `seq, arrival_timestamp, query_id, exec_ms, mbytes_scanned, query_file, read_tables`.
  `exec_ms` and `mbytes_scanned` are the **real Redshift** measurements for the matched query,
  not measurements of the IMDb query.

Only SELECTs are extracted here. The source CSV also holds 11,314 inserts, 110 updates and
48 deletes (36,353 rows total); re-extract from `workload.csv` if the write stream is wanted.

## Measured skew (computed from stream.csv)

Span 2024-05-04T20:45 → 2024-05-13T12:39 (9 days).

**Query concentration:** top 10 distinct queries = **92.2%** of all executions; hottest query
fires **7,825** times; median distinct query fires 3 times. 30 distinct table-sets.
6,405 distinct `exact_repetition_hash` over 24,881 selects.

**Table read share** (20 tables read in total):
`title` 22.8% · `keyword` 22.3% · `movie_keyword` 22.3% · `movie_info` 21.9% ·
`info_type` 1.7% · `cast_info` 1.7% · `name` 1.7% · `role_type` 1.2% · tail <1% each.
Top 4 ≈ 89%.

**Filter-predicate columns** (26 distinct, weighted by executions) — the axis the sorting
experiment decides over:

| column | share |
|---|---|
| `title.production_year` | 30.3% |
| `keyword.keyword` | 29.6% |
| `movie_info.info` | 29.3% |
| 23 more (`cast_info.note`, `name.gender`, `movie_companies.note`, `company_name.country_code`, …) | ≤1.9% each |

Tables per distinct query: 4–17, most commonly 6.

**These column shares are indicative, not authoritative.** They came from a one-off heuristic
regex over the `FROM`/`WHERE` text (alias resolution + `col OP literal`), not from the project's
parser. Before they drive any sorting decision, re-derive the column sets through the SQL-parsed
path that the sorting harness validates against the Spark listener — the same way the 99 TPC-DS
queries were done. Note also that `oracle/scripts/tpcds_parse_columns_from_query.py` is
TPC-DS-specific and carried a substring bug (`d_date` credited inside `d_date_sk`) fixed
2026-10-07; if any of it is borrowed, use the whole-identifier version.

## Why sorting and not placement

Sorting decides over **columns**: 26 of them with a long tail, so the decision stays
discriminating (`REVISION_PLAN.md` framing #3). Placement decides over **tables**, where four
of twenty take ~89% of reads and the decision is nearly pre-made. IMDb is also only ~1–1.5 GB
as Parquet, so a placement storage hierarchy would need implausibly small disks to create
contention, while bytes-scanned is scale-insensitive.

## Experiment design

Do **not** run two scenarios. Run one sorting experiment and sweep the correlation ρ between
task value and query frequency, e.g. ρ ∈ {1.0, 0.5, 0.0, −0.5}:

- **ρ = 1 (value aligns with frequency).** Frequency picks `title.production_year`,
  `keyword.keyword`, `movie_info.info`; an aligned value assignment picks the same. Shows VDI
  **costs nothing** when frequency is already a good signal.
- **ρ ≤ 0 (value decorrelated).** Value concentrates in the 23-column tail, which lives on
  *different* tables. VDI diverges from frequency and should win on bytes scanned.

One figure, gap ≈ 0 at ρ=1 widening as ρ falls. It answers R3D4 **and** the "When does VDI
help?" subsection that `REVISION_PLAN.md` names as framing decision #1 — covering R1W3, R1E4,
R2W1, R2D5 and MW2.

**The ρ=1 arm is not automatically a null result.** `REVISION_SORTING.md` records that under
Constant task values, VOD and Frequent already differ in sort columns beyond the top few: VOD
divides each query's value equally among the columns it touches, while Frequent counts accesses.
So the honest ρ=1 claim is "VDI matches frequency *on the tables that matter*", not "VDI reduces
to LFU." Phrase it that way in the paper.

**Dialect:** run these through the sorting harness's `translate_queries.py` (DuckDB → Spark SQL
via sqlglot, already clean on 99/99 TPC-DS queries) rather than hand-editing. These queries are
vanilla comma-join SELECTs with `LIKE` / `IN` / `MIN()`, so they should need less work.

## Check this first

**Row-group eligibility.** `REVISION_SORTING.md` found only 10 of 24 TPC-DS tables span more
than one row group at SF30, which is why half the published k=2 budget hit no-op tables. Run
the same check on IMDb Parquet before committing to a k/c budget.

**Measured 2026-10-07 — see the section below.** 14 of 21 tables are eligible and all three hot
columns are sortable, so the experiment is viable.

## Getting the data (Parquet)

Two routes; either way, land Parquet per table.

1. **Prebuilt DuckDB (shortest).** `https://osf.io/download/68abfdbf18fead7c5dbcbebf/` →
   `db_original.duckdb`, 2.66 GB, IMDb already loaded. Then one
   `COPY <table> TO '<table>.parquet' (FORMAT PARQUET)` per table.
2. **Raw CSVs.** `https://event.cwi.nl/da/job/imdb.tgz` — verified live 2026-10-07,
   1,263,193,115 bytes, 21 tables, ~3.7 GB decompressed. Load with JOB's `schema.sql` /
   `load.sql`, then export.

Redbench's own code takes route 1; its CWI path is present but commented out.

## Regenerating instead of reusing

The published workload above used `join` matching on one cluster. To change the diversity
profile — the 92% top-10 concentration is extreme — generate a fresh one with `scanset`
matching and/or a different cluster:

```bash
python src/redbench/run.py --redset_path data/full_provisioned.parquet \
  --output_dir output --generation_strategy matching \
  --config_path_matching <config>     # must pass explicitly: run.py defaults to fast.json
```

`matching/run.py` silently falls back to `fast.json` ("for fast evaluation - change to
default.json for full generation"). Use the `matching` strategy, not `generation`: generation
emits Postgres `DISTINCT ON`, which Spark 3.5.5 will not parse.

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
56 layouts, 10,807 query executions, ~14 GB; net utility verified against a hand computation on
all 624 configs. Steps in NODE_RUNBOOK.md ("Second workload").

## Value assignment used for the run (Tapan, 2026-10-08; SUPERSEDES the tier ratios above)

The paper's five assignments, exactly as for TPC-DS: **Constant**, and **Value 50 / 100 / 500 /
1000** with high = N, medium = N/10, low = 1. Tiers are defined by data columns, as in the paper:

| tier | defining columns | distinct queries | executions (share) |
|---|---|---|---|
| high | `cast_info.role_id` | 345 | 1,303 (5.24%) |
| medium | `name.gender`, `name.name_pcode_nf` (queries not already high) | 11 | 51 (0.20%) |
| low | everything else | 59 | 23,527 (94.56%) |

Recorded with the per-tier query lists in `harness/value_tiers.json` (also copied to
`$RESULTS/analysis/value_tiers.json` on the node). The `comp`, `rare` and `hot` selections and
the r : √r : 1 ratios were never run. Unlike TPC-DS (1 high and 2 medium of 99 distinct
queries), the high column here is read by most distinct queries but by only 5% of executions.
