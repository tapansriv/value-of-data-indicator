# Sorting on Spark + Iceberg, Redbench IMDb — results (2026-10-08, Chameleon node)

Reviewer item R3D4 (a real or realistically skewed workload), on the same harness as the
TPC-DS SF30 rerun (`../RESULTS_NOTE.md`). Workload provenance: `../../../../redbench_imdb/README.md`.
Copied from `/mnt/tpcds/vdi_sort/imdb/results/`; Spark event logs, listener usage logs and
full driver logs stay on the node.

**Files.** `pilot.jsonl.gz`, `configs_ps.jsonl.gz` and `explain.jsonl.gz` are gzipped
(11–13 MB raw each, per-scan metrics for every table); `gunzip -k` before running
`analyze_sweep.py` on them. `analysis/` is exactly what `./run_phase.sh analyze ps` wrote.
`value_tiers.json`: the value-tier definition (goes in the paper). `logs/`: load, check-source,
build summaries, analyze output and the follow-on script's log.

## Setup (same as TPC-DS unless noted)

- Same harness, Spark build (fork `rowgroup-dev` @ 1fb30a5e3c, Spark 3.5.5, Scala 2.13.8,
  Java 17.0.20.1), Iceberg 1.8.1, `local[*]`, 128,000-row row groups, P = min(32, base row
  groups), `ps` layouts (partition on a transform of c1 + sort by c1, c2), metrics
  `task_bytes_read` + `task_records_read`, configurations measured directly, Frequent's
  group repeated. Harness commit efc85b2 + the uncommitted changes committed alongside this
  note (value assignments, `plan_layouts.py --keep-ids-from`).
- Data: JOB IMDb snapshot (`https://event.cwi.nl/da/job/imdb.tgz`, 1,263,193,115 bytes), 21
  tables, strict load (no rows dropped); all row counts match `imdb_row_counts.json`.
  14 of 21 tables span more than one row group (TPC-DS SF30: 10 of 24).
- Workload: 415 distinct queries, 24,881 executions in the Redset trace (Redbench, cluster
  186, db 8, May 2024). Each distinct query is executed once per layout. **Different from
  TPC-DS:** utility weights each query by its trace executions (net utility):
  Σ executions(q) · value(q) · NoSort(q) / sorted(q), No Sort = Σ executions(q) · value(q).
- **Value assignments: the paper's** (Tapan, 2026-10-08): Constant, Value 50/100/500/1000;
  high = N, medium = N/10, low = 1. Tiers by data column:

| tier | defining columns | distinct queries | executions |
|---|---|---:|---:|
| high | `cast_info.role_id` | 345 | 1,303 (5.24%) |
| medium | `name.gender`, `name.name_pcode_nf` (if not high) | 11 | 51 (0.20%) |
| low | the rest | 59 | 23,527 (94.56%) |

  Unlike TPC-DS (1 high, 2 medium of 99), the high column is read by most distinct queries but
  by only 5.24% of executions.

## Headline: k = 2, c = 2 (15 configurations, 5 groups, 2,112 query executions)

**task_bytes_read**

| Assignment | VOD | Frequent | Random | No Sort | VOD vs Freq | VOD vs Random |
|---|---:|---:|---:|---:|---:|---:|
| Constant | 25914.396 | 25914.396 | 24718.083 | 24881 | +0.00% | +4.84% |
| Value 50 | 98920.557 | 90095.360 | 81754.896 | 88932 | +9.80% | +21.00% |
| Value 100 | 174066.497 | 155633.940 | 139997.056 | 154337 | +11.84% | +24.34% |
| Value 500 | 1033960.357 | 679942.576 | 605934.336 | 677577 | +52.07% | +70.64% |
| Value 1000 | 2044392.209 | 1335328.372 | 1188355.937 | 1331627 | +53.10% | +72.04% |

Normalized to No Sort (VOD / Frequent / Random): Constant 1.042 / 1.042 / 0.993;
Value 50 1.112 / 1.013 / 0.919; Value 100 1.128 / 1.008 / 0.907; Value 500 1.526 / 1.003 /
0.894; Value 1000 1.535 / 1.003 / 0.892.

**task_records_read**

| Assignment | VOD | Frequent | Random | No Sort | VOD vs Freq | VOD vs Random |
|---|---:|---:|---:|---:|---:|---:|
| Constant | 28864.284 | 28864.284 | 24825.204 | 24881 | +0.00% | +16.27% |
| Value 50 | 121542.227 | 93123.990 | 86332.842 | 88932 | +30.52% | +40.78% |
| Value 100 | 219004.646 | 158743.352 | 149138.862 | 154337 | +37.96% | +46.85% |
| Value 500 | 1202278.497 | 683698.248 | 651587.021 | 677577 | +75.85% | +84.52% |
| Value 1000 | 2381029.930 | 1339891.868 | 1279647.220 | 1331627 | +77.70% | +86.07% |

Chosen tables (layout id, sort columns):
- VOD, Value 50/100: `cast_info` (l008: person_id, role_id) + `name` (l041: id, gender).
  Value 500/1000: `cast_info` (l011: role_id, person_id) + `name` (l041).
- Frequent, every assignment: `title` (l050: id, production_year) + `movie_keyword`
  (l038: keyword_id, movie_id).
- VOD, Constant: `title` (l053: id, title) + `movie_keyword` (l038). Identical bytes to
  Frequent on all 185 queries: `title.id` is unique, so sorting by (id, ·) gives one order.
- Random (single seed): `movie_info_idx` (l034: note, movie_id) + `name` (l045: md5sum,
  imdb_id). DPP never fires (0/390), so it reads slightly more than No Sort.

## Checks

- 2,112 / 2,112 configuration queries ok on the first attempt (retry pass found nothing).
- Repeat of Frequent's group `g_l038+l050_ps`: bytes and records identical on 185/185.
- Listener cross-check: 415 queries logged, 0 differ from the SQL-parsed column sets.
- `check-source` OK (21 tables); `build-base`: "multi-row-group tables match the manifest (14)";
  `explain`: 415/415 ok.
- DPP fired: g_l008+l041 373/376, g_l011+l041 375/376, g_l038+l050 and g_l038+l053 185/185,
  g_l034+l045 (Random) 0/390.

## Pilot (`cast_info` on person_id, role_id; 376 queries; 1,919 executions, all ok)

| arm | DPP | task_bytes_read | task_records_read | proc_rchar | skippedDataFiles |
|---|---:|---:|---:|---:|---:|
| base | 0 | — | — | — | 249 |
| base_rep | 0 | +0.0% | +0.0% | −0.0% | 249 |
| s | 0 | +0.2% | +3.3% | +1.5% | 219 |
| ps | 328 | −8.1% | −25.5% | −11.0% | 740 |
| pz | 328 | −7.8% | −25.5% | −10.8% | 738 |

Determinism (base_rep vs base): task_bytes_read and task_records_read max 0.0000%;
proc_rchar max 1.2258%. Same conclusion as TPC-DS: ps (DPP) is what prunes.

## Runtime (recorded, not the metric)

Per query on base (415): median 4.31 s, p90 7.21 s, max 15.32 s (q309), min 1.2 s.
Configuration runs: medians 2.94–4.48 s per run. Wall clock: pilot 03:43–07:10 UTC,
configurations 07:13–10:54 UTC. Layout builds 6–39 s each; warehouse 3.1 GB.

## Not done

- `plot` not run: `plot_workload_value.py` does not apply execution weighting.
- k/c beyond 2/2 not run.
