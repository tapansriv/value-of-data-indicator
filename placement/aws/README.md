# EC2 runbook: data-placement experiment on Spark

**Status: none of this has been run yet** (written 2026-10-05). Each script has been checked
only with `bash -n`. Expect the first build and the first calibration to surface bugs.

Single-node runs: each instance is a standalone m7g.2xlarge (8 vCPU Graviton, 32 GiB) running
the forked Spark 3.5.5 (Scala 2.13, Java 17) in local mode, caching TPC-DS SF30 columns
from `s3://vod-tpcds-10gb` onto its gp3 root volume. There is no cluster.

## Prerequisites

- The spark-scale setup already exists and is shared: `~/.config/vdi-spark/env`
  (account ID, VPC, results bucket, key pair; see
  `value_of_data/spark-scale/spark-lineage-api/aws/SECRETS.md`), the IAM stack
  (instance profile `vdi-spark-node`, operator policy), the S3 gateway endpoint and the
  key pair. Nothing account-specific is in this directory; use `<account-id>` etc. in docs.
- `aws-vault` profile `vdi`; the AWS CLI with the Session Manager plugin; `jq`, `python3`.
- `run/run_spark_matrix.sh` exists and is executable (harness side, below).
- `~/value_of_data/value-of-data-metric/spark-lineage-api` (main) contains
  `vdi.placement.PlacementUsageListener` (override the path with `VDI_LISTENER_DIR`).

## Isolation from spark-scale

Same account and region, separated by tags (details in `lib.sh`, "Isolation"):

| | spark-scale selects | placement selects |
|---|---|---|
| instances | `project=vdi-spark-scale` [+ `vdi-cluster=<c>`] | `project=vdi-placement` + `vdi-exp=placement` + `vdi-place-run=<run>` |
| AMIs | `project=vdi-spark-scale` + `vdi-image=spark-rg` | `project=vdi-placement` + `vdi-exp=placement` + `vdi-image=placement` |
| Names | `vdi-<cluster>-driver/worker`, `vdi-builder-*` | `vdi-place-<run>-<i>`, `vdi-place-builder-*` |
| security group | `vdi-spark-cluster` | `vdi-place-node` (no inbound rules) |
| S3 prefix | `runs/`, `build/` | `placement/`, `placement-build/` |

`env.sh` hard-codes the placement tag and unsets the env file's `VDI_TAG_KEY/VALUE`.
Teardown, extend and run additionally call `vdi_place_guard`, which refuses if any
selected instance lacks a placement tag, the `vdi-place-` name, or carries `vdi-cluster`.

**Coordination:** the spark-scale session shares the account's 512-vCPU Standard quota in
us-east-2. The sweep needs 5 x 8 = 40 vCPU, calibration 8. Check with that session (or
its `45_status.sh`) that its clusters leave the headroom before launching.

## Prices used (on-demand, us-east-2; verify before relying on them)

| Item | $/hr |
|---|---|
| m7g.2xlarge | 0.3264 (verify) |
| gp3 100 GB + 6000 IOPS + 300 MB/s | ~0.041 |
| **per node** | **~0.363** |

## Before the first AMI build: land the Spark fix

