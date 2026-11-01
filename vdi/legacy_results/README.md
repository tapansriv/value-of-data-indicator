# legacy_results

Pre-revision listener-overhead benchmarking runs (Oct 2025 – Feb 2026) that used to
live on separate branches. Most of these are being rerun for the PVLDB #926
revision; they are kept here for reference and provenance, not as current results.

Archived 2026-09-27. Each `<branch>/` directory holds the files that branch
**added or modified** relative to its merge base with `main`, at their original
paths. Files the branch never touched are not copied — their versions are in
`main`'s history at the merge base.

| Directory | Source head | Last commit | Merge base | Contents |
|---|---|---|---|---|
| `cluster/` | `c9f28263` | 2026-02-24 | `7aee185c` | Distributed run (`--master spark://controller:7077`), instrumented Spark. TPC-H 1TB, 2 reps, all six listener variants; partial, uneven TPC-DS. Only copy of `scripts/plot_spark_internal_tpch.py` → `figs/tpch_node4_1tb.pdf`. Node count (4) is not recorded in any file — see `REVISION_SCALEUP.md` §1.3. |
| `node1_tpcds/` | `6db4ac56` | 2025-10-27 | `5f14811a` | TPC-DS, single node, instrumented Spark. |
| `node1_tpcds_unmod_spark/` | `9e96655d` | 2025-12-03 | `5f14811a` | TPC-DS, single node, unmodified Spark (no `rowgroup` variant by design). |
| `node1_tpch/` | `00336318` | 2025-10-27 | `8298a959` | Script edits only (`test_tpch_split*.sh`); the branch otherwise deleted result files. |
| `node2_tpch_unmod_spark/` | `2d1d89b4` | 2025-12-10 | `7aee185c` | TPC-H, single node, unmodified Spark (no `rowgroup` results). |

Paths under each directory mirror the repo root, e.g.
`cluster/spark-lineage-api/benchmarking/spark_internal_listener_vanilla_results.csv`.

**Same filename ≠ same experiment.** The top-level
`spark_internal_listener_<variant>_results.csv` files share names across branches
but are disjoint runs. Several also have mixed row widths (some rows carry a
leading pandas index, some do not), so a naive `pd.read_csv` misaligns columns.
See `spark-lineage-api/benchmarking/data/MANIFEST.md` §2.1 and §4.1 before reading
any of them; `inventory.csv` beside it has a `current_location` column mapping
each inventoried file to where it now lives.

Not archived: `spark-lineage-api/cs` (73 MB ELF binary committed by accident on
`node1_tpcds_unmod_spark`) and `spark-lineage-api/metastore_db/` (Derby metastore
on `cluster`). Full branch histories, including those, are preserved in a local
git bundle: `~/vdi_branch_backups/value-of-data-metric_legacy_branches_2026-09-27.bundle`
(restore with `git fetch <bundle> 'refs/remotes/origin/*:refs/remotes/legacy/*'`).
