# Spark Scale-Up Experiment — Execution Plan (R2D16)

Overhead of the VDI listener as the Spark cluster grows — **4, 8 and 16 nodes**
(1 node optional, §5.4) — on TPC-H at **1TB**, extending the 1- and 4-node results
already in the paper (`fig:tpch_1tb`, `fig:tpch_1tb4` in
`vod_paper2/sections/evaluation.tex`).

Companion to `../REVISION_PLAN.md` (priorities and framing) and
`../REVISION_EXPERIMENTS.md` (specs for all revision runs). Those two live outside
version control because `value_of_data/` is not itself a git repo; this file lives
here because the code changes it describes land in this repo.

Deadline **2026-11-01**. Written 2026-09-13; revised 2026-09-26 (platform moved to
EC2 + S3, run matrix trimmed, budget added).

---

## 0. Working plan

Decided 2026-09-26. Each row links to the section with the reasoning.

| | Decision | § |
|---|---|---|
| Platform | EC2, **r7g.2xlarge** (8 vCPU Graviton3, 64 GiB), us-east-2, on-demand | §5 |
| Storage | **S3 read directly**; HDFS only as a measurement-triggered fallback | §4 |
| Workload | TPC-H SF1000, **22 standard queries** | §5.3 |
| Configurations | **4**: `vanilla`, `bare` (listener only), `cols`, `rowgroup` | §5.3 |
| Repetitions | **2** — the minimum that shows the noise band the result will sit in | §1.5 |
| Node counts | **{4, 8, 16} committed**; N=1 gated on the measured k | §5.4 |
| Budget | **~$270-530**, ~$330-660 with contingency; longest size 2-4 days | §5.3 |

**Sequence:**

| Step | What | Cost |
|---|---|---|
| 1 | Phase A — code changes | local, free |
| 2 | Account prerequisites — admin runs `aws/iam/vdi-spark-scale-setup.yaml`; Tapan requests the vCPU quota | admin, free — **long pole** |
| 3 | Phase B — build once, bake an ARM AMI | 1-2 builder-hours |
| 4 | Phase D — **done**: TPC-H SF1000 already in `s3://vod-tpch-1tb`, verified | — |
| 5 | Phase E — validation + k calibration | a few dollars |
| 6 | Phase F — the run, sizes in parallel | the budget above |
| 7 | Phase G — analysis, §6 prose | local |
| 8 | Then: sorting in Spark, placement (R2D14 / R3W1 / R3D1) | separate clusters |

**Why overhead first** still holds: it is the simplest driver of the three — submit a
query file, time it, no placement simulation or cache hierarchy — so it is the
cleanest end-to-end proof that the custom Spark plus the row-group accumulator work
distributed at all, and it is the only experiment that exercises 16 nodes.

On EC2 the earlier Chameleon-era ordering worries (a fixed reservation window, one
shared 16-node reservation) no longer apply: each experiment gets its own on-demand
cluster, and sizes run in parallel. Data staging still does not transfer between
experiments — overhead is TPC-H, sorting and placement are TPC-DS
(`clustering/queries/tpcds*`, `partitioning/queries/tpcds*`) — so settle the S3 prefix
layout for both datasets up front.

---

## 1. Findings from the code and existing data

### 1.1 The accumulator design survives distribution

`ParquetFileFormat.scala:208` calls `sparkContext.register(acc, "RowGroupAccumulator")`
on the driver, and `acc.add(...)` (~`:317`) sits **inside** the closure handed to
executors. `RowGroupAccumulator.scala` implements `merge` correctly. That is the
standard, correct `AccumulatorV2` pattern: executor-side updates merge back to the
driver at task completion.

Row-group capture therefore needs **validation** at 8/16 nodes, not redesign — the
experiment is not blocked on an instrumentation rewrite.

Residual risk: `RowGroupMetricsRegistry.remove(execId)` clears the local map but
never unregisters from `AccumulatorContext` (weak refs, so GC handles it). Driver
memory pressure grows with the number of concurrent tasks merging in — which is
precisely what rises with node count. Watch driver heap at 16.

### 1.2 Every listener variant hardcoded `.master("local[*]")` — **FIXED**

`.master()` in code beats `--master` on spark-submit. Left as-is, a 16-node submit
would silently run single-node and produce a null result that looks real.

Removed from all 13 sites across `listener_versions/` (6) and
`listener_versions_new/` (7), replaced with a comment explaining why it must stay
unset. `spark-submit` defaults to `local[*]` when `--master` is omitted, so
single-node behaviour is unchanged. `src/main/scala/LineageAPI.scala` still contains
the line and was deliberately left alone — `compile.sh` overwrites it from
`listener_versions_new/` on every build.

### 1.3 The existing 4-node data lives on the `cluster` branch (now `legacy_results/cluster/`)

Absent from `main`, present only on `cluster`, which is why it first looked lost. As of
2026-09-27 that branch is archived on `main` under `legacy_results/cluster/`. Full
inventory of all six result branches: `spark-lineage-api/benchmarking/data/MANIFEST.md`
and `inventory.csv` beside it.

- **Generating script:** `legacy_results/cluster/spark-lineage-api/benchmarking/scripts/plot_spark_internal_tpch.py:123`
  writes `figs/tpch_node4_1tb.pdf`.
- **Raw inputs:** the top-level `spark_internal_listener_*_results.csv` on `cluster`,
  all six variants: 37 TPC-H queries x 2 reps, written in one clean run
  (`fa422157`, 2025-11-16) and byte-frozen since.
- **Run configuration** (from the `cluster` scripts): `--master spark://controller:7077`,
  `--executor-cores 30`, `--executor-memory 45g`, `--driver-memory 4g`, on nodes with
  Intel Xeon E5-2650 v3 @ 2.30GHz (Haswell) and 64GB RAM.

No committed file records the node count; "4 nodes" rests on commit subjects and the
figure filename. Since all node counts are now rerun on EC2, this only matters if the
old figure itself is cited — confirm against the Chameleon reservation record first.

### 1.4 No unmodified-Spark baseline — now a deliberate scope choice

`vanilla` and stock Spark measure different things: `vanilla` is the *instrumented*
build with no listener registered, isolating listener cost; stock Spark 3.5.5 isolates
the cost of carrying the fork. The old 4-node run had only the former.

The working plan (§0) keeps it that way — four listener configurations, no stock-Spark
arm. It therefore measures **listener overhead at scale, not the cost of the
instrumented engine itself**.

**Decided 2026-09-27: stock Spark is not rerun.** The paper keeps the stock-Spark
implementation and numbers it already reports; the 4/8/16-node runs add listener
overhead only. §6 must say which comparison each figure makes. (Adding it back would
have cost ~25% more, `budget_model.py --configs 5`.)

### 1.5 At 4 nodes, listener overhead is the same size as run-to-run noise

