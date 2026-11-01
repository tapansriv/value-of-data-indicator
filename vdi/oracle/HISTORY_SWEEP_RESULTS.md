# Query-history size sweep — results note

**Answers:** R2D8, R2D13 ("does the 1500-query history size drive your results?")
**Lands in:** one sentence in §6 carrying the threshold; full sweep in the cover letter.
**Run:** 2026-09-13, branch `query_history_experiment`, single seed 42, Zipf task values,
100 draws, six history sizes. ~7 min local, no cluster, no budget.

## What was run

```
oracle/scripts/sweep_history.py --seeds 42 --distro both
oracle/scripts/analyze_history_sweep.py --distro zipf
```

N ∈ {100, 250, 500, 1000, 1500, 2000}. Everything else held fixed at the §4.4
configuration. Task values were **not** regenerated between points —
`generate_oracle_vals.py` draws one value per query per trial independently of N, so
every history size sees identical task values and all movement is attributable to
history size alone.

Histories are **nested**: at a fixed seed the draw for N=100 is a strict prefix of the
draw for N=2000, so a smaller N is the same workload observed for less time, not an
unrelated sample.

**Anchor check:** the sweep's N=1500 point is byte-identical to the committed §4.4
results in `oracle/data/` for all five compared files. The sweep is anchored to the
paper's actual numbers.

## Result 1 — rank stability

Spearman ρ of the per-table mean normalized value against N=2000, minimum across the
five distinct series (Full, Equal, Cardinality, Column, Row Group):

| N | distinct queries | min ρ (all 32 tables) | min ρ (7 figure tables) | min Kendall τ | top-3 overlap | top-5 overlap |
|---|---|---|---|---|---|---|
| 100 | 66/128 | 0.925 | 0.964 | 0.810 | 1.00 | 0.80 |
| 250 | 101/128 | 0.961 | 0.964 | 0.855 | 1.00 | 0.80 |
| 500 | 125/128 | 0.988 | 1.000 | 0.923 | 1.00 | 0.80 |
| 1000 | 128/128 | 0.996 | 1.000 | 0.964 | 1.00 | 0.80 |
| 1500 | 128/128 | 0.997 | 1.000 | 0.976 | 1.00 | 1.00 |
| 2000 | 128/128 | 1.000 | 1.000 | 1.000 | 1.00 | 1.00 |

**N\* = 250** over all 32 tables, at the ρ ≥ 0.95 threshold fixed before looking.
Over the seven tables the figures actually show, **N\* = 100** — the lowest size tested.
The top-3 tables are identical at every N.

The ranking is essentially converged well before 1500. The residual movement at small N
tracks coverage: at N=100 only 66 of 128 queries have been seen at all, and the tables
that move are low-value ones whose mutual order is noise.

## Result 2 — the §4.4 quantities

| N | date_dim access fraction | VDI share, Full | VDI share, Equal | normalized freq. share |
|---|---|---|---|---|
| 100 | 0.670 | 0.1613 | 0.1622 | 0.1634 |
| 250 | 0.644 | 0.1552 | 0.1551 | 0.1574 |
| 500 | 0.600 | 0.1501 | 0.1483 | 0.1489 |
| 1000 | 0.593 | 0.1440 | 0.1432 | 0.1438 |
| 1500 | 0.603 | 0.1453 | 0.1450 | 0.1445 |
| 2000 | 0.593 | 0.1431 | 0.1424 | 0.1422 |

All four are within ±0.005 of their N=2000 value **from N=1000 onward**.

Every ordering claim §4.4 makes holds at **all six** history sizes:
Cardinality's top table is `store_sales`; Column < Table and Row Group < Column for both
`store` and `date_dim`; Row Group < Table for `customer`.

## Result 3 — box spread does not come from history size

Mean 95% CI half-width across the seven figure tables under Equal is flat in N
(0.0107 at N=100 → 0.0098 at N=2000), as is mean IQR (0.050 → 0.048). The spread in
Figures 3 and 4 is driven by the 100 task-value draws, not by sampling noise in the
history. Growing the history does **not** narrow the boxes. (This contradicts the
expectation stated when the experiment was designed; recording it as the actual result.)

## Sentence this justifies

> VDI rankings are stable well below the history size we use: the table ranking at
> N = 250 already correlates with the ranking at N = 2000 at Spearman ρ ≥ 0.95 across
> all dividing strategies and granularities (ρ ≥ 0.99 by N = 500), and every ordering
> reported in §4.4 holds at every history size from 100 to 2000 queries. We use 1500.

## Figure corrections — applied 2026-09-13

Four issues were found while wiring the analysis. Items 1 and 2 have since been fixed in
`graph_comp_oracles.py` (approved); items 3 and 4 are prose and remain open.

