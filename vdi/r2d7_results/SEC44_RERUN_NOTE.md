# §4.4 rerun on the R2D7 Spark data — figures, history sweep, number of draws

**Answers:** R2D7 (scale factors), R2D8/R2D13 (query-history size), and the implicit
"why 100 draws?" question. **Run:** 2026-09-27/28, local, no cluster, about 45 min of
CPU time. Branch `r2d7-sec44`.

Three pieces, all built from `r2d7_results/sf{30,60,100}` (TPC-DS only, 99 queries,
Spark capture):

| Piece | Where |
|---|---|
| Frozen July-submission numbers and figures ("before") | `sec44_before/` (see its README) |
| Rerun figures and numbers ("after"), plus the side-by-side comparison | `sec44_after/` |
| Query-history sweep, N = 100…2000 × 5 seeds × 3 SFs | `history_sweep/sf<N>/` |
| Number-of-draws convergence study | `num_draws/` |

The pipeline reproduces the remote node's `sf30/vdi` byte for byte for Zipf. Normal
differs only at the last float digit (≤4e-16 relative, x86 vs ARM).

**Column-parser fix, 2026-10-07.** Everything below was rerun after fixing the substring bug
in `tpcds_parse_columns_from_query.py` (see `RESULTS_NOTE.md` → Known caveats). Same capture,
same values, same seeds; derived outputs overwritten in place, pre-fix versions in git at
`6bbf534`. Numbers below are post-fix; "pre-fix" marks the old value where it moved.
- Row-group granularity is unaffected: Zipf row-group outputs and the row-group frequency
  baseline are byte-identical; Normal differs ≤4.2e-16 relative (the same x86/ARM noise).
- `date_dim` access fraction is unchanged (0.885); table granularity moves only through
  queries 16/94/95 (`promotion`) and 44 (`store`); column granularity moves broadly.
- Biggest move: `date_dim` Column/Equal median 18.4% → 15.5%, column frequency 17.0% → 14.0%.

---

## 1. Before → after (`sec44_after/before_after_compare.csv`)

Median share over the 100 draws. Before = Drill, TPC-H+TPC-DS, SF30. After = Spark,
TPC-DS only. Table- and column-granularity values do not depend on SF, so one "after"
column covers them.

| | Before | After |
|---|---|---|
| `date_dim`, Full / Equal | 14.4% / 14.6% | 18.2% / 19.4% (pre-fix 17.9% / 19.3%) |
| `date_dim` access fraction (share of queries) | 0.60 | 0.89 (no TPC-H queries dilute it) |
| `store_sales`, Cardinality | 27% | 57% (SF30/60/100: 56.8/56.8/56.5%; unchanged by the fix) |
| `store_sales`, Row Group | 26% | 48 / 50 / 51% |
| `date_dim`, Row Group | 0.2% | 3.5 / 2.1 / 1.3% |
| `date_dim`, Column / Equal | — | 15.5% (pre-fix 18.4%) |
| VDI(Equal)/frequency, `store_sales` | 0.93 | 1.16 (pre-fix 1.15; frequency now *under*values it) |
| VDI(Equal)/frequency, `date_dim` | 1.01 | 1.08 (1.076; pre-fix 1.081) |
| VDI(Equal)/frequency, `household_demographics` | 0.43 | 0.61 (0.607; pre-fix 0.612) |

**What this means for the prose (`metric.tex` §4.4). Nothing has been edited yet.**
- "`date_dim` is accessed by 60% of queries": now 89%.
- "15–18%": neither Full (18.2%) nor Equal (19.4%) falls in the range any more
  (pre-fix, Full at 17.9% did).
- "`store_sales`'s 700" row groups: now 29 / 58 / 96 at SF30 / 60 / 100, because the new
  Parquet uses 128 MiB row groups. That change is why `date_dim`'s row-group share rose
  roughly 17×.
- "99 TPC-DS and 22 TPC-H queries", "8 of 32 tables": now 99 TPC-DS queries only, and
  the figures show 6 of 24 tables.
- The orderings the prose claims still hold. Column < Table < … for `store` and
  `date_dim`, Row Group < Table for `customer`, and Cardinality's top table is
  `store_sales` at every SF.

