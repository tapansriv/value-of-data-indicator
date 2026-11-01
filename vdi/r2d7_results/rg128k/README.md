# R2D7 rerun with 128,000-row row groups and queries 132–163

Raw outputs of the second R2D7 run (Chameleon node, 2026-10-21), done to the plan in
`~/value_of_data/REVISION_R2D7_RG128K.md`. Start with **`RESULTS_NOTE.md`**. Every judgement call
is in `DECISIONS.md`. The first run (128 MiB row groups, queries 1–99) is in the parent directory
`r2d7_results/`, left as it was.

Paths in the notes map to this directory as follows:
- `/mnt/tpcds/results_rg128k/<x>` → `r2d7_results/rg128k/<x>`
- `/mnt/tpcds/parquet_rg128k/sf<N>/` notes → `sf<N>/datagen/`

The Parquet itself (written by `RG_ROWS=128000 PARQUET_ROOT=/mnt/tpcds/parquet_rg128k`) is not in
git. It is rebuilt from the same dsdgen 4.0.0 text, seed 19620718 (`sf<N>/datagen/DATAGEN_NOTES.md`).

Code that produced this, all in `value-of-data-metric`:
- **Conversion:** `tpcds_datagen/` (`RG_ROWS`, `PARQUET_ROOT`).
- **Capture and VDI:** `oracle/scripts/run_spark_sf.sh` and `run_capture_all.sh` (`QUERIES=1-163`, `RESULTS`, `QUERY_DIR`).
- **Authored queries:** `oracle/scripts/author_rg_selective.py` wrote `spark-lineage-api/benchmarking/tpcds_queries_spark/query132.sql`–`query163.sql`.
- **Checks:** `rg_selective_accept.py`, `rg128k_checkpoint.py`, `rg128k_before_after.py`.

The driver scripts that called these are in `run_scripts/`. The code state as run, the tracked
diff and the engine jar hashes are in `provenance/`.

## Layout

| Path | What |
|---|---|
| `RESULTS_NOTE.md` | the results note: settings, row groups, authored queries, pruning, §4.4 results, caveats, wall-clock |
| `DECISIONS.md` | judgement calls made during the run, with reasons |
| `CHECKPOINT_SF30.md` | the SF30 checkpoint written after its capture |
| `authored_queries_by_sf.md` | queries 132–163: predicate, row groups read / total, rows returned, per SF |
| `before_after_first_run.{md,csv}` | §4.4 medians and cross-SF stability, first run vs this run |
| `sf_comparison.json` | cross-SF comparison (`compare_sf.py`) |
| `query_set_131.json` | the 131-query set every VDI result uses: 1–99 plus 132–163 |
| `common_completed_sf30_60_100.json` | queries completed at all three SFs (163) |
| `sf<N>/datagen/` | `ROWGROUPS.md` (row groups per table, old vs new), Parquet notes, row-count verification, conversion meta, gzipped conversion log |
| `sf<N>/capture/` | `queries.csv` (per statement: status, runtime, rows returned), `spark_conf.txt`, `driver.log.gz` |
| `sf<N>/values/`, `vdi/`, `figs/` | task values, VDI outputs (all but the row-group Full files), per-SF figures |
| `sf<N>/pruning.json` | row groups read / total per query and table, first run vs this run |
| `sf<N>/rg_selective_acceptance.json` | acceptance of queries 132–163 against the capture |
| `sf30/order_profile.csv` | which columns follow row order (§5.2) |
| `sf30/rg_selective_calibration.json` | literals for 132–163, calibrated on SF30 footers |
| `sf30/rg_selective_overrides_UNUSED_cr_order_window.json` | the template F override that was tried and not used (see `DECISIONS.md`) |
| `sf30/acceptance/` | the Spark acceptance run before capture (8 bases + 32 authored) |
| `sf{60,100}/rg_selective_predicted.json` | footer-predicted row groups for 132–163 |
| `sec44_after/` | §4.4 figures per SF, per-table numbers |
| `history_sweep/sf<N>/` | R2D8/R2D13 sweep analysis and plots |
| `num_draws/` | number-of-draws convergence: MCSE, ordering reproducibility, plot |
| `paper_figs/` | candidate paper figures on the display set (`sf<N>/`, `convergence/`) |
| `run_logs/` | chained capture log, memory/size monitor, downstream log and per-step logs, gzipped capture consoles |

## Not in git: the archive on the node

The files below are kept out of git to hold the repo to 147 MB. None of the figures read them.
They are on the Chameleon node, in one archive and also as loose originals:

- **Archive:** `/mnt/tpcds/results_rg128k/archive/rg128k_not_in_git.tar.zst`
  - 313 MB, from 8.5 GB raw, 3,300 entries
  - sha256 `7576e3f04148b201a22bcfd05207b4bbfc1d6954b74989260ff5b907e853aac3`
  - Paths inside are relative to `/mnt/tpcds/results_rg128k`, the same layout as this directory.
  - Checked with `tar --zstd -df` against the originals.
  - Extract with `tar --zstd -xf rg128k_not_in_git.tar.zst`.
- **Loose originals:** the same files under `/mnt/tpcds/results_rg128k/`.

| In the archive | Size raw | Needed for |
|---|---|---|
| `sf<N>/capture/rg/<q>.csv` | 62 MB | every row group each query read: the evidence behind `pruning.json` and the authored-query tables |
| `sf<N>/logs/tpcds_<q>/access.json`, `capture_summary.json` | 76 MB | input for recomputing VDI (`run_spark_sf.sh vdi`) |
| `sf<N>/vdi/data_val_rgs_tbls_{zipf,normal}_full.json` | 75 MB | the row-group/Full numbers in `sf_comparison.json` (`compare_sf.py`) |
| `sf<N>/eventlog/` | 0.5 / 0.97 / 2.72 GB | Spark physical plans and stages, for auditing |
| `sweep/` | 2.7 GB | the input to `history_sweep/` (`analyze_history_sweep.py --data-root`) |
| `draws_pool/` | 1.8 GB | the input to `num_draws/` and `paper_figs/convergence/` |

The node is a temporary Chameleon reservation. Copy the archive somewhere else before it ends.

## Regenerating the figures

Run from `oracle/scripts`, with `R=../../r2d7_results/rg128k`.

- **From this directory alone:** `sf<N>/figs`, `sec44_after/figs_sf<N>` and `paper_figs/sf<N>`.

  ```
  graph_comp_oracles.py [--distro zipf --ylim 1.0] [--tables "$DISP"] --tpcds-only \
      --data-dir $R/sf<N>/vdi --fig-dir <out>
  ```

  `DISP` comes from `select_display_tables.py $R`. I checked SF30 `paper_figs`, SF100 `figs` and
  SF100 `sec44_after` after slimming. They come out identical to the files here apart from the
  PDF creation date.
- **These also need `sweep/` or `draws_pool/` from the archive:**
  - `history_sweep/`
  - `num_draws/`
  - `paper_figs/convergence/`

  The exact commands are in `run_scripts/downstream.sh`.