1. **FIXED — Figure 3 and Figure 4 plotted the frequency baseline differently.**
   `graph_divide_comp` calls `collect_boris_data` without `normalized`, so it defaults to
   `False` and Figure 3's red line is the **raw access fraction** (0.603 for `date_dim`).
   `graph_granularity_comp` passes `normalized=True`, so Figure 4's markers are
   **normalized shares** (0.145). Same baseline, two different quantities, two figures.

2. **FIXED — the red line for the Customer column was the wrong table.** In both `plot_divide` and
   `graph_granularity_comp` the baseline is looked up as `labels[i].lower()`. `labels[1]`
   is hardcoded to `"Customer"`, which resolves to the **TPC-H** `customer` table, while
   the box above it is **`tpcds.customer`**. At N=1500 that is 0.105 plotted where 0.317
   belongs (raw), or 0.025 where 0.076 belongs (normalized) — a factor of three. Only the
   Customer column is affected; `date_dim`, `store_sales` and the rest resolve correctly.

3. **OPEN (prose) — "15–18%" does not match the current data.** §4.4 says `date_dim` "receives only
   15–18% of value under Full or Equal." At N=1500 the mean share is 14.5% (Full) and
   14.5% (Equal), medians 14.4% and 14.6%, IQRs 12.1–17.7% and 11.0–18.5%. The stated
   range does not correspond to the mean, the median, or the IQR. The figures appear to
   have been regenerated after the sentence was written. The **"60% of queries"** number
   is exactly right (0.603).

4. **OPEN (prose) — caption says 8 tables, figures show 7.** `subset_tables` has seven entries in both
   plotting functions; `"part"` is commented out. Both captions say "8 of 32 tables."

**What the fix changed.** `graph_divide_comp` now forwards `normalized`, so both figures
put the baseline on the boxes' scale; the baseline is looked up by table key rather than
by lowercased label; and `subset_tables` moved to a proportionally stratified sample of a
k=7 clustering over the five behaviours the figures display (the old set is retained,
commented out, in both plotters). The new set is `date_dim`, `store_sales`,
`tpcds.customer`, `lineitem`, `store`, `household_demographics`, `customer_demographics` —
it keeps every table Sec 4.4 names and reproduces the population's 3:1 skew toward
frequency assigning more share than VDI (19 of 31 tables), which the old set showed as 3:2.
`customer_demographics` stands in for the `income_band` the clustering picked first: same
trend (VDI/freq 0.584 vs 0.585, Full/Equal 1.445 vs 1.426) at 2.7x the value, which halves
the figure's dynamic range from 15.4x to 7.5x, and it fills a Fig 4 gap at
RowGroup/Table 0.97. The cost is that cluster 0 {`income_band`, `call_center`} goes
unrepresented — every member is too low-value to plot, which is itself worth a sentence in
the letter.

**Consequence for the prose:** under the corrected baseline `date_dim` is the closest
frequency/VDI agreement in the whole catalog (ratio 1.003), so it can no longer carry the
"frequency would overvalue it" claim. See the pending prose list in memory
(`vdi-figure-prose-updates`).

**Y-limit: resolved.** Both figures are now capped at 0.70, with any point above it marked
by a triangle at the axis edge labelled with its value, positioned over the series it
belongs to. Figure 3 hides one point (`store_sales`/Cardinality, 0.961) and Figure 4 one
(`store_sales`/RowGroup, 0.958); neither cuts a box, median or whisker.
Measured trade-off over the 2100 plotted points (7 tables x 3 strategies x 100 draws):

| ylim | points hidden | whiskers cut | boxes cut |
|---|---|---|---|
| 1.00 | 0 | 0 | 0 |
| 0.70 | 1 | 0 | 0 |
| 0.50 | 20 | 1 | 0 |
| 0.45 | 26 | 2 | 0 |
| 0.30 | 64 | 2 | 1 |

0.70 is the knee: it hides only the single `store_sales`/Cardinality point at 0.961 and no
summary statistic, and that point is marked at the axis edge. Below ~0.60 the
upper whiskers of `store_sales` (0.694) and `lineitem` (0.476) under Cardinality start
being cut, which removes the defining feature of that strategy. Note that 0.70 only buys
1.43x for the small tables; the `income_band` -> `customer_demographics` swap does more for
legibility than the limit does, and the remaining small-table gaps are best carried as
numbers in the cover letter rather than fought on the axis.

## Reproducing

Raw per-point results are gitignored (~60 MB per point). Regenerate with the two commands
above; each point's `manifest.json` records N, seed, trial count, distributions, query-set
size, coverage, and the git revision. Derived CSVs and figures are in
`oracle/data/sweep/analysis/`.

## Not yet done

- Single seed only. Five seeds (42–46) would separate "history of size N" from "this
  particular prefix" at ~40 min local. Worth doing before the sweep goes in the letter.
- The downstream-decision half of R2D8 — whether placement and sorting choices change
  with N — is a separate experiment in `clustering/` and `partitioning/`, which use
  hand-set task values rather than the 100 draws, and whose sorting side needs the
  Chameleon node.
