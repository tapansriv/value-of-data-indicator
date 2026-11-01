#!/usr/bin/env bash
# Generate TPC-DS raw text with dsdgen 4.0.0, N parallel children run concurrently.
# Usage: gen.sh <SF> <NCHILDREN>
# Output: /mnt/tpcds/tpcds_raw/sf<SF>/<table>_<child>_<N>.dat
#
# Quirks of this dsdgen build (verified):
#  - must run with cwd = tools dir (finds tpcds.idx relative to cwd; -distributions <abs> segfaults)
#  - never use -_filter (writes into cwd on this build)
#  - tables with < 1,000,000 "rows" (sales tables count orders/tickets) are only emitted by child 1
#  - concatenating child files 1..N reproduces the serial (-parallel-less) output byte for byte (checked at SF1)
set -euo pipefail

SF=${1:?scale factor}
N=${2:?number of children}
SEED=19620718
TOOLS=/home/cc/DSGen-software-code-4.0.0/tools
OUT=/mnt/tpcds/tpcds_raw/sf${SF}
LOG=${OUT}/_gen_logs
mkdir -p "$OUT" "$LOG"

cd "$TOOLS"
if ls "$TOOLS"/*.dat >/dev/null 2>&1; then echo "ERROR: stray .dat files in $TOOLS before start"; exit 1; fi

echo "dsdgen: $TOOLS/dsdgen ($(./dsdgen -release 2>&1 | head -1))" | tee "$LOG/gen_meta.txt"
echo "cmd template: cd $TOOLS && ./dsdgen -scale $SF -rngseed $SEED -parallel $N -child <i> -dir $OUT -force Y -quiet Y" | tee -a "$LOG/gen_meta.txt"
start=$(date +%s)
echo "start: $(date -Is)" | tee -a "$LOG/gen_meta.txt"

# run each child; record exit code per child
seq 1 "$N" | xargs -P "$N" -I{} bash -c \
  "./dsdgen -scale $SF -rngseed $SEED -parallel $N -child {} -dir $OUT -force Y -quiet Y > $LOG/child_{}.log 2>&1; echo \$? > $LOG/child_{}.rc" || true

end=$(date +%s)
echo "end: $(date -Is)" | tee -a "$LOG/gen_meta.txt"
echo "gen_wallclock_s: $((end-start))" | tee -a "$LOG/gen_meta.txt"

fail=0
for i in $(seq 1 "$N"); do
  rc=$(cat "$LOG/child_${i}.rc" 2>/dev/null || echo missing)
  if [ "$rc" != "0" ]; then echo "ERROR: child $i rc=$rc"; cat "$LOG/child_${i}.log"; fail=1; fi
done
if ls "$TOOLS"/*.dat >/dev/null 2>&1; then echo "ERROR: stray .dat files appeared in $TOOLS"; ls "$TOOLS"/*.dat; fail=1; fi
[ $fail -eq 0 ] && echo "all $N children rc=0" | tee -a "$LOG/gen_meta.txt"
exit $fail
