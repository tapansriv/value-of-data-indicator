# Phase E — validation and calibration on a 4-node cluster

`REVISION_SCALEUP.md` §7. Every command runs from `spark-lineage-api/aws/` as
`aws-vault exec vdi -- ./...`. Cluster name `val`; budget ~$10–20 (5 × r7g.2xlarge ≈
$2.14/hr, 2–4 h). Results land in `s3://<results>/runs/<run-id>/`.

| Dir | Queries | Used for |
|---|---|---|
| `rg_quick/` | two cheap ad-hoc queries on `orders` and `partsupp ⋈ part` | step 1 first pass: catches a broken accumulator in minutes |
| `rg_check/` | TPC-H Q6, Q14 | step 1 as specified (local run is slow: 8 cores, all of `lineitem`) |
| `kcal/` | Q16 (short), Q14 (medium), Q9 (heavy) | step 4: k vs. the old Chameleon 4-node times (~110 s, ~580 s, ~1450 s) |

## Steps

```bash
# 0. Launch (6h dead-man) and check health
./20_launch.sh val 4 6
./45_status.sh val

# 1. Row-group capture: same queries, local mode vs. cluster, rowgroup variant only
Q=../benchmarking/phaseE
./30_run.sh val e-rgq-local   --queries-local $Q/rg_quick --local --variants rowgroup --reps 1
#    (wait for MATRIX COMPLETE: ./45_status.sh val e-rgq-local)
./30_run.sh val e-rgq-cluster --queries-local $Q/rg_quick         --variants rowgroup --reps 1
scp -F ~/.config/vdi-spark/ssh/val.conf $Q/compare_rowgroups.py driver:vdi/
ssh -F ~/.config/vdi-spark/ssh/val.conf driver \
    "/opt/spark/bin/spark-submit --master 'local[4]' vdi/compare_rowgroups.py <bucket> e-rgq-local e-rgq-cluster"
#    IDENTICAL -> repeat with rg_check (run ids e-rgc-local / e-rgc-cluster).
#    DIFFERENT -> stop. Every later number would be invalid.

# 2. The listener ran: cols writes a usage-log entry per query
./30_run.sh val e-cols --queries-local $Q/rg_quick --variants cols --reps 1

# 3. k calibration
./30_run.sh val e-kcal --queries-local $Q/kcal --variants vanilla --reps 1

# 4. Pull results + event logs; per-query CPU ratio, spill, shuffle, driver heap
./40_fetch.sh e-kcal --eventlogs
python3 $Q/summarize_eventlog.py ../benchmarking/data/ec2/e-kcal/rep1/vanilla/eventlog

# 5. Tear down, verify by listing
./99_teardown.sh val
```

## Pass criteria

1. `compare_rowgroups.py` prints IDENTICAL for `rg_quick` and `rg_check`: same
   (table, offset, size) set per query, no row group recorded twice.
2. `cols` and `rowgroup` usage logs have an entry for every query that succeeded.
3. k = (new per-query time) / (old Chameleon time); feed `budget_model.py --k <k>`.
4. Event logs: executors = 4, none removed, no speculative tasks; record cpu/run per query
   (the §4.3 baseline) and disk spill (whether gp3 binds); no `503 SlowDown` in driver logs.
5. Slowest listener time observed → replaces `LISTENER_TIMEOUT_MIN = 30` (A11).
