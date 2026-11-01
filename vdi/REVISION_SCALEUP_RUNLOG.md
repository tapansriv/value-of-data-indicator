# R2D16 scale-up — run log

Chronological record of what ran, what broke, how it was fixed, and what it cost. Plan and
rationale: `REVISION_SCALEUP.md`. Times are UTC (laptop log lines are CDT = UTC−5).
Account details are omitted on purpose (`spark-lineage-api/aws/SECRETS.md`).

## Morning summary (as of 12:20Z)

1. **Phase E passed** after four fixes, all found by the validation runs, none by luck:
   root-owned scratch dir (AMI), listener reacting to its own usage-log write, **instrumented
   Spark capturing only the last table of every join**, and **named accumulator blowing up
   driver memory/event logs** (O(tasks²)). The last two are Spark-fork bugs on new branch
   `rowgroup-dev-multiscan` (`2d7540e`, `0ad8dbc`) — **not merged into `rowgroup-dev`, not
   pushed**; they affect any row-group data from the Spark prototype so far, and R2D14.
2. **k = 0.55** (EC2 node ≈ 1.8 Chameleon nodes). Full {4, 8, 16} ≈ $146; N=1 adds 4.1 days
   and ~$85 — the §5.4 rule says run it. **Not started: N=4 and N=1 await your go.**
3. **Valid main runs** `n16-main2` (n16b) and `n8-main2` (n8b), AMI #7, started 07:03Z. All
   variants so far 22/22, no listener timeouts, no failures. n16b ≈ done 13:50Z; n8b ≈ 20:00Z.
4. **First signal (n16b rep 1):** per-query latency within noise for every variant
   (bare −0.5%, cols −3.6%, rowgroup −2.2% vs vanilla). `rowgroup` adds ~50 s/query of
   post-query listener work outside the timed window. Rep 2 gives the noise band.
5. **⚠ Old `n16`/`n8` still running** (invalid; my teardown was blocked) — see ACTION NEEDED.
6. AWS session (aws-vault) expires 15:06Z; after that my monitoring stops, the runs do not
   (results sync to S3 after every variant; dead-man switches bound cost). Renew with
   `aws-vault exec vdi --duration=12h -- true` if you want monitoring to continue.

## ~~ACTION NEEDED~~ — resolved 14:20Z

Old `n16` and `n8` (invalid first main runs) were torn down by Tapan at 14:18Z / 14:20Z with
`99_teardown.sh` (verified by listing; my earlier teardown had been blocked by the auto-mode
permission check). They ran 05:32–14:20 (~8.8 h): ≈ $64 (n16, 17 nodes) + $34 (n8, 9 nodes)
≈ **$98 spent on invalid runs**.

## Status at a glance

