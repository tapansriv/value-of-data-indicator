#!/bin/bash
# usage: watch_all.sh <cluster>:<run-id> ...  -- every 5 min, emit new 'end rep' / FAILED / ABORT /
# MATRIX lines from each run's matrix.log. State (lines seen) persists across re-arms.
cd "$(dirname "$0")/.."
ST=$HOME/.config/vdi-spark/state/runwatch; mkdir -p $ST
while true; do
  for cr in "$@"; do
    c=${cr%%:*}; r=${cr#*:}
    log=$(aws-vault exec vdi --duration=12h -- ssh -F ~/.config/vdi-spark/ssh/$c.conf -o ConnectTimeout=25 driver "cat ~/vdi/runs/$r/matrix.log 2>/dev/null" 2>/dev/null) || continue
    n=$(echo "$log" | grep -c .); seen=$(cat "$ST/$r" 2>/dev/null || echo 0)
    if [ "$n" -gt "$seen" ]; then
      echo "$log" | tail -n +$((seen + 1)) | grep -E "end rep|FAILED|ABORT|MATRIX" | sed "s/^/[$c] /" | cut -c1-200
      echo "$n" > "$ST/$r"
    fi
  done
  sleep 300
done
