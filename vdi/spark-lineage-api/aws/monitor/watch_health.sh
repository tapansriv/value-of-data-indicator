#!/bin/bash
# usage: watch_health.sh <cluster>:<run-id> [...]   -- every 20 min run 45_status.sh per cluster;
# print WARN/ALERT lines when they change, plus a progress line every ~2h. Never exits on its own.
cd "$(dirname "$0")/.."
ST=$HOME/.config/vdi-spark/state/health; mkdir -p $ST   # persists across re-arms
while true; do
  for cr in "$@"; do
    c=${cr%%:*}; r=${cr#*:}
    out=$(aws-vault exec vdi --duration=12h -- ./45_status.sh "$c" "$r" 2>&1 | sed -E 's/[0-9]{12}/<acct>/g')
    bad=$(echo "$out" | grep -E '^(ALERT|WARN)' | grep -v 'other live project instance')
    prev=$(cat "$ST/$c" 2>/dev/null)
    if [ -n "$bad" ] && [ "$bad" != "$prev" ]; then echo "[$c $(date -u +%H:%MZ)] $(echo "$bad" | tr '\n' ' ' | cut -c1-400)"; fi
    echo "$bad" > "$ST/$c"
    lastp=$(cat "$ST/$c.progress" 2>/dev/null || echo 0)
    if [ $(( $(date +%s) - lastp )) -ge 7000 ]; then
      date +%s > "$ST/$c.progress"
      prog=$(echo "$out" | grep -E 'query [0-9]+ \(|runs done|so far|MATRIX' | tr '\n' ' ' | cut -c1-400)
      echo "[$c $(date -u +%H:%MZ)] progress: $prog"
    fi
  done
  sleep 1200
done
