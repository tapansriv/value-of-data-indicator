#!/bin/bash
# usage: finish_run.sh <cluster> <run-id>  -- fetch results + usage logs, summarize event logs on
# the driver, validate, then tear the cluster down (only if MATRIX_DONE was fetched).
set -u
c=$1 r=$2
cd "$(dirname "$0")/.."
D=../benchmarking/data/ec2/$r
aws-vault exec vdi --duration=12h -- bash -c ". ./env.sh
./40_fetch.sh $r >/dev/null 2>&1
aws s3 sync s3://\$VDI_RESULTS_BUCKET/runs/$r/usage_logs $D/usage_logs --quiet
scp -F ~/.config/vdi-spark/ssh/$c.conf -q ../benchmarking/phaseE/summarize_eventlog.py driver:vdi/
ssh -F ~/.config/vdi-spark/ssh/$c.conf driver 'cd ~/vdi/runs/$r; for d in rep*/*/eventlog; do echo \"### \$d\"; python3 ~/vdi/summarize_eventlog.py \$d; done' > $D/eventlog_summary.txt 2>&1"
if [ ! -f "$D/MATRIX_DONE" ]; then echo "$r: no MATRIX_DONE fetched; NOT tearing down $c"; exit 1; fi
echo "== validate $r"; (cd ../benchmarking && python3 scripts/validate_run.py data/ec2/$r tpch22 2>&1 | grep -E "usage log|identical|PASS|FAILED|FAIL ")
echo "== event logs $r"; grep "^==" $D/eventlog_summary.txt | awk '{print $3,$4,$5,$6,$7,$8,$9}' | sort | uniq -c
VDI_YES=1 aws-vault exec vdi --duration=12h -- ./99_teardown.sh $c 2>&1 | tail -1 | sed -E 's/[0-9]{12}/<acct>/g'