Measured on the `cluster` data (`budget_model.py --derive` reproduces it):

| | Rep-to-rep difference |
|---|---|
| per query, median | 0.8-1.3% |
| per query, worst | up to 8.2% |
| whole 22-query pass | 0.1-0.9% |

| Variant | Overhead vs `vanilla` (q1-22, mean of 2 reps) |
|---|---|
| `bare` | **-1.0%** |
| `cols` | -0.2% |
| `rowgroup` | +0.3% |

`bare` came out 1% *faster* than `vanilla`: the differences are inside the noise. Two
consequences:

- **One rep cannot support any claim about these deltas.** Two is the minimum that
  shows the noise band; hence 2 reps in the working plan.
- The likely finding is not "overhead falls with scale" but **"overhead stays within
  run-to-run noise at every cluster size"** — see the revised hypothesis in §4.3. This
  is Chameleon local-disk data; S3 may shift it, which is why it is pre-registered as
  one of two outcomes rather than assumed.

---

## 2. Phase A — Code changes (local, free)

| # | Change | Where | Status |
|---|---|---|---|
| A1 | Remove hardcoded `.master("local[*]")` | 13 sites, both listener dirs | **done** |
| A2 | `loadData` used `java.io.File.listFiles` — driver-local POSIX only; now the Hadoop `FileSystem` API | 6 files in `listener_versions_new/` | **done** |
| A3 | `regex_prefix` hardcoded `file://` + absolute path; table name now from the basename | `LineageAPI_rgs.scala`, `UsageCollector` | **done** |
| A4 | Usage-log sink path | `cols` + `bare` listeners, run scripts | **done** (code fix 2026-09-27) + pass an `s3a://` path |
| A5 | Executor sizing for r7g.2xlarge | `aws/node/run_matrix.sh` | **done** 2026-10-04 (driver 16g, see §9) |
| A6 | Pin `spark.speculation=false` | `run_matrix.sh` + baked `spark-defaults.conf` | **done** 2026-10-04 |
| A7 | Let `loadData` accept directory-per-table, to avoid an S3 prefix hotspot | `loadData` | **only if Phase E shows throttling** |
| A8 | One query at a time: `cols` and `bare` wait for their listener before the next query, as `rowgroup` already did | `LineageAPI.scala`, `LineageAPI_bare.scala` | **done** 2026-10-04 |
| A9 | Usage-table existence check / creation moved out of the timed window | `LineageAPI.scala`, `LineageAPI_bare.scala` | **done** 2026-10-04 |
| A10 | Query listing sorted and `.sql`-filtered | all six variants | **done** 2026-10-04 |
| A11 | Bounded listener wait (30 min), flag-and-continue | `rowgroup`, `cols`, `bare` | **done** 2026-10-04; **re-evaluate the limit after Phase E** |

**What "overhead" means here (decided 2026-10-04).** The metric is **user-observed query
latency**: the timer runs from just before `spark.sql` to the return of `show()`. Listener
work that runs after results are returned (column extraction, row-group processing, the
usage-log write) is not seen by the user and is deliberately **outside** the timed window.
§6 must state this definition.

**A8.** Previously `cols` and `bare` stopped the timer and immediately unregistered the
listener. Spark delivers `QueryExecutionListener` events asynchronously, so the listener
could be removed before its event arrived (its work silently never ran), and when it did
run its work could overlap the next query's timed window. Now every listener-bearing
variant counts down a `CountDownLatch` in `onSuccess`/`onFailure` (in `finally`), and the
driver awaits it after stopping the timer. Timed runtime is unchanged in definition; the
gap between queries is now the same for all variants: one query in flight at a time, each
query starting only after the previous one's listener has finished. Failed queries now
write `-1` in `cols` and `bare` too, matching `vanilla` and `rowgroup`.

**A9.** `cols` and `bare` ran `fs.exists(usageTablePath)` (and on the first query, the
empty-table write) between `startTime` and the query, so every query's timing included at
least one storage round trip, against S3, that `vanilla` and `rowgroup` did not pay. That
setup now runs once before the query loop.

**A11.** The A8 wait was unbounded: one dropped listener event would hang the run, and
the cluster with it, until the dead-man's switch fired. The wait is now
`await(LISTENER_TIMEOUT_MIN = 30, MINUTES)`. It bounds only the post-query listener work,
not the query, which has already returned. On timeout the driver prints a `WARNING` and
moves on, and the row's new `listener_timeout` column is `true`. **Treat a flagged query
and the one after it as suspect for that rep and rerun them** (the next one may have run
alongside the late listener). Results CSVs are now `query,dataset,runtime,listener_timeout`
in all four matrix variants (`vanilla` always `false`, kept for a uniform schema). 30 min is
a placeholder: set it from the slowest listener time measured in Phase E, with a wide
margin.

All six variants compile (`mvn -o compile`, 2026-10-04).

**A2/A3 (applied 2026-09-13).** `loadData` resolves the source through
`new Path(path).getFileSystem(spark.sparkContext.hadoopConfiguration)` and enumerates
with `fs.listStatus`, yielding fully-qualified URIs so executors resolve exactly what
the driver enumerated rather than relying on `fs.defaultFS`. Sorted for deterministic
registration order. The query-file listing stays on `java.io.File` — query files are
local to the driver; only the data moved.

A3 replaced the regex with `new Path(filePath).getName.stripSuffix(".parquet")`. The
old prefix `"file://" + absolutePath` was sensitive not just to the scheme but to how
Hadoop qualifies a local URI (`file:/x` vs `file:///x`); any mismatch made
`.split(prefix)(1)` throw `ArrayIndexOutOfBoundsException`, reported by `onSuccess`'s
caller as a generic "Query failed" — silent loss of all row-group lineage. The basename
is also what `loadData` registers each view as, so the two agree by construction.

All six variants compile against the custom Spark in the local `~/.m2` (`mvn compile`,
Java 17, Scala 2.13). `org.apache.hadoop.fs.Path` resolves transitively through the
`provided` `spark-sql_2.13` dependency; `pom.xml` needed no change. Both changes are
scheme-agnostic: the same code serves `s3a://`, `hdfs://` and local paths.

**A4 — corrected 2026-09-27.** This was earlier described as config-only; that was wrong
for two variants. `LineageAPI.scala` (`cols`) and `LineageAPI_bare.scala` **ignored the
path argument** and hardcoded `/tmp/iceberg/warehouse/usage_logs`, resolving it with
`FileSystem.get` on the default filesystem. On a multi-node cluster the usage-log write
runs as a distributed job, so each executor would write its task output to its own
node's `/tmp` and the driver's commit would fail or lose rows; an `s3a://` path would
also have thrown "Wrong FS". **Fixed:** both now take `args(3)`, like `rowgroup`, and
resolve the filesystem from the path. All six variants compile. `nowrite`, `vanilla` and
`register` write no usage logs. Pass an `s3a://` path in the run scripts. The Iceberg
warehouse config (`file:///tmp/iceberg/warehouse`) is only used for `sourceType=iceberg`,
which these runs don't use. **Decide deliberately** where the log goes (open decision, §11): written
to S3 it crosses the network and becomes part of the measured overhead, and it is the
component most likely to be masked at high node counts (§4.3).