`10_build_ami.sh` builds Spark `rowgroup-dev` and parquet-java `vod_rg` (the merged forks:
multiscan and the capture fix are both in, as in spark-scale's build #8). The placement
harness additionally needs `RowGroupMetricsRegistry.keys` to be thread-safe: without it
TPC-DS q6 fails intermittently (`ArrayIndexOutOfBoundsException: Index 34 out of bounds
for length 33`) because its subqueries plan scans concurrently. That fix is in
`rowgroup-dev` as of 2026-10-06 (`e9174562ee3`, local, not pushed); `10_build_ami.sh`
refuses to build a Spark ref without it. `VDI_SPARK_FROM_BUILD` (reusing spark-scale's dist) skips that check and
brings the race back; don't use it for placement unless that dist carries the fix.

## One-time: network and AMI

```bash
cd ~/s3-column-cache/aws
aws-vault exec vdi -- ./00_network.sh       # creates SG vdi-place-node; free
aws-vault exec vdi -- ./10_build_ami.sh     # BILLABLE; prints the AMI id at the end
```

`10_build_ami.sh` builds Spark from the fork (same steps as spark-scale; ~1.5-2.5 h,
~$0.50-0.85) unless `VDI_SPARK_FROM_BUILD=<spark-scale build id>` reuses the dist that
spark-scale's builder backed up to `s3://<results-bucket>/build/<id>/artifacts/` (~20 min,
~$0.10). AMI storage ~10 GB, ~$0.50/month. Rebuild the AMI only when Spark, the listener or
Python packages change: `30_run.sh` ships the current harness working tree on every start.

## (a) Calibration: 1 instance, 1 config, ~1 h

```bash
aws-vault exec vdi -- ./20_launch.sh cal1 1 2          # 1 node, dead-man 2 h: ~$0.36/hr, cap $0.73
aws-vault exec vdi -- ./30_run.sh cal1 --calibrate 0 <size>
aws-vault exec vdi -- ./45_status.sh cal1              # repeat; DONE marker when finished
aws-vault exec vdi -- ./40_fetch.sh cal1               # -> data/spark/cal1/0/
aws-vault exec vdi -- ./99_teardown.sh cal1
```

Expected cost ~$0.36 for one hour. Use its wall time per config to choose the sweep's
max-hours: (5 sizes x per-config time) plus margin.

## (b) Sweep: 5 instances, one value_iter each, all 5 sizes

```bash
aws-vault exec vdi -- ./20_launch.sh sweep1 5 <max-hours>
aws-vault exec vdi -- ./30_run.sh sweep1 <s1> <s2> <s3> <s4> <s5>   # node i -> value_iter i
aws-vault exec vdi -- ./45_status.sh sweep1
aws-vault exec vdi -- ./25_extend.sh sweep1 <hours>    # only if it will outlast the dead-man
aws-vault exec vdi -- ./40_fetch.sh sweep1             # -> data/spark/sweep1/<0..4>/
aws-vault exec vdi -- ./99_teardown.sh sweep1
```

Cost: 5 x ~$0.363 = **~$1.82/hr**; e.g. 12 h ~$22, 24 h cap ~$44.
Restart one failed node: `./30_run.sh sweep1 --only 3 <sizes...>` (add `--force` if it
already has DONE). Different iteration mapping: `--iters "5 6 7 8 9"`.

## What runs on a node

`30_run.sh` (via SSM `send-command`) starts `node/run_node.sh` as systemd unit
`vdi-place-run` (user `ubuntu`), which extracts the shipped harness over
`/opt/vdi-place/s3-column-cache`, then runs
`cd run && ./run_spark_matrix.sh <value_iter> <sizes...>` (or `--calibrate <iter> <size>`).
It syncs `run/results/spark/` to `s3://<results-bucket>/placement/<run>/<i>/results/spark/`
every 10 min (`VDI_PLACE_SYNC_MIN`), whenever the harness runs `"$VDI_PLACE_SYNC"`, and
at the end, then writes `<i>/DONE` or `<i>/FAILED`. Log: `/home/ubuntu/vdi-place/run_node.log`
(also in S3). Shell: `aws ssm start-session --target <instance-id>`.

Node layout: `/opt/spark`, `/opt/jars/iceberg-spark-runtime.jar`, `/opt/jars/vdi-listener.jar`,
`/opt/vdi-place/s3-column-cache`, `/opt/vdi-place/venv` (Python 3.11), env in
`/etc/profile.d/vdi-place.sh` (`SPARK_HOME JAVA_HOME VDI_ICEBERG_JAR VDI_LISTENER_JAR
PYSPARK_PYTHON PYTHONPATH VDI_PLACE_DATA_BUCKET AWS_REGION`).

## Leak guard (not installed)

`git-hooks/pre-commit` is spark-scale's secret scanner. Install it once per clone with
`aws/git-hooks/install.sh` (copies it into the shared hooks dir, so it covers this
worktree and `~/s3-column-cache`).