**Figure settings changed for the "after" figures.** They are rendered with
`--ylim 1.0` (new flag; default 0.70 is unchanged). On the Spark data, 0.70 hides 18
points and cuts the `store_sales` whisker; on the Drill data it hid 1 point and cut
nothing. At 1.0 nothing is hidden. **Open:** the 6-table display set is the Drill-era
set minus `lineitem`. The clustering rationale behind it was computed on the Drill data
and has not been redone.

---

## 2. Query-history sweep (`history_sweep/`)

The design is the same as the 2026-09-13 Drill sweep (`oracle/HISTORY_SWEEP_RESULTS.md`):
- task values fixed per SF;
- nested histories, so a smaller N is a prefix of the larger one;
- N ∈ {100, 250, 500, 1000, 1500, 2000}.

Now with **5 seeds (42–46)** instead of 1, and at all three SFs. The ρ ≥ 0.95 and
±0.005 thresholds were carried over from the first sweep.

**Rank stability** (Spearman ρ of per-table mean share vs the same seed at N=2000):

| N | SF30 mean over seeds, worst series | SF30 worst single seed | SF60 | SF100 |
|---|---|---|---|---|
| 100 | 0.952 | 0.904 | 0.904 | 0.904 |
| 250 | 0.971 | 0.951 | 0.951 | 0.951 |
| 500 | 0.983 | 0.965 | 0.968 | 0.976 |
| 1000 | 0.991 | 0.980 | 0.983 | 0.983 |
| 1500 | 0.995 | 0.988 | 0.994 | 0.995 |

(Pre-fix the N=100 and N=250 worst single seed were 0.918 and 0.957 / 0.958 / 0.970.)

(The SF60 and SF100 columns are the worst single seed, all 24 tables.)

On the 6 displayed tables, almost every deviation is one adjacent swap (ρ = 0.943),
between `customer_demographics` and `household_demographics`. Their shares are
1.4% vs 1.7%, and that swap persists to N=1000–1500 for a few seeds. The exceptions are
at N=100, where SF60 drops to 0.83 and SF100 Row Group to 0.77. From N=250 every series at
every seed is at or above 0.943.

**§4.4 quantities.** The `date_dim` Full and Equal shares and the frequency share stay
within ±0.005 of their N=2000 value from N=1000 onward (Full and frequency from N=500).
Unchanged by the parser fix. The access fraction joins them
from N=1500. Those three shares reach ±0.018 at N=100.