| | |
|---|---|
| Live clusters | **`n8b` only** (valid main run, ≈ done 19:10Z). Everything else torn down and verified. |
| AMI for main runs | **`ami-0a74b436b174b689b`** (build #7: Spark `rowgroup-dev-multiscan` **0ad8dbc** = multiscan + unnamed accumulator; listeners as vdi 3c38fa8) |
| Main runs | **`n16-main2` (n16b), `n8-main2` (n8b) started 07:03Z** (22 TPC-H × vanilla/bare/cols/rowgroup × 2 reps). `n16-main`/`n8-main` invalid (issue 4). N=4 and N=1 not started (Tapan's call) |
| Spend so far (approx.) | ~$4 |

## 2026-10-04/05 — stage 1, network (free)

- `00_network.sh`: security group (self-only inbound), S3 gateway endpoint, key pair. Verified,
  idempotent on re-run.

## 2026-10-05 01:17–03:52 — stage 2, AMI build (~$1.30)

| Build | Outcome |
|---|---|
| #1 `20261005-011732` | completed, then looked failed; builder terminated |
| #2 `20261005-015047` | same |
| #3 `20261005-022407` | same |
| #4 `20261005-030749` | **AMI `ami-0a153b2ee8a47ffd5`** (BUILD_OK written from the laptop) |

**Issue:** every builder powered off ~30 min after boot with no BUILD_OK marker, so the
laptop terminated it as failed. Chased unattended-upgrades, cloud-init and SSM credential
rotation (all red herrings). **Cause:** the build takes ~30 min; at the end `finish()` ran
`aws s3 cp` from a working directory the cleanup had just deleted, and the AWS CLI fails in a
deleted cwd (`[Errno 2]`, reproduced locally) while `shutdown` succeeds. **Fix:** `cd /`
before cleanup and in `finish()` (`7b9021c`). All builds had in fact passed every check;
their artifacts are in `s3://<results>/build/<id>/artifacts/`.

## 2026-10-05 04:06– — Phase E on `val` (4 × r7g.2xlarge + driver, $2.14/hr, 6h dead-man)

Cluster came up in 50 s; SSH over SSM works; `45_status.sh` all OK.

| Run | What | Result |
|---|---|---|
| `e-rgq-local` | rg_quick, rowgroup, local mode | 1st attempt failed: root-owned `spark-local` (fix 1) |
| `e-rgq-local` (retry) | same | 2/2 OK |
| `e-rgq-cluster` | rg_quick, rowgroup, cluster | 2/2 OK |
| compare | local vs cluster | orders identical (12,188 RGs); **join logged nothing** (fix 2) |
| `e-rgq2-local` / `-cluster` | rg_quick with fix-2 jars | **IDENTICAL**, but join shows `part` only (fix 3) |
| `e-kcal` | Q9, Q14, Q16, vanilla | 3/3 OK, 04:36–04:56; **k = 0.55** (below) |

**Fix 1** — `/home/ubuntu/spark-local` was root-owned on every node (baked into AMI #4 by
the builder's root smoke test); Spark could not create scratch dirs. `boot.sh` uses
`install -d -o ubuntu`; build cleanup deletes the dirs (`7c5799b`). Fixed live on `val`.

**Fix 2** — listener acted on its own usage-log write. The write inside `onSuccess` fires a
listener event ("command"); the next query's collector took it as its own, released the
driver latch early, and the last query's real event hit a stopped SparkContext (its row
groups lost). In a full run this would have overlapped usage-log writes with the next
query's timed window, for `cols` and `rowgroup` only. Listeners now ignore every event whose
action is not `"head"` (= `show()`) (`7c5799b`).

**Fix 3** — the instrumented Spark kept only the last Parquet scan's row-group accumulator
per query (`RowGroupMetricsRegistry.put` replaced; one accumulator per scan). Every join
reported one table. **Spark fix on new branch `rowgroup-dev-multiscan` (`2d7540e`) — not
merged into `rowgroup-dev`, not pushed; your call.** Listener merges all scans, dedups
row groups per query (`3c38fa8`). Affects all row-group data from the Spark prototype to
date, and R2D14's planned Spark runs.

### k calibration (`e-kcal`, 4 workers, vanilla, 1 rep)

| Query | EC2 (s) | Chameleon 4-node (s, mean of 2) | k |
|---|---|---|---|
| Q9 | 749.3 | 1446.5 | 0.52 |
| Q14 | 359.8 | 579.5 | 0.62 |
| Q16 | 63.1 | 109.5 | 0.58 |
| **sum** | | | **0.55** |

One r7g.2xlarge does the work of ~1.8 Chameleon nodes (storage difference folded in).
`budget_model.py --k 0.55`: N4 1.0 d, N8 0.5 d, N16 0.3 d; **$146** ($183 with 25%) for
{4, 8, 16}. With N=1: 4.1 d, $231 ($289) — the §5.4 rule (k ≤ 1.5) says run it; decision
left to Tapan.

Event log (`summarize_eventlog.py`): 4 executors, none removed, no speculative tasks, no
spill, driver peak heap 2.02 GiB. **cpu/run per query: Q9 0.54, Q14 0.30, Q16 0.47** —
tasks spend roughly half their time waiting on S3 already at 4 nodes. This is the §4.3
"masking" regime; compare the ratio at 8 and 16. Q9 shuffles 232 GB with no spill.

## 2026-10-05 04:21–05:18 — AMI rebuilds for the fixes (~$0.50)

| Build | Contents | Outcome |
|---|---|---|
| #5 `20261005-042142` | vdi 7c5799b (fixes 1–2), Spark rowgroup-dev | `ami-09aa516c863d93509` — **superseded, do not use** (no multiscan). First build to write its own BUILD_OK: the cwd fix works. |
| #6 `20261005-043536` | vdi 3c38fa8 (fixes 1–3), Spark **rowgroup-dev-multiscan 2d7540e** | **`ami-0857b9d82e7284686`** — all checks + 4-jar smoke OK; smoke join `nation ⋈ region` now logs **both** tables |

`cols` listener check on `val` (`e-cols`, rg_quick): 2/2 OK; usage log has one entry per
query with exactly the columns read (`orders.{o_orderdate,o_totalprice}`; the join:
`part.{p_brand,p_partkey,p_size}`, `partsupp.{ps_partkey,ps_supplycost}`). Step 3 passes.

`val` torn down 05:19 (verified by listing). `val2` launched 05:19 from build #6, 4 workers
in 33 s; `spark-local` owned by ubuntu at boot (fix 1 confirmed on fresh nodes).

## 2026-10-05 05:20–05:32 — multiscan validation on `val2`: PASS

| Run | Result |
|---|---|
| `e-rgq3-local` | 2/2 OK |
| `e-rgq3-cluster` | 2/2 OK |
| compare | **IDENTICAL**: orders 12,188 RGs; join **8,123 = part 1,624 + partsupp 6,499** (every row group of both tables), no duplicates |

This was the gate Tapan set for the main runs.

## 2026-10-05 05:32 — main runs launched (AMI `ami-0857b9d82e7284686`)

| Cluster | Nodes | Dead-man | Ready | Run id | Started |
|---|---|---|---|---|---|
| `n16` | 16 workers + driver | 20 h | 05:33:27 | `n16-main` | 05:33:47 |
| `n8` | 8 workers + driver | 30 h | 05:33:28 | `n8-main` | 05:34:11 |

Both on Spark `2d7540e` (checked `BUILD_INFO` on each driver). Settings: 22 queries
(`tpch22/`), variants vanilla, bare, cols, rowgroup; 2 reps, order reversed on rep 2;
executor 7 cores / 48g, driver 16g, AQE off, speculation off, exchange/subquery reuse off;
usage logs to `s3://<results>/runs/<run-id>/usage_logs/`. Expected (k = 0.55, ideal scaling):
n16 ~0.3 d, n8 ~0.5 d; S3-bound queries will scale worse.

Also running on `val2`: `e-rgc-local` (Q6, Q14, rowgroup, local mode), then `e-rgc-cluster`.

## 2026-10-05 06:04 — issue 4: named row-group accumulator; first main runs invalid

The health watcher flagged n16's driver heap at 80%. Not GC noise: old gen 85% live after
a full GC; `GC.class_histogram` showed **12.7 GB of `byte[]`** (strings), and the
`rep1/vanilla` event log was **13 GB after 18 of 22 queries** (n8: 6.3 GB). n16 heap
reached 14 GB of 16 GB a few minutes later.

**Cause:** `ParquetFileFormat` registers the accumulator with a *name*
(`register(acc, "RowGroupAccumulator")`). For named accumulators
`DAGScheduler.updateAccumulators` (line 1696) attaches `acc.value` — a copy of the whole
row-group map accumulated so far (`RowGroupAccumulator.scala:57`) — to every task-end
event; the status store and event log keep it as strings. O(tasks²) driver memory, a full
map copy per task on the scheduler thread, and event-log volume, **in every variant
including `vanilla`** (it is the engine, not the listener).

**Consequences:** the runs would likely have hit driver OOM and/or filled the 200 GB driver
disk with event logs; and the per-task driver work inflates every query's time by an amount
that depends on task count and N — a confound for R2D16. Partial `vanilla` CSVs kept in
`benchmarking/data/ec2/aborted-named-accumulator/` for reference only (n16: 16 queries,
n8: 8). **Do not use them.**

**Fix:** register unnamed (Spark `rowgroup-dev-multiscan` `0ad8dbc`). Unnamed accumulators
merge identically; the listener reads them via the registry. Does the old Chameleon data
have the same confound? Yes, if it ran this engine: the paper's existing 1- and 4-node
numbers include this per-task driver cost in all variants. Worth a sentence in §6.

Next: AMI build #7 (started 06:12) → validate on a small cluster (row groups identical, event
log small, driver heap flat) → relaunch n8/n16 main runs as `n8-main2` / `n16-main2`.

## 2026-10-05 05:32–06:24 — Phase E step 1, full check (Q6, Q14) on `val2`: PASS

| Run | Result |
|---|---|
| `e-rgc-local` | Q6, Q14 rowgroup, local mode: 2/2 OK, 38 min |
| `e-rgc-cluster` | same on 4 workers: 2/2 OK, 11 min |
| compare | **IDENTICAL**: Q6 48,372 RGs (= all of lineitem); Q14 49,996 (= lineitem 48,372 + part 1,624); no duplicates |

(`val2` ran AMI #6, which still has the named accumulator; naming changes driver overhead,
not which row groups are captured, so the correctness result carries over to #7.)
`val2` torn down 06:24, verified.

## 2026-10-05 06:38–07:04 — build #7, validation on `val3`, corrected main runs

- **Build #7** `20261005-060719` → **`ami-0a74b436b174b689b`**: Spark `0ad8dbc` (multiscan +
  unnamed accumulator). All checks and smoke tests passed; builder wrote BUILD_OK itself.
- **`val3`** (4 workers, 3h dead-man) launched 06:51 from #7.
  - `e-rgq4-cluster` vs. `e-rgq3-local`: **IDENTICAL** (orders 12,188; join 8,123 = part +
    partsupp). Unnamed registration does not change capture.
  - `e-kcal-rg` (Q9, Q14, Q16, rowgroup): during Q9 the event log grew linearly at ~1.4 MB/min
    (3.3 → 8.9 MB over 5 min; the named-accumulator build was at GBs), driver old gen flat
    ~35–39%, no full GC. Fix confirmed.
- **Old `n16`/`n8`**: `rep1/vanilla` failed on both (n16: `java.lang.OutOfMemoryError: Java heap
  space` after 19/22 queries; n8: 4 queries -1), as predicted. Still running, still invalid.
- **Main runs relaunched** from #7 as new clusters (old names still occupied):

| Cluster | Nodes | Dead-man | Ready | Run id | Started |
|---|---|---|---|---|---|
| `n16b` | 16 workers + driver | 20 h | 07:03:11 | `n16-main2` | 07:03:35 |
| `n8b` | 8 workers + driver | 30 h | 07:03:14 | `n8-main2` | 07:03:59 |

vCPUs in use: 456 of the 512 quota (incl. the old clusters and `val3`).

## Phase E — summary: all steps pass (07:18Z)

| Step | Check | Result |
|---|---|---|
| 1 | Row-group capture local vs cluster | **PASS** — rg_quick and Q6/Q14 IDENTICAL, all tables of each join, no duplicates (after fixes 2–3) |
| 2 | (folded into 1/3) | — |
| 3 | Listener ran: usage-log entry per query | **PASS** — `cols`: one entry per query with exactly the columns read; `rowgroup`: every query logged |
| 4 | k calibration | **k = 0.55** (`e-kcal`) |
| 5 | Event logs: executors, spill, speculation, CPU ratio, driver heap | **PASS** on build #7 — 4 executors, none removed, no spec, no spill; cpu/run 0.32–0.56 (S3-bound already at N=4); driver peak heap **0.48 GiB** for `rowgroup` on Q9/Q14/Q16; event log 40 MB for the 3 queries |
| 6 | Listener timeout | no timeouts in any run; 30-min limit kept (no listener came close; per-query listener time is not recorded separately) |

`e-kcal-rg` (rowgroup, build #7, 4 workers): Q9 739.3 s, Q14 353.0 s, Q16 68.1 s. Not
directly comparable with `e-kcal` (vanilla on build #4, which carried the named-accumulator
cost) — the main runs give the real variant comparison.

`val3` torn down 07:17, verified. Validation clusters `val`, `val2`, `val3`: all gone.

## Main-run progress

| Time (UTC) | Cluster | Event |
|---|---|---|
| 07:50 | n16b | `rep1/vanilla` done: **22/22 OK, 46.5 min**, event log 355 MB, no timeouts |
| 08:33 | n8b | `rep1/vanilla` done: **22/22 OK, 89 min** (1.9× n16b); projection 8 × ~89 min ≈ 11.9 h → done ~19:00Z (dead-man at 30 h) |
| 08:36 | n16b | `rep1/bare` done: **22/22 OK, 46.4 min** (vanilla 46.5); `rep1/cols` started |
| 09:23 | n16b | `rep1/cols` done: **22/22 OK, 47.0 min**, no listener timeouts; `rep1/rowgroup` started |
| 09:59 | n8b | `rep1/bare` done: **22/22 OK, 86.7 min** (vanilla 89.0); `rep1/cols` started |
| 10:27 | n16b | `rep1/rowgroup` done: **22/22 OK**, pass 63.4 min (see note); rep 2 started, order rowgroup→cols→bare→vanilla |
| 11:29 | n8b | `rep1/cols` done: **22/22 OK, 89.4 min**; `rep1/rowgroup` started |
| 11:30 | n16b | `rep2/rowgroup` done: **22/22 OK**, pass 63.7 min |
| 12:18 | n16b | `rep2/cols` done: **22/22 OK**, pass 47.5 min; `rep2/bare` started |
| 13:04 | n16b | `rep2/bare` done: **22/22 OK**, pass 45.7 min; final pass `rep2/vanilla` started |
| 13:06 | n8b | `rep1/rowgroup` done: **22/22 OK**, pass 97 min; **rep 1 complete (6.0 h)**; rep 2 started → done ≈ 19:10Z |
| 13:49 | n16b | `rep2/vanilla` done: **MATRIX COMPLETE — 8/8 passes, 176/176 queries, 0 failures, 0 listener timeouts**; results fetched; n16b torn down 13:52 (verified) |

n16b `rep1/vanilla` per-query (s): Q1 164, Q2 38, Q3 132, Q4 112, Q5 154, Q6 76, Q7 132, Q8 149,
Q9 171, Q10 115, Q11 30, Q12 107, Q13 45, Q14 83, Q15 169, Q16 17, Q17 261, Q18 294, Q19 92,
Q20 96, Q21 305, Q22 22. (Q9: 171 s at 16 workers vs 749 s at 4 → 4.4× for 4× nodes.)
Projection: 8 passes × ~47 min ≈ 6.3 h → n16b done ~13:20Z (dead-man at 20 h).

### n16b rep 1 — per-query runtimes (the metric) vs. pass wall time

Sum of per-query runtimes over the 22 queries (user-observed latency, `show()` return):

| | vanilla | bare | cols | rowgroup |
|---|---|---|---|---|
| sum (s) | 2765.9 | 2750.8 | 2666.0 | 2705.1 |
| vs vanilla | — | −0.5% | −3.6% | −2.2% |
| pass wall time (min) | 46.5 | 46.4 | 47.0 | **63.4** |

- **Latency overhead is within noise for every variant** after one rep (listeners even
  slightly faster; `vanilla`, run first on a fresh cluster, was 5–15% slower on Q1–Q7, which
  looks like warm-up). Rep 2 runs in reverse order and gives the noise band.
- **`rowgroup`'s pass is 17 min longer** because the listener's post-query work (collect
  ~50k row-group entries per query, write them to S3) runs after `show()` returns and before
  the next query: ~50 s per query, outside the timed window by design. Invisible to the user
  but a real driver/S3 cost; worth one sentence in §6 alongside the latency result. It also
  sizes the listener timeout: minutes at most, far under the 30-min limit (A11).

## N=16 result (`n16-main2`, 16 × r7g.2xlarge, AMI #7) — complete

`python3 benchmarking/scripts/overhead_summary.py benchmarking/data/ec2/n16-main2`:

| variant | rep1 (s) | rep2 (s) | mean (s) | rep-to-rep |
|---|---|---|---|---|
| vanilla | 2765.9 | 2690.0 | 2728.0 | 2.78% |
| bare | 2750.8 | 2711.7 | 2731.3 | 1.43% |
| cols | 2666.1 | 2690.1 | 2678.1 | 0.90% |
| rowgroup | 2705.1 | 2730.3 | 2717.7 | 0.93% |

| vs vanilla | relative | absolute | |
|---|---|---|---|
| bare | +0.12% | +151 ms/query | within noise (band 2.78%) |
| cols | −1.83% | −2.3 s/query | within noise |
| rowgroup | −0.38% | −0.5 s/query | within noise |

Per-query rep-to-rep difference (vanilla): median 4.0%, max 16.3%.

**This is pre-registered outcome A** (`REVISION_SCALEUP.md` §4.3): listener overhead on
user-observed latency is indistinguishable from run-to-run noise at 16 nodes. Report it as
"within noise", with the band, not as "zero overhead".

Event logs (summarized on the driver, `data/ec2/n16-main2/eventlog_summary.txt`): 16
executors in every pass, none removed; driver peak heap 0.51–0.96 GiB; mean cpu/run over
queries 0.47 (vanilla), 0.47 (bare), 0.49 (cols), 0.48 (rowgroup) — the listeners do not
change how I/O-bound the cluster is. `rowgroup` passes were ~17 min longer than the others
because of post-query listener work outside the timed window (see n16b rep 1 note).

Raw results committed (CSVs, run_info, metadata, matrix.log; 184 KB). Event logs and driver
logs stay in `s3://<results>/runs/n16-main2/` (`data/ec2/.gitignore`).

## 14:40Z — output validation of `n16-main2`: lineage is wrong for some queries (issues 5, 6)

`benchmarking/scripts/validate_run.py data/ec2/n16-main2 tpch22` (usage logs synced from S3):

| Check | Result |
|---|---|
| completion (176/176, no timeouts) | pass |
| query answers identical across all 8 passes | **pass, 22/22** — listeners do not change results |
| `rowgroup` usage log | **18/22** per rep; Q13, Q18, Q21, Q22 wrong |
| `cols` usage log | **12/22** per rep |

**Issue 5 — stale row-group capture (parquet-java fork).** `RowGroupFilter.java` keeps the
capture in a `ThreadLocal` (`lastResult`, line 63) that is set only on the filtered path
(line 140); the no-filter visits (145–151) return without setting it and nothing clears it.
Spark reads it after opening each file (`ParquetFileFormat.scala:308`). An executor thread
that read a filtered split (e.g. `orders` with `o_orderstatus='F'`) and then an *unfiltered*
split of another table logs the first table's row groups under the second's path. Matches
every failure (Q13 customer > 1,217; Q22 orders = customer's 1,217; Q18/Q21 lineitem >
48,372), nondeterministic across reps. Phase E's queries happened not to hit it.
Fix: set the result on the no-filter visits (all blocks accepted) and clear it in Spark
before each `initialize`.

**Issue 6 — `cols` listener lineage.** It uses `attr.qualifier.last`, which is the alias
(`profit`, `c_orders`, `revenue0`, `n1`, `l1`, `custsale`, …) rather than the base table,
and `qe.analyzed.collect` does not descend into subquery plans, so tables used only in
`EXISTS` / `IN` / `NOT IN` / `NOT EXISTS` are missed (Q4, Q16, Q20, Q22).
Fix: resolve attributes to base relations through the plan's `LogicalRelation`s
(by `exprId`), including subqueries.

**What this does and does not affect.** Timings: the timed window covers the query only;
issue 5 changes which labels the listener writes, issue 6 how many rows — both in post-query
listener work outside the window. The N=16 latency result stands as measured. Lineage: the
row-group/column usage data the prototype produces is not trustworthy for multi-table
queries — matters for the VDI artifact and R2D14. Both issues predate this experiment.

## 14:40Z — fixes for issues 5 and 6; full rerun planned on build #8 (Tapan's decision)

| Fix | Where | Commit |
|---|---|---|
| Record "all blocks read" on every unfiltered path, so the thread-local capture is never stale | parquet-java, **new branch `vod_rg-capturefix`** (from `vod_rg`) | `6519501` |
| Clear the capture before and after each reader `initialize` | Spark `rowgroup-dev-multiscan` | `4ba4a96` |
| `cols` listener: base tables via optimized-plan `LogicalRelation`s by exprId, incl. subqueries | `listener_versions_new/LineageAPI.scala` | `9dc0732` |
| Harness `--rep-only K` (one rep per cluster) | `aws/node/run_matrix.sh` | `9dc0732` |

Neither fork branch is merged into its main branch or pushed.

**Plan (Tapan, 14:35Z): rerun all of N ∈ {1, 4, 8, 16} on build #8**, with N=1 and N=4 each
split across two clusters (one rep each). `n8b` (`n8-main2`, old build) keeps running as a
cross-check. Variant order for every size: rep 1 `cols rowgroup vanilla bare`, rep 2
reversed. Gate: `n16c` starts first; after its rep-1 `cols` and `rowgroup` passes,
`validate_run.py` must pass before the other clusters launch.

| Cluster | Workers | Run id | Reps | Dead-man |
|---|---|---|---|---|
| `n16c` | 16 | `n16-v3` | 1, 2 | 20 h |
| `n8c` | 8 | `n8-v3` | 1, 2 | 30 h |
| `n4a` / `n4b` | 4 each | `n4-v3-r1` / `n4-v3-r2` | 1 / 2 | 30 h |
| `n1a` / `n1b` | 1 each | `n1-v3-r1` / `n1-v3-r2` | 1 / 2 | 72 h (extend with `25_extend.sh`) |

vCPUs with `n8b`: 392 of 512.

## 15:22Z — build #8 and the validation gate

- **Build #8** `20261005-143754` → **`ami-0ddfe14707a2f05d7`**: Spark `4ba4a96`, parquet-java
  `6519501` (`vod_rg-capturefix`), vdi `9dc0732`. All checks + smoke tests passed. Smoke join
  `nation ⋈ region`: `cols` now logs base tables `nation` {N_NAME, N_REGIONKEY}, `region`
  {R_NAME, R_REGIONKEY}; `rowgroup` one row group each. Note: `cols` now records the
  **physical** column names from the parquet schema (upper-case in this dataset), where the
  old listener recorded the names as written in the SQL. Validator prefix check made
  case-insensitive.
- **`n16c`** (16 workers, 20 h) up 15:22; **`n16-v3`** started 15:22:46, rep 1 order
  `cols rowgroup vanilla bare`. Gate: `validate_run.py` on rep-1 `cols` (~16:10Z) and
  `rowgroup` (~17:15Z) before launching n8c / n4a / n4b / n1a / n1b.

## 17:15Z — gate PASSED; all sizes launched on build #8

`validate_run.py data/ec2/n16-v3 tpch22` after rep-1 `cols` and `rowgroup`:
**cols 22/22, rowgroup 22/22** (Q13/Q18/Q21/Q22 now correct; were 12/22 and 18/22),
answers identical across passes **and identical to build #7's answers** for all 22 queries.

| Cluster | Workers | Run id | Reps | Dead-man | Started |
|---|---|---|---|---|---|
| `n16c` | 16 | `n16-v3` | 1, 2 | 20 h | 15:22 |
| `n8c` | 8 | `n8-v3` | 1, 2 | 30 h | 17:18 |
| `n4a` / `n4b` | 4 each | `n4-v3-r1` / `n4-v3-r2` | 1 / 2 | 30 h | 17:18 |
| `n1a` / `n1b` | 1 each | `n1-v3-r1` / `n1-v3-r2` | 1 / 2 | 72 h | 17:18 |
| `n8b` (old build, cross-check) | 8 | `n8-main2` | 1, 2 | 30 h | 07:03 |

All on AMI `ami-0ddfe14707a2f05d7`, variant order rep 1 `cols rowgroup vanilla bare`, rep 2
reversed. Expected finish (k = 0.55): n16c ≈ 22:10Z today; n8c ≈ 06:00Z tomorrow; n4a/n4b
≈ 06:00Z tomorrow; n1a/n1b ≈ 2 days (≈ 10-07 18:00Z; extend dead-man with `25_extend.sh` if
needed). n8b ≈ 19:10Z today.

## 19:10Z (2:10 pm CDT) — `n8-main2` (n8b, build #7 cross-check) complete

8/8 passes, 176/176 queries, no failures or listener timeouts. n8b torn down 19:17Z, verified.

| vs vanilla (mean of 2 reps) | relative | absolute | |
|---|---|---|---|
| bare | −0.98% | −2.3 s/query | within noise (band 2.08%) |
| cols | −0.10% | −0.2 s/query | within noise |
| rowgroup | +0.16% | +0.4 s/query | within noise |

Pass sums (s): vanilla 5316.9 / 5207.4, bare 5172.4 / 5248.7, cols 5208.0 / 5305.5,
rowgroup 5233.0 / 5308.3. Vanilla per-query rep-to-rep: median 2.3%, max 25.7%.
Event logs: 8 executors every pass, none removed; driver peak heap 0.52–1.24 GiB.
Validation: answers identical in all 8 passes; lineage shows the known build-#7 bugs
(cols 12/22, rowgroup 19/22 and 20/22 — nondeterministic, as expected for issue 5).
**Cross-check only**; the 8-node result for the paper is `n8-v3` (build #8).

## 20:39Z (3:39 pm CDT) — issue 7: 1-node worker disk full; n1 relaunched with 1.5 TB

Health ALERT: n1b worker disk 100% (191 GB in `spark-local`), Q8 failing with
`java.io.IOException: No space left on device`; n1a at 63% on the same query and bound to
follow. At N=1 every shuffle lands on one worker. One pass shuffles **1.28 TB** in total
(from the n16 event logs; Q9 232 GB, Q8 174 GB, Q17 168 GB, Q21 134 GB, Q5 131 GB), and
shuffle files are only deleted once the driver garbage-collects the query's objects
(periodic GC default 30 min), so at N=1 they accumulate faster than they are removed.
N≥4 spreads the same volume over ≥4 disks; n4b completed a full pass without a disk warning.

Fix: tear down n1a/n1b (20:41–20:42, verified; ~3.4 h of progress lost, ~$6) and relaunch as
**`n1c` / `n1d` with a 1,500 GB root volume** (`VDI_ROOT_GB=1500`): enough for a full pass
with no cleanup at all. gp3 IOPS (6,000) and throughput (300 MB/s) unchanged, so the
storage configuration matches every other size except capacity, which does not affect gp3
performance. No Spark setting changed. Extra gp3 cost ≈ $50 over the run.

| Cluster | Workers | Disk | Run id | Reps | Dead-man | Started |
|---|---|---|---|---|---|---|
| `n1c` | 1 | 1.5 TB | `n1-v3b-r1` | 1 | 72 h | 20:44Z |
| `n1d` | 1 | 1.5 TB | `n1-v3b-r2` | 2 | 72 h | 20:44Z |

Expected finish ≈ 10-07 23:00Z (6 pm CDT Wed). The `n1-v3-r1/r2` partial results in S3 are
abandoned (new run ids, so nothing mixes).

## 22:11Z (5:11 pm CDT) — **N=16 final (`n16-v3`, build #8) complete**

8/8 passes, 176/176 queries, no failures or listener timeouts. n16c torn down, verified.
**`validate_run.py`: PASS** — cols 22/22 and rowgroup 22/22 in both reps; answers identical in
all 8 passes.

| variant | rep1 (s) | rep2 (s) | mean (s) | rep-to-rep |
|---|---|---|---|---|
| vanilla | 2651.1 | 2757.8 | 2704.4 | 3.94% |
| bare | 2684.0 | 2777.5 | 2730.7 | 3.42% |
| cols | 2722.1 | 2709.8 | 2716.0 | 0.45% |
| rowgroup | 2736.6 | 2776.2 | 2756.4 | 1.44% |

| vs vanilla | relative | absolute | |
|---|---|---|---|
| bare | +0.97% | +1.2 s/query | within noise (band 3.94%) |
| cols | +0.43% | +0.5 s/query | within noise |
| rowgroup | +1.92% | +2.4 s/query | within noise |

Vanilla per-query rep-to-rep: median 6.1%, max 27.2%. Event logs: 16 executors every pass,
none removed; driver peak heap 0.47–1.21 GiB. Unlike the build-#7 run (n16-main2), all
listener variants are slightly *above* vanilla here, rowgroup most; still inside the noise
band, so report the numbers as measured with the band, not as "zero".

## 05:00Z (midnight CDT) — **N=4 final (`n4-v3` = n4a rep 1 + n4b rep 2, build #8) complete**

n4a (`n4-v3-r1`) done 04:58Z, n4b (`n4-v3-r2`) done 05:00Z; both torn down, verified.
Each: `validate_run.py` PASS (cols 22/22, rowgroup 22/22, answers identical); 4 executors every
pass, none removed; driver peak heap ≤ 0.97 GiB. Merged into `data/ec2/n4-v3`
(`MERGED_FROM.txt`); merged validation PASS (answers identical in all 8 passes).

| variant | rep1 (s, n4a) | rep2 (s, n4b) | mean (s) | rep-to-rep |
|---|---|---|---|---|
| vanilla | 10399.0 | 10450.1 | 10424.5 | 0.49% |
| bare | 10322.0 | 10238.3 | 10280.2 | 0.81% |
| cols | 10347.4 | 10414.0 | 10380.7 | 0.64% |
| rowgroup | 10422.0 | 10476.2 | 10449.1 | 0.52% |

| vs vanilla | relative | absolute | script verdict (band 0.81%) |
|---|---|---|---|
| bare | **−1.38%** | −6.6 s/query | "OUTSIDE noise" |
| cols | −0.42% | −2.0 s/query | within noise |
| rowgroup | +0.24% | +1.1 s/query | within noise |

Vanilla per-query rep-to-rep: median 2.5%, max 20.0%.

**Interpretation caveat.** `bare` is *faster* than `vanilla` in both reps, which cannot be
listener overhead (`bare` does strictly more work). The 2-rep band (rep-to-rep difference of
pass sums) **underestimates true run-to-run variation**: slow drift across a ~12 h run (S3
performance, time of day) shifts whole passes, and two reps cannot capture it. Across sizes
the `bare` delta changes sign (N=4 −1.4%, N=16 +1.0%; build-#7 runs N=8 −1.0%, N=16 +0.1%),
which is the signature of noise. For §6: state that every variant's overhead is within about
±2% at every size, with mixed sign, and show per-query spread — not a precise per-variant
band from 2 reps. `overhead_summary.py`'s "OUTSIDE noise" verdict should be read with this
in mind.

## 05:32Z (12:32 am CDT) — **N=8 final (`n8-v3`, build #8) complete**

8/8 passes, 176/176 queries; `validate_run.py` PASS (cols/rowgroup 22/22 both reps, answers
identical in all 8 passes); 8 executors every pass, none removed; driver peak heap ≤ 1.06 GiB.
n8c torn down 05:38Z, verified.

| variant | rep1 (s) | rep2 (s) | mean (s) | rep-to-rep |
|---|---|---|---|---|
| vanilla | 5318.6 | 5283.5 | 5301.0 | 0.66% |
| bare | 5319.7 | 5252.8 | 5286.3 | 1.27% |
| cols | 5209.9 | 5296.5 | 5253.2 | 1.65% |
| rowgroup | 5415.0 | 5313.3 | 5364.2 | 1.89% |

bare −0.28% (−0.7 s/query), cols −0.90% (−2.2 s/query), rowgroup +1.19% (+2.9 s/query);
all within the 1.89% band. Vanilla per-query rep-to-rep: median 1.7%, max 10.6%.

## Summary so far — build #8, overhead on user-observed latency vs vanilla

| N | vanilla pass (s, mean) | bare | cols | rowgroup | 2-rep band |
|---|---|---|---|---|---|
| 4 | 10424.5 | −1.38% | −0.42% | +0.24% | 0.81% |
| 8 | 5301.0 | −0.28% | −0.90% | +1.19% | 1.89% |
| 16 | 2704.4 | +0.97% | +0.43% | +1.92% | 3.94% |
| 1 | running (n1c / n1d) | | | | |

Every listener variant is within about ±2% of vanilla at N = 4, 8, 16, with mixed sign; no
monotone trend with N. Pre-registered **outcome A**. `rowgroup` is the only variant above
vanilla at every N (+0.2 to +1.9%) — small, inside noise at each size, but consistent in
direction; worth stating rather than hiding. Vanilla pass time scales near-linearly
(4→8: 1.97×, 8→16: 1.96×).

## 10-06 13:40Z (8:40 am CDT) — handoff point (laptop restart)

**Live:** only `n1c` (`n1-v3b-r1`, rep 1) and `n1d` (`n1-v3b-r2`, rep 2), 1 worker each,
1.5 TB disks, AMI #8, 72 h dead-man (fires ≈ 10-08 20:44Z / 3:44 pm CDT Thu). Each was in its
2nd of 4 passes at 13:18Z; expected finish ≈ 10-07 19:00Z (2 pm CDT Wed).
**Done:** N=16, 8, 4 on build #8 (see summaries above); all other clusters torn down.

To resume monitoring (from `spark-lineage-api/`):

    aws/monitor/watch_all.sh    n1c:n1-v3b-r1 n1d:n1-v3b-r2
    aws/monitor/watch_health.sh n1c:n1-v3b-r1 n1d:n1-v3b-r2

When both report MATRIX COMPLETE:

    aws/monitor/finish_run.sh  n1c n1-v3b-r1
    aws/monitor/finish_run.sh  n1d n1-v3b-r2
    aws/monitor/merge_split.sh n1-v3 n1-v3b-r1 n1-v3b-r2
    (cd benchmarking && python3 scripts/overhead_summary.py data/ec2/n1-v3 \
        && python3 scripts/validate_run.py data/ec2/n1-v3 tpch22)

aws-vault session valid until 10-07 01:18Z (8:18 pm CDT); renew with Tapan present
(`aws-vault clear vdi && aws-vault exec vdi --duration=12h -- true`).

## 10-06 — forks and branches merged (Tapan's decision)

| Repo | Branch | Now at | How |
|---|---|---|---|
| `tapansriv/spark` (public) | `rowgroup-dev` | `7de9151` | fast-forward to `4ba4a96` (R2D16 fixes), then `-s ours` merge of upstream `1fb30a5` (R2D7's independent fix of the same bugs): code identical to `4ba4a96`, `1fb30a5` kept in history |
| `tapansriv/parquet-java` (public) | `vod_rg` | `6519501` | fast-forward (stale-capture fix) |
| `TheDataStation/value-of-data-metric` (private) | `main` | `e556c21` | `spark-scale` merged (`add5396`) + note in `r2d7_results/BUILD_NOTES.md` |

The temporary branches `rowgroup-dev-multiscan` / `vod_rg-capturefix` and their worktrees
were deleted after merging. `10_build_ami.sh`'s defaults (`rowgroup-dev`, `vod_rg`) now build
the fixed code. Listeners built against the new Spark tip must use
`RowGroupMetricsRegistry.getAll` (main's listener does). The R2D16 results cite `4ba4a96`;
R2D7's cite `1fb30a5`; both are reachable from `rowgroup-dev`.