**A5.** Starting values to validate in Phase E, not final:

- Driver on its own node, `--driver-memory 4g` as on `cluster`. The `50g` in the older
  single-node scripts was a `local[*]` setting where driver and executor share one JVM.
- One executor per worker: `--executor-cores 7` (one core left for the OS and the
  worker daemon), `--executor-memory 48g` (plus Spark's default ~10% overhead, leaving
  headroom in 64 GiB), `--total-executor-cores 7N`.
- Keep these identical at every N — only the worker count may vary.

**A6.** Speculative re-execution double-counts into the accumulator, inflating
row-group counts. Off by default; pin it explicitly — it bears on the correctness of
the metric, not just performance.

**A7.** `loadData` requires one file per table, so `lineitem` is one 214 GB S3 object and
every read at 16 nodes hits one key under one prefix — where S3's per-prefix request
ceiling (~5,500 GET/s) could bite. The data is **already staged** that way
(`s3://vod-tpch-1tb`, §6), so this is now conditional: watch for S3A `503 SlowDown`
throttling in Phase E step 3. Only if it appears, accept a directory per table in
`loadData` (a small change now that it uses the `FileSystem` API) and rewrite `lineitem`
into many objects. Spark already splits the single file across tasks by row group
(48,372 of them), so parallelism is not the concern — request rate is.

**Not changed — `QueryRunner.scala`** still uses `java.io.File` for data discovery. It is
not built by `compile.sh` and not on the benchmark path; it will not work against
`s3a://` or `hdfs://` if anyone revives it.

---

## 3. Phase B — Build once, bake an AMI

Build order is fixed; Spark resolves parquet-hadoop from `~/.m2`:

1. Thrift 0.16.0 from source (`./configure --disable-libs && sudo make install`)
2. `parquet-java` @ `vod_rg`:
   `MAVEN_OPTS="--add-opens java.base/java.lang=ALL-UNNAMED" mvn clean install -pl parquet-hadoop -DskipTests`
3. `spark` @ `rowgroup-dev`: `./dev/change-scala-version.sh 2.13`, then
   `./dev/make-distribution.sh --name vod-rg --tgz -Pscala-2.13 -DskipTests`
4. `spark-lineage-api/compile.sh` -> the listener JARs
5. `hadoop-aws` 3.3.4 and its pinned AWS SDK bundle into the distribution's `jars/`

Then snapshot the builder as an AMI and terminate it. Every node at every cluster size
boots from that one image — this replaces the Chameleon-era "build once, rsync 15
times" and is better for reproducibility. Copy the built artifacts to S3 as a backup.

**Graviton is ARM (aarch64).** Build on a Graviton builder so the AMI matches.
`spark-setup/setup.sh` downloads `cs-x86_64-pc-linux.gz`, which will not run there —
use the aarch64 Coursier build and an aarch64 JDK 17. Everything else is JVM; snappy-java
and zstd-jni ship aarch64 native libraries.

**Two traps in the existing docs:**

- `setup.sh` and `spark/README_rg.md` stop at `mvn install`, which builds into the source
  tree — enough for `local[*]`, not for a standalone master/workers deployment. The
  `make-distribution.sh` tarball is what goes in the AMI as `SPARK_HOME`.
- `benchmarking/README.md` instructs downloading stock Apache Spark 3.5.5. That must
  *not* be `SPARK_HOME`, or the instrumentation is absent and every variant collapses
  onto `vanilla` — a clean-looking zero-overhead result.

---

## 4. Phase C — Storage: S3 *(decided 2026-09-26)*

**Object storage (S3) read directly by the EC2 Spark cluster.** HDFS is a documented
fallback (§4.4), triggered only by the Phase E measurement.

This supersedes an earlier decision in this file for HDFS on Chameleon bare metal. That
decision rested on S3 egress cost and data locality — both on-prem arguments that do not
survive the move to EC2: in-region S3<->EC2 transfer is free, and a large instance's
network bandwidth is in the same league as its local NVMe.

| Option | At 16 nodes | |
|---|---|---|
| NFS from one node | single server saturates; measures the NFS box, not the listener | disqualifying |
| Replicate 1TB per node | perfect locality, but 16 stagings and an unrealistic deployment | rejected |
| HDFS co-located on compute | bandwidth scales with N, but *storage changes along the measured axis* | fallback only |
| **S3 read directly** | storage identical at every node count; durable across teardown | **chosen** |

The methodological fact underneath: **the slower the storage, the smaller the measured
listener overhead appears**, because an I/O-bound scan hides listener CPU in I/O wait.
That does not disqualify S3 — it determines what has to be said about the result
(§4.2, §4.3).

S3A setup:

- **`hadoop-aws` 3.3.4**, matching `hadoop.version` in the Spark fork's `pom.xml`, with the
  AWS SDK bundle version that POM pins. Mismatch fails at runtime as `NoSuchMethodError`.
- **`fs.s3a.experimental.input.fadvise=random`** — required for Parquet; the sequential
  default over-reads badly on columnar range requests.
- **Raise `fs.s3a.connection.maximum`** (default 96) and `fs.s3a.threads.max` together; at
  16 nodes the default exhausts and surfaces as a hang, not an error.
- **IAM instance profile**, not static keys; **S3 gateway VPC endpoint** so traffic never
  leaves the VPC.
- Spread keys across prefixes (A7) to stay under the per-prefix request ceiling.

### 4.1 Why S3 over HDFS on EC2

- **Teardown economics.** On instance storage the data dies with the instances. In S3 it
  persists at ~$23/month and the cluster is disposable — no re-staging 1TB at every
  bring-up, no paying to keep idle nodes alive.
- **It decouples storage from the measured axis.** With HDFS co-located on compute,
  changing N changes the storage system at the same time as the compute. With S3 the
  storage layer is byte-identical at every node count and only parallelism varies.
- **It closes the prototype gap more completely.** R2D14 / R3W1 / R3D1 complain about
  prototype-vs-evaluation mismatch; the prototype is Spark/Databricks + Unity Catalog,
  which reads object storage.
- **One staging serves all three experiments** — placement explicitly wants an
  S3 + local-cache hierarchy (`REVISION_EXPERIMENTS.md` §3.2).
- **Reproducible for artifact evaluation** — a bucket is something a reviewer can point at.
- Less setup: no namenode, no formatting, no re-balancing at each cluster size.