**Prose claims.** Every ordering claim holds at every N and seed. (Pre-fix, `date_dim`
Column < Table failed at N=100 seed 43 and N=250 seed 46; the false `d_date` credits had
inflated `date_dim`'s column share.) The "15–18%" range claim fails at almost every point.

**Box spread does not come from history size.** The mean 95% CI half-width of a table's share
is flat in N: 0.0047–0.0048 averaged over all 24 tables, 0.0071–0.0072 over the 6 displayed
tables, at every N and SF (`history_sweep/sf<N>/sweep_summary.csv`, column `ci95_halfwidth`).
An earlier "0.009" here could not be reproduced from the outputs and has been removed. This
replicates the Drill result: the spread in the boxes comes from the task values, not from the
history.

**Bug fixed along the way.** The old "within ±0.005 from N=X onward" line reported the
smallest N at which *any* point was inside the band, not the N from which all larger N
stay inside it. It also compared against the seed-averaged reference. Both are fixed in
`analyze_history_sweep.py`. The single-seed Drill note is unaffected, because with one
seed its "from N=1000 onward" statement is still true.

**Sentence this supports:** VDI table rankings at a 250-query history already correlate
with the 2000-query ranking at ρ ≥ 0.95 at every seed and scale factor (worst 0.951 post-fix,
so this now holds with almost no margin). The §4.4 shares
move less than half a percentage point beyond 1000 queries. We use 1500.

---

## 3. How many task-value draws? (`num_draws/`, `oracle/scripts/draws_convergence.py`)

**Method.** Draw a pool of 2000 Zipf(2.0) task-value vectors (seed 20260927, independent
of the paper's draws). Push the pool through the unchanged pipeline (N=1500, history
seed 42). Then, for K ∈ {10…1000}, resample 2000 experiments of K draws and measure how
much each displayed box statistic moves: its Monte Carlo standard error (MCSE). Three
checks back up the resampling:
- **Independent blocks.** Splitting the pool into 20 disjoint blocks of 100 draws gives
  20 independent reruns of the paper's experiment. Their spread matches the bootstrap
  MCSE (median ratio 0.91–0.94; pre-fix 0.97).
- **1/√K scaling.** MCSE falls as K^−0.51 (fitted slope −0.47 to −0.59). Shares are
  bounded, so the CLT applies even though Zipf(2) has an infinite mean.
- **Where the paper's draws sit.** The seed-42 set of 100 draws lies within |z| ≤ 2.79 of
  the pool medians (pre-fix 2.85). The largest offsets are `customer` Cardinality and Row
  Group (z ≈ −2.5 to −2.8).

**Criteria, fixed in the script's docstring before the run:**

| Criterion | At K=100 | K needed |
|---|---|---|
| C1: MCSE of every displayed median ≤ 0.5 pp | **Fails for 3 of 30 medians**: `store_sales` Cardinality (1.35–1.38 pp), `store_sales` Row Group (1.25–1.31 pp), `store_sales` Column (0.60 pp; pre-fix 0.56). The other 27 are ≤ 0.42 pp; the typical one is 0.15–0.16 pp. | between 500 (worst 0.62) and 1000 (0.44) |
| C2: every displayed ordering with a gap ≥ 1 pp reproduced in ≥ 95% of experiments | **Passes**: 43 orderings per SF, worst reproduced 98.2–99.1% (pre-fix 41–42, 97.3–98.0%) | 100 |
| C3: Spearman ρ ≥ 0.95 vs the pool in ≥ 95% of experiments | **Passes**: 100% (≥ 99% even at K=10) | 10 |

In relative terms, every displayed median's MCSE at K=100 is 7.5–9.6% of its box's IQR (unchanged),
so the Monte Carlo wobble is under a tenth of the box height. The orderings not
reproduced at K=100 all have pool gaps under 0.5 pp (e.g. `store` Full vs Equal, 0.09
pp). Those are genuine ties, and the prose already treats them as "similar".

**Conclusion.** 100 draws is enough for everything the figures are used to argue: the
orderings, the rankings, and "Full ≈ Equal". It is **not** enough to quote `store_sales`'s
Cardinality or Row Group median closer than about ±2.7 pp. There are two defensible
fixes:
- **(a) Keep K=100.** Report the `store_sales` Cardinality and Row Group numbers with
  ±2.7 pp, or quote the pool medians.
- **(b) Move to K=1000.** All three criteria pass there (worst MCSE 0.44 pp). Compute is
  not the obstacle: a 2000-draw pool took about 15 minutes per SF on a laptop. The
  drawback is that the boxplots gain about 10× more outlier dots, so fliers should be
  thinned or the whiskers switched to 5–95%.

Either way, one cover-letter sentence carries it: "With 100 draws, every ordering we
report with a gap ≥ 1 pp is reproduced in ≥ 97% of independent repeats; Monte Carlo
error on the medians is at most 0.42 pp except for `store_sales`, whose widest boxes carry
±1.35 pp."

---

## Reproducing

```
cd oracle/scripts
R=../../r2d7_results
# figures + numbers
python graph_comp_oracles.py --distro zipf --tpcds-only --ylim 1.0 --data-dir $R/sf30/vdi --fig-dir $R/sec44_after/figs_sf30
python sec44_summary.py --data-dir $R/sf30/vdi --tpcds-only --label spark_sf30 --out $R/sec44_after/sec44_numbers_spark_sf30.csv
# history sweep (~10 min per SF; raw outputs gitignored under oracle/data/sweep/)
python sweep_history.py --seeds 42 43 44 45 46 --distro zipf --no-plots --tpcds-only \
  --logs-dir $R/sf30/logs --values-dir $R/sf30/values --columns-in-queries $R/sf30/tpcds_columns_in_queries.json \
  --cardinality $R/sf30/tpcds_cardinality.json --query-set $R/common_completed_sf30_60_100.json \
  --data-root ../data/sweep/r2d7_sf30 --fig-root ../figs/sweep/r2d7_sf30
python analyze_history_sweep.py --tpcds-only --data-root ../data/sweep/r2d7_sf30 --out-dir $R/history_sweep/sf30
# draws study (builds pools if missing, ~15 min per SF; then ~1 min)
python draws_convergence.py
```
