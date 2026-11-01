#!/bin/bash
# usage: watch_run.sh <cluster> <run-id>   -- emits new matrix.log lines and driver-log errors; exits when the run ends
C=$1 R=$2; seen=${3:-0}; lasterr=""   # 3rd arg: matrix.log lines to skip (earlier attempts)
cd "$(dirname "$0")/.."
while true; do
  out=$(aws-vault exec vdi --duration=12h -- ssh -F ~/.config/vdi-spark/ssh/$C.conf -o ConnectTimeout=25 driver "cat ~/vdi/runs/$R/matrix.log 2>/dev/null; echo ===; for f in ~/vdi/runs/$R/rep*/*/driver.log; do grep -h -E 'Exception|ERROR|Query failed|WARNING: listener|OutOfMemory' \$f 2>/dev/null | grep -v -E 'StatusLogger|NativeCodeLoader|ERROR Inbox|FileAlreadyExists' | tail -3; done" 2>/dev/null) || { echo "ssh failed"; sleep 60; continue; }
  log=$(echo "$out" | sed '/^===$/,$d'); errs=$(echo "$out" | sed '1,/^===$/d')
  n=$(echo "$log" | grep -c .)
  new=""
  if [ "$n" -gt "$seen" ]; then new=$(echo "$log" | tail -n +$((seen + 1))); echo "$new" | sed -E 's/[0-9]{12}/<acct>/g' | cut -c1-220; seen=$n; fi
  if [ -n "$errs" ] && [ "$errs" != "$lasterr" ]; then echo "DRIVER-LOG: $(echo "$errs" | cut -c1-250)"; lasterr=$errs; fi
  echo "$new" | grep -q -E 'MATRIX COMPLETE|MATRIX FINISHED|ABORT' && exit 0
  sleep 45
done