### 4.2 The one thing HDFS wins, and why it is not disqualifying

HDFS co-scaled with compute keeps the cluster **compute-bound at every node count**,
because aggregate read bandwidth grows with N. With S3 the endpoint bandwidth is fixed
while demand grows, so at 16 nodes the scan may become I/O-bound where at 4 it was not,
and listener CPU then hides in I/O wait.

That is a real effect, but it is **in scope rather than a confound**: blob storage plus
elastic compute is the common deployment, so measuring in that regime is measuring what
people actually run. The requirement it creates is disclosure, not avoidance (§4.3).

### 4.3 Pre-registered hypothesis

Stated **before the runs**, following the "predict the direction before running"
convention in `REVISION_EXPERIMENTS.md` §2. This matters more than usual because both
likely outcomes *flatter* VDI; a pre-registered prediction plus absolute numbers is what
makes the result defensible rather than post-hoc.

**Two outcomes are pre-registered**, because §1.5 shows the 4-node overhead is already
at the noise floor:

| Outcome | What it looks like | Answer to R2D16 |
|---|---|---|
| **A. Within noise at every size** *(most likely, per §1.5)* | variant deltas stay inside the rep-to-rep band at 4, 8 and 16 | "overhead remains within run-to-run noise at every cluster size" — the absolute numbers and the noise band carry the argument, not a trend |
| **B. Decreasing with scale** | a measurable overhead at 4 that shrinks at 8 and 16 | "the trend continues, and overhead becomes less significant at scale" — needs the mechanism analysis below |

Outcome A is a complete answer and arguably a stronger one. It must be reported as
"indistinguishable from noise", with the noise band shown — not as "zero overhead".

**For outcome B, two mechanisms produce the same downward curve:**

| | Mechanism | What it says |
|---|---|---|
| **Amortization** | listener cost is largely per-query and driver-side — plan walk, accumulator merge, log write — so a roughly fixed cost is a smaller fraction of a larger total | a scaling property **of the VDI design**; ours to claim |
| **Masking** | listener CPU disappears into I/O wait because the cluster is storage-bound | a property **of S3**; not ours to claim |

Both must be addressed in §6 when describing why overhead decreases. They are separable
with data already being collected:

1. **Report absolute overhead (ms) alongside relative (%).** Flat absolute per-query
   listener cost with a falling percentage is amortization, unambiguously. A reviewer
   shown only percentages cannot tell the two apart and will reasonably suspect masking.
2. **`executorCpuTime / executorRunTime`** per stage, from Spark's task metrics. A
   declining ratio as N grows means the cluster is becoming I/O-bound — masking is in
   play; a flat ratio means it is not.
3. **The variant ladder** (`bare` -> `cols` -> `rowgroup`) decomposes where listener cost
   sits. If the write-bearing variants converge toward `bare` at 16 nodes, the log write
   specifically is being masked.

**Honest framing for §6 under B:** state that overhead declines with scale, give the
absolute figures, and say explicitly that part of the relative decline reflects the
cluster becoming storage-bound at high node counts — itself representative of
production object-store deployments. Do not claim pure amortization unless (2) shows a
flat CPU ratio.

### 4.4 If HDFS is needed after all

Hydrate HDFS from S3 at cluster start as a run-time cache layer — roughly 15 minutes of
bring-up, paid per session. Trigger is the Phase E check, not preference. Settings if
used: Hadoop 3.3.4, `dfs.replication=2` uniform across node counts (at N=1 the block
stays under-replicated — `fsck` warns, reads unaffected), `dfs.datanode.data.dir` on
instance storage, not the root volume. **S3 remains the durable copy either way.**

---

## 5. Platform and budget

### 5.1 Node choice: r7g.2xlarge

8 vCPU Graviton3, 64 GiB, **$0.4284/hr** on-demand in us-east-2 (published list price —
not verified live, since the `tapan` IAM user lacks `pricing:GetProducts`; re-check
before spending). 16 nodes ≈ **$165/day**, ~$175/day with the driver node.

Compared with the Chameleon nodes behind the existing data (Xeon E5-2650 v3, 64GB):
memory is identical, so executor memory settings carry over directly. Per core,
Graviton3 (2021, every vCPU a full physical core) is clearly stronger than Haswell
(2014) — roughly 1.5-2x on JVM-style workloads, plus far higher memory bandwidth; a
ballpark, not a benchmark. Whether one r7g.2xlarge matches one Chameleon node depends
on that node's socket count: `--executor-cores 30` on `cluster` implies at least 30
logical CPUs, which points to dual-socket (20 cores / 40 threads).

### 5.2 The model

`spark-lineage-api/benchmarking/scripts/budget_model.py` — regenerate every number in
this section with it; `--derive` recomputes its reference inputs from `legacy_results/cluster/`.

- **Reference:** one full 22-query TPC-H SF1000 pass of one variant took **5.64 h** on
  the 4-node Chameleon cluster (7.62 h for all 37 queries). The four variants agree
  within ~1%.
- **k** = throughput of one Chameleon node / one r7g.2xlarge. Unknown until measured;
  plausibly 1-2 (≈1 if the Chameleon nodes were single-socket, ≈1.5-2 if dual).
- Node-hours per pass = 5.64 x 4 x k; wall time at N = passes x that / N; one driver node
  per cluster size for its whole wall time.
- **Assumes ideal scaling** (optimistic at 16). **Excludes** reruns, data staging, the AMI
  build — the script adds 25% contingency for those.

The binding constraint is the **calendar, not the cost**. Within an instance family,
price scales linearly with size, so total cost is set by the amount of work; node size
only changes how long it takes.

### 5.3 Working plan: 22 queries x 4 configs x 2 reps, {4, 8, 16}

`python budget_model.py`:

| k | N=4 | N=8 | N=16 | Longest | Cost | With 25% |
|---|---|---|---|---|---|---|
| 1 | 1.9 d | 0.9 d | 0.5 d | 1.9 d | $266 | $332 |
| 1.5 | 2.8 d | 1.4 d | 0.7 d | 2.8 d | $399 | $498 |
| 2 | 3.8 d | 1.9 d | 0.9 d | 3.8 d | $532 | $664 |

Sizes run in parallel, so calendar time is the longest single size. How the trim was
reached, for the record:

| Plan | N=1 wall (k=1-2) | Cost (k=1-2) |
|---|---|---|
| 37 queries x 7 configs x 3 reps, {1,4,8,16} | 27-53 days | $1.5-3.0k |
| 22 queries x 5 configs x 2 reps, {1,4,8,16} | 9-19 days | $0.5-1.0k |
| **22 queries x 4 configs x 2 reps, {4,8,16}** | — | **$0.27-0.53k** |

- **22 vs 37 queries:** the other 15 in `tpch_queries_spark/` are custom extras, not
  TPC-H. `--queries 37` adds ~35%.
- **4 configs:** the four the paper's existing plot script shows. Dropped: `register`,
  `nowrite`, and the stock-Spark baseline (§1.4).
- **2 reps, not 1:** §1.5 — one rep cannot distinguish the deltas from noise.

### 5.4 N=1 is optional, gated on the measured k

`python budget_model.py --nodes 1 4 8 16`:

| k | N=1 wall | Cost | With 25% |
|---|---|---|---|
| 1 | 7.5 d | $420 | $526 |
| 1.5 | 11.3 d | $631 | $788 |
| 2 | 15.0 d | $841 | $1,051 |

N=1 adds only ~$150-300 but quadruples the calendar time — it is the only point that
threatens the schedule. Dropping it costs the argument little:

- **R2D16 does not need it.** The reviewer asked whether the trend continues *past* the
  4-node result; 4 -> 8 -> 16 on one identical setup answers that directly.
- **The paper already has a single-node figure** (`fig:tpch_1tb`). It came from a
  different setup (`local[*]`, node-local disk) and cannot sit on the new trend line
  either way; it stays as the single-node result, with scale-out as a separate study.
- **Outcome A survives without it** — "within noise at 4, 8 and 16" is complete.

**Decision rule:** after measuring k in Phase E, run N=1 only if it would finish with
about two weeks left before 2026-11-01 for prose; if so, **start it first**, since it is
the long pole. Rough guide: if setup takes about a week, runs start around 2026-10-03
and N=1 lands between 2026-10-10 (k=1) and 2026-10-18 (k=2) — so **run N=1 if k is
about 1.5 or lower.** The setup week is an estimate; replace it with the real start
date once §9's prerequisites clear. If dropped, §6 says the scale-out study starts at
4 nodes.

### 5.5 Quota

Running {4, 8, 16} in parallel is 28 workers + 3 drivers = 31 r7g.2xlarge = **248 vCPUs**
(264 with N=1). Graviton falls under the Running On-Demand Standard instances quota.
New accounts are often well below this and increases can take days — check it first
(§9).

---

## 6. Phase D — Data: already in S3 *(verified 2026-09-26)*

TPC-H SF1000 is already staged in **`s3://vod-tpch-1tb`** (us-east-2, SSE-S3, uploaded
2025-12-02), one parquet file per table — exactly the layout `loadData` expects. Every
table's footer row count matches the SF1000 spec exactly:

| Table | Rows | Row groups | Size |
|---|---|---|---|
| lineitem | 5,999,989,709 | 48,372 | 214 GB |
| orders | 1,500,000,000 | 12,188 | 64 GB |
| partsupp | 800,000,000 | 6,499 | 45 GB |
| part | 200,000,000 | 1,624 | 6.2 GB |
| customer | 150,000,000 | 1,217 | 12 GB |
| supplier | 10,000,000 | 81 | 0.8 GB |
| nation / region | 25 / 5 | 1 / 1 | — |

About 343 GB in total. Nothing to generate or upload. The nodes get **read-only**
access to this bucket (`aws/iam/`); results go to a separate bucket.

**TPC-DS (`s3://vod-tpcds-1tb`) is out of scope here, but broken for later:**
`item.parquet` has the full schema and **0 rows** (expected ~300,000). Most TPC-DS
queries join `item`, so the Spark sorting and placement runs would silently return
empty or wrong results until it is regenerated. `reason.parquet` has 75 rows against an
expected 65, but that expected value is unconfirmed. Every other TPC-DS table matches
spec.

---

## 7. Phase E — Validation and calibration (mandatory, before any 1TB run)

**1. Accumulator correctness.** On the same `s3://vod-tpch-1tb` data, run the `rowgroup`
variant over 2-3 selective, cheap queries (e.g. Q6, Q14) twice: once in `local[*]` on a
single node, once on a 4-node cluster. The set of (file, row-group) pairs the accumulator
reports must be identical. If it isn't, capture is broken distributed and every number
afterwards is invalid while looking entirely plausible. Same data and same query in both
modes, so no separately stored "known values" are needed.

**2. Calibrate k.** Once the 1TB data is in S3, run a handful of representative queries
(a short one, a medium one, and a heavy one such as Q9, Q18 or Q21) on a 4-node
r7g.2xlarge cluster and compare against the per-query times already in hand from the
4-node Chameleon run. About $1.71/hr, under $10 total. Feed the result to
`budget_model.py --k <measured>` and apply the §5.4 N=1 rule. The measured k folds in
the storage difference (local disk vs S3) as well as CPU; that is fine, because k is only
for budgeting — the paper compares new runs with each other, never with the old ones.

**3. Is the scan I/O-bound?** Run one query at 4 nodes and at 16 (and 1, if N=1 runs)
and compare `executorCpuTime / executorRunTime` per stage, plus any S3A throttling the
client reports.

- **Flat ratio** -> compute-bound at 16; S3 direct is correct.
- **Declining ratio** -> becoming I/O-bound at high N. Not a reason to abort — it is the
  representative production regime (§4.2). It *is* a reason to say so in §6 and, if
  outcome B materialises, to consider §4.4 HDFS hydration as a cross-check at 16.

Record the ratio either way; it is the evidence behind the §6 sentence.

### Phase E log (2026-10-05, cluster `val`, 4 × r7g.2xlarge + driver)

Findings so far, each fixed before any main run:

1. **`/home/ubuntu/spark-local` root-owned** on every node (baked into AMI #4 by the
   builder's root smoke test); Spark could not create scratch dirs. `boot.sh` now uses
   `install -d -o ubuntu`; build cleanup removes the dirs. Fixed live on `val` with chown.
2. **Listener reacted to its own usage-log write.** The write inside `onSuccess` fires a
   listener event ("command"); the *next* query's collector took it as its own, released the
   driver latch early, and the last query's real event hit a stopped context, so its row
   groups were lost. In a full run this would also have overlapped usage-log writes with the
   next query's timed window. Listeners now act only on action `"head"` (`show()`).
   Commit `7c5799b`.
3. **Instrumented Spark kept one row-group accumulator per query.** `ParquetFileFormat`
   registers one per Parquet *scan*; `RowGroupMetricsRegistry.put` replaced the previous one,
   so any multi-scan query (every join) reported only the last scan's table: the
   `partsupp ⋈ part` check query reported `part` only, identically in local and cluster
   mode. **Fix on Spark branch `rowgroup-dev-multiscan` (`2d7540e`, not merged into
   `rowgroup-dev`, not pushed)**: a list per execution plus `getAll`; the `rowgroup` listener
   merges all scans and logs each (file, offset, size) once per query (`3c38fa8`). This
   affects every row-group capture from the Spark prototype to date, not only this
   experiment; R2D14 sorting/placement in Spark depend on it too.

Step 1 so far: with fixes 1-2, `rg_quick` local vs. cluster is IDENTICAL per query
(`orders`: 12,188 row groups = the whole table; the join: 1,624 = all of `part`, i.e. the
pre-fix single-scan capture). To repeat with the multiscan build, which must then show
`partsupp` too.

**4. Listener actually ran.** After the short validation runs, confirm the `cols` usage
log holds rows for every query that succeeded, and the `rowgroup` log rows for every
query that scanned parquet. A missing query means the listener's work never happened and
its overhead would be understated.

---

## 8. Phase F — The run

Matrix: `vanilla`, `bare`, `cols`, `rowgroup` x 22 queries x 2 reps x {4, 8, 16}
(+ N=1 per §5.4). All sizes rerun on the same S3 data and AMI, so every point shares one
storage layer and one build; none are reused from Chameleon.

- **Sizes in parallel**, one cluster each, identical instance type and executor sizing
  (A5). Changing the instance type across sizes would confound the node-count axis.
- **Timing:** use the in-application timings the listener already writes to
  `spark_internal_listener_*_results.csv` (`System.currentTimeMillis()`), not the
  `/usr/bin/time` wrapper in `run_test_tpch.sh`, which includes JVM startup and executor
  acquisition — a larger and noisier constant on a cluster than in local mode.
- **Harness runs on the driver node inside `tmux`**, started over SSH (tunneled through SSM, no open port 22), per `TMUX.md`, so it
  survives any disconnect, including the Claude session ending.
- **Every result file records** node count, instance type, AMI ID, executor settings and
  seed, and is written to S3 as it lands (`REVISION_EXPERIMENTS.md` §5 ground rules).
- **Carry the existing exclusions forward** if they recur: `query88.sql`
  (`run_test_tpch.sh`) and 64/85/17 (`test_tpch_split_*.sh`); `INSTRUCTIONS.md` warns of
  OOM at 1TB.

---

## 9. EC2 workflow and guardrails

How the runs are driven with Claude, and the rules that keep the cost bounded.

**Who does what:**

- **Claude:** writes the scripts, runs read-only checks, watches long runs, pulls
  results into the worktree, verifies teardown.
- **Tapan approves** every step that creates a billable resource; Claude states the rough
  cost before each one and does not launch anything without a go-ahead.
- **Tapan does** anything needing account credentials or admin rights.

**Prerequisites — the long pole, because the timeline is not ours:**

State as checked 2026-09-26: AWS CLI 2.32 authenticated as IAM user `tapan`, us-east-2
(account ID in `~/.config/vdi-spark/env`, not the repo; see `aws/SECRETS.md`). EC2 reads work. IAM reads, Service Quotas, the Pricing API and
IAM Access Analyzer are all **denied**.

**The admin's whole job is one CloudFormation stack.** Everything is in
`spark-lineage-api/aws/iam/`:

- **`vdi-spark-scale-setup.yaml`** — the template, and the single source of truth for
  every permission. Passes `cfn-lint`; both managed policies are well under IAM's size
  limit. Deploying it creates:
  - role + instance profile `vdi-spark-node`: **object read/write in every S3 bucket**
    (no bucket administration), only the SSM agent's minimum (not
    `AmazonSSMManagedInstanceCore`, which can read every Parameter Store value), **no
    EC2 permissions**;
  - results bucket `vdi-spark-scale-results-<account-id>`, retained if the stack is
    deleted;
  - operator policy on user `tapan`: `iam:PassRole` on that one role only; **all of
    EC2 in us-east-2** (`ec2:*`, no tag required; the account has no other EC2
    workloads) **except long-term purchase commitments**, which are explicitly denied;
    **any instance type**, with the vCPU quota as the cost ceiling (switching to x86
    needs a second AMI); **plain SSH** to any us-east-2 instance, tunneled through SSM
    (`AWS-StartSSHSession`; no open port 22); permission to **request the vCPU quota
    himself**; **unrestricted S3** (`s3:*`);
  - read-only billing and cost visibility for `tapan` via AWS's `AWSBillingReadOnlyAccess`
    (bills, invoices, budgets, Cost Explorer) plus forecasts. He can't change the budget
    or payment settings. Seeing costs may also need the root user's one-time "IAM access
    to Billing" switch and the organization's permission for member-account Cost
    Explorer (README, *Seeing costs*);
  - a monthly budget alert (default $800; emails at 50% and 80%, and at a 100% forecast).
- **`walkthrough.md`** — a click-by-click console guide for an admin new to AWS:
  region, upload, four fields, one checkbox; about 10 minutes. Covers what the stack
  grants and doesn't, how to report a failure, and how to undo it.
- **`README.md`** — the technical rationale, for Tapan or any reviewer.
- **`verify/`** — the offline verification battery (yamllint, cfn-lint, Parliament, and a
  48-case claims audit organised as the actual workflow: network, key, build, SSH, run,
  manage, cost, teardown, plus every fence); rerun after any template edit. The workflow
  audit (2026-09-27) found gaps that the earlier claims-only audits had missed: no outbound
  internet for builds, nodes unable to write outside the results bucket, and the
  hardcoded log path in A4. All are fixed. See the README's Verification section.

**Deployed 2026-09-27 and verified live** (README, *Live verification*): the vCPU quota
is **already 512**, so no request is needed; the budget threshold is $1,500; the
r7g.2xlarge price of $0.4284/hr is confirmed; Cost Explorer works; the purchase Deny
holds. **Caveat:** `tapan` already had EC2 access in other regions, so the template's
us-east-2 condition doesn't fence anything. Still to do: install
`brew install --cask session-manager-plugin` locally, and a first-boot smoke test of the
node role (SSM agent, s3a).

Account facts checked 2026-09-26: EBS default encryption is off and the default key is
AWS-managed, and the data buckets use SSE-S3, so **no KMS permissions are needed**. The
account **is in an AWS Organization**, so a service control policy
could still deny something the stack allows. The walkthrough tells the admin how to
recognise that and who to escalate it to.


**Scripts** (written 2026-10-04, in `spark-lineage-api/aws/`; none of the old `run_*.sh` /
`test_tpch_split_*.sh` harnesses is reused). Every AWS-touching script sources `env.sh` +
`lib.sh`, calls `vdi_check_account`, tags everything `project=vdi-spark-scale`, and asks for
a typed `yes` (with a cost line) before creating anything billable. Run each as
`aws-vault exec vdi -- ./NN_*.sh ...`.

| Script | Does | Billable |
|---|---|---|
| `00_network.sh` | security group (inbound only from itself; refuses to continue if any CIDR rule exists), S3 gateway endpoint on the default VPC's main route table, import key pair from `~/.ssh/vdi-spark.pub`. Idempotent | no |
| `10_build_ami.sh` | `git archive`s the **committed** forks (`rowgroup-dev`, `vod_rg`) and this repo's HEAD to S3 (refuses uncommitted listener changes); boots one Ubuntu 22.04 arm64 builder running `node/build_ami.sh`; on `BUILD_OK` images the stopped builder (AMI tagged with all three SHAs) and terminates it | ~$1 + snapshot storage |
| `node/build_ami.sh` | builder user-data: Thrift 0.16.0 → parquet-hadoop → Spark (`install` for the listener build, then `make-distribution`, `-Pscala-2.13 -Phadoop-cloud`) → 4 listener jars in `/opt/vdi/jars/{vanilla,bare,cols,rowgroup}.jar`. **Fails the build** unless `spark-sql` contains `RowGroupAccumulator`/`RowGroupMetricsRegistry`, the bundled `parquet-hadoop` is byte-identical to the fork's, `hadoop-aws-3.3.4` + SDK bundle are present, and Scala is 2.13 (the §3 "stock SPARK_HOME" trap). Then a **local-mode smoke test** on `nation`/`region` from `s3://vod-tpch-1tb`, writing usage logs to the results bucket: covers the node role, s3a read + write, the jar and row-group capture | (inside the ~$1) |
| `20_launch.sh <name> <N> <max-hours>` | 1 driver (master + client-mode driver, no worker) + N workers, one AZ (`us-east-2a`), 200 GB gp3 at 6000 IOPS / 300 MB/s (shuffle spills here), IMDSv2, shutdown-behaviour terminate + `shutdown -h +max` dead-man; workers self-register from user-data; waits until the master reports N alive; writes `~/.config/vdi-spark/ssh/<name>.conf` (SSH over SSM) | (N+1) × $0.4284/hr |
| `25_extend.sh <name> <hours>` | resets the dead-man on every node to `<hours>` from now (and the `vdi-max-hours` tag), for a run that outlasts the launch estimate | extends billing |
| `30_run.sh <name> <run-id> [args]` | copies `node/run_matrix.sh` + `benchmarking/tpch22/` to the driver and starts it in tmux session `vdi-<run-id>` | no (cluster is) |
| `node/run_matrix.sh` | the harness: one `spark-submit` per (rep, variant); variant order forward on odd reps, reversed on even; resumable (`DONE` markers; a failed variant is logged and skipped, rerun retries it); aborts if alive workers ≠ N; writes `run_metadata.txt` (instance type, AMI, AZ, BUILD_INFO SHAs, every submit flag, query sha256s); per-run event log; `aws s3 sync` to `s3://<results>/runs/<run-id>/` after every variant. `--local` for Phase E step 1 | no |
| `45_status.sh <name> [run-id]` + `node/status_remote.sh` | health report, OK / WARN / ALERT per line, exit 0/1/2: instances, spend so far, dead-man time left, stray project instances, alive vs intended workers, driver heap vs max, driver and worker disk, current query and a **stall** check (3x that query's slowest time in this run, floor 30 min, 3h with no history), OOM / lost-executor / S3-throttling / listener-timeout lines in the current driver log, failed-not-retried runs, usage-log objects in S3 | no |
| `40_fetch.sh <run-id>` | pulls a run into `benchmarking/data/ec2/<run-id>/` (event logs only with `--eventlogs`) | no |
| `99_teardown.sh <name>\|--all` | terminates by tag, waits, then **lists** every live project instance and fails if any of the cluster's remain | stops billing |

**Spark settings in every submit** (`run_matrix.sh`, recorded per run): `--executor-cores 7
--executor-memory 48g --total-executor-cores 7N`, `--driver-memory 16g`,
`spark.speculation=false`, `spark.sql.adaptive.enabled=false`, `spark.sql.exchange.reuse=false`,
`spark.sql.execution.reuseSubquery=false`, `spark.scheduler.minRegisteredResourcesRatio=1.0`
(first query waits for every executor), event log on with stage executor metrics (gives
`executorCpuTime/executorRunTime` for §4.3 and driver peak heap for §1.1). Baked
`spark-defaults.conf`: instance-role credentials, regional endpoint, `fadvise=random`,
`connection.maximum=200`, `threads.max=64`.

**Independent review (2026-10-04), fixes applied before any AWS run:**

- *Master UI binds to the private IP*, not localhost (`WebUI.scala:143`: `SPARK_LOCAL_IP` if
  set). The launch wait, the harness worker check and the status probe all queried localhost
  and would have failed; they now use the private IP. Same for the UI tunnels.
- *`unzip -l | grep -q` under `pipefail`* would have failed a good build via SIGPIPE; the
  instrumentation check now asks `unzip` for the member directly.
- *One Spark build, not two:* `make-distribution` then `install -pl sql/core -am` (no clean).
  Thrift dropped from the build (nothing in `-pl parquet-hadoop` invokes it; jammy's
  `thrift-compiler` 0.16.0 installed as insurance). Builder dead-man 6h; build log pushed to
  S3 every 5 min.
- *Listener compiled with `-Dscala.version=2.13.8`*, the Scala Spark is built with; the pom's
  2.13.16 is not binary-safe on a 2.13.8 runtime. Smoke test now covers all four jars.
- *No stranded instances:* `10_build_ami.sh` terminates the builder on any error or Ctrl-C;
  `20_launch.sh` terminates already-launched nodes if a later step fails (e.g. no capacity
  for the workers); a failed AMI no longer spins forever.
- *Measurement:* the harness re-checks alive workers before **every** submit and stops if
  one is lost; `--workers` comes from the launch-time `vdi-workers` tag, not the current
  count. **DONE requires a complete clean pass** (exit 0, every query a result, none `-1`,
  no listener timeout): the listeners exit 0 even when every query fails. A retry deletes
  the failed attempt's S3 output (event logs and append-mode usage logs) first. Consequence:
  a query that *always* fails (e.g. OOM at 1TB, cf. the old Q88/64/85/17 exclusions) keeps
  its (rep, variant) from completing; decide explicitly whether to drop it from `tpch22/`.
- `spark.sql.shuffle.partitions` stays at the default 200 at every size (about 7 task waves
  at N=4, 2 at N=16). Same for every variant; state it in §6 as part of the scaling setup.

All harness paths (normal, failed query, crash, retry with S3 cleanup, lost worker, local
mode) re-tested locally with stubs. Nothing has run on AWS yet.

Choices made while writing these, to confirm:

- **Driver memory 16g, not 4g.** The driver node is dedicated and has 64 GiB; §1.1 flags
  driver heap at 16 nodes as the residual risk, and the setting is identical across
  variants and sizes, so it costs nothing in comparability.
- **AQE off**, as in the paper's existing Spark runs (`run_test_tpch.sh` passed it). Spark 3.5
  defaults it on; keeping it off keeps plans fixed across variants and sizes.
- **`spark.sql.exchange.reuse=false` is passed on submit** because the listeners set
  `spark.sql.execution.reuseExchange`, which is **not a real Spark key**; only the submit
  flag actually disables exchange reuse.
- **Shuffle on gp3.** r7g has no instance store; heavy queries (Q9, Q18, Q21) spill shuffle
  to EBS. Check spill/shuffle volume in the Phase E event logs; if EBS bandwidth binds,
  r7gd.2xlarge (local NVMe, ~27% dearer) is the alternative, at every size alike.

**Network (revised 2026-09-27).** Nodes run in the default VPC's public subnets with
**no inbound rule except from the cluster's own security group**. They have outbound
internet (builds, SSM), but none of the Spark daemons is reachable from outside. That
closes the real exposure: an unauthenticated Spark master on 7077 is remote code
execution and is actively scanned for. This replaces an earlier private-subnet design
that had no internet route, which would have blocked building on nodes and needed paid
SSM interface endpoints. Public IPv4 costs $0.005/hr per node. Do **not** use
`spark.authenticate` / `spark.network.crypto.enabled` as the mitigation — both add
overhead that would contaminate the deltas, unevenly across node counts.

**Guardrails:**

- **Dead-man's switch.** Every instance gets a maximum lifetime at boot (shutdown
  behaviour = terminate, plus a scheduled shutdown), so nothing outlives a crashed
  session or a forgotten teardown by more than a set number of hours.
- **Budget alarm** from the admin's stack (`aws/iam/`).
- **Sync logs and results to S3 before shutdown.** Termination deletes the root volume,
  so the dead-man's switch would otherwise take local logs and CSVs with it. Sync after
  each batch and set `spark.eventLog.dir` to S3.
- **Tag everything** `project=vdi-spark-scale`. The IAM policy no longer requires it, so
  this is now the scripts' job: teardown finds resources by the tag, and an untagged
  instance would escape it and keep billing until the dead-man's switch fires. The tag
  also lets cost reports separate this experiment's spend.
- **Teardown is verified by listing**, not by the script's exit code.
- Nodes use the instance role, never the `tapan` user's long-lived keys.
- **No secret in user-data, launch templates, tags or AMIs** — any process on the node
  can read user-data from instance metadata. Every script loads account settings via
  `aws/env.sh` and calls `vdi_check_account` before creating anything. Full rules:
  `spark-lineage-api/aws/SECRETS.md`.

---

## 10. Phase G — Analysis

- Append `{4,8,16}_node` rows (and `1_node` if run) to `benchmarking/data/all_results.csv`
  (schema: `query, dataset, runtime, variant, configuration`), with `configuration`
  naming the platform (e.g. `ec2_r7g2x_4_node`). Watch the mixed-width-row defect
  documented in `MANIFEST.md` — a naive `pd.read_csv` silently shifts those rows.
- Generalize `benchmarking/scripts/plot_tpch_single_node.py` into a {4, 8, 16} trend plot.
- **Show the noise band** (rep-to-rep spread) on the plot. Under outcome A it *is* the
  result.
- **Report absolute overhead (ms) and relative overhead (%) together** (§4.3).
- Record `executorCpuTime / executorRunTime` per node count alongside the results.
- Write the per-experiment results note required by `REVISION_EXPERIMENTS.md` §5: the
  numbers, the review item they answer, and the sentence or two they justify.
- Tag the resulting prose `\update{R2D16}{...}` at the moment it is written.

---

## 11. Open decisions

**Decided 2026-09-26** (see §0): EC2 r7g.2xlarge; S3 direct; 22 queries; 4 configs;
2 reps; {4, 8, 16} with N=1 gated on k. Superseded: HDFS on Chameleon (2026-09-13), the
seven-configuration / 3-rep / {1,4,8,16} matrix.

- [x] **Account prerequisites** (§9) — stack deployed and verified 2026-09-27; the
      quota is already 512 vCPUs, so no request is needed.
- [x] **AMI built (2026-10-05): `ami-0a153b2ee8a47ffd5`** (`vdi-spark-rg-20261005-030749`),
      Spark `f0c593d`, parquet-java `5d67eec`, vdi `eb94d29`. All build checks and the
      four-jar S3 smoke test passed; artifacts backed up under
      `s3://<results>/build/20261005-030749/artifacts/`. Node role confirmed live: SSM
      registration, s3a read of the dataset, s3a write of usage logs. **SSH over SSM not yet
      exercised** (first cluster launch). Took four builder runs (~$1.30): the first three
      completed but `finish()` ran `aws s3 cp` from a directory the cleanup had deleted, so
      BUILD_OK never landed and the laptop terminated good builders (fixed in `7b9021c`).
- [ ] **Measure k** (Phase E step 2), then apply the N=1 rule (§5.4).
- [x] **Usage-log write path** — **S3, counted as listener overhead** (decided
      2026-10-04). Node-local is not viable for `cols`/`bare` on a cluster (the write is a
      distributed job, §2 A4), and S3 is what a production deployment pays. §6 must say
      the log write is inside the measured overhead.
- [x] **Query set** — `benchmarking/tpch22/q01.sql`..`q22.sql` (2026-10-04), copied from
      `tpch_queries_spark/1..22.sql`, which match canonical `tpch_queries/` except for
      table references (`lineitem` vs `'lineitem.parquet'`). Zero-padded so lexical sort =
      numeric. All six listeners now sort and `.sql`-filter the query listing. Files 23-38
      of `tpch_queries_spark/` are selective variants (extra predicates), not TPC-H.
- [x] **Harness** — the old `run_*.sh` / `test_tpch_split_*.sh` are **not** reused; new
      scripts are written from scratch under `aws/`.
- [x] **Stock-Spark baseline** — not rerun (2026-09-27). The paper keeps its existing
      stock-Spark numbers; the scale-up measures listener overhead only (§1.4).
- [x] **Data** — TPC-H SF1000 already in `s3://vod-tpch-1tb`, row counts verified (§6).
- [ ] **TPC-DS `item.parquet` is empty** (0 rows) in `s3://vod-tpcds-1tb`. Regenerate it
      before the Spark sorting/placement runs; not needed for this experiment (§6).
- [ ] **Recover or write off 32 `all_results.csv` rows** (`single_node_mod_spark`/`tpch`/
      `bare`) that exist in no committed CSV on any branch — see `MANIFEST.md`.
- [ ] **Scale-factor conflict**: `storage_1_node/README` says 10GB, `stacked_bars.py`
      writes `tpch_node1_30gb.pdf`. Resolve before citing either.
- [ ] **If the old 4-node figure is cited**, confirm it really used 4 nodes against the
      Chameleon reservation record (§1.3).
