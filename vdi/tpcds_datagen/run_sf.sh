#!/usr/bin/env bash
# Full pipeline for one or more scale factors, sequentially; stops at the first failure.
# Usage: run_sf.sh <NCHILDREN> <SF> [<SF> ...]     (run inside tmux session "datagen")
# Env (optional): PARQUET_ROOT (default /mnt/tpcds/parquet), RG_ROWS (see convert.py), SKIP_GEN=1.
set -euo pipefail
N=${1:?children}; shift
HERE=$(cd "$(dirname "$0")" && pwd)
PY=~/vdi-venv/bin/python
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
PQ=${PARQUET_ROOT:-/mnt/tpcds/parquet}

for SF in "$@"; do
  mkdir -p /mnt/tpcds/tpcds_raw/sf$SF $PQ/sf$SF
  LOG=$PQ/sf$SF/_pipeline.log
  set +e
  (
    set -e
    echo "=== SF$SF pipeline start $(date -Is)"; free -g | head -2; df -h /mnt/tpcds | tail -1
    if [ "${SKIP_GEN:-0}" = "1" ]; then
      echo "=== SKIP_GEN=1: reusing existing raw data + _raw_check.json (resume after a failed convert)"
      test -f /mnt/tpcds/tpcds_raw/sf$SF/_raw_check.json
      rm -rf $PQ/sf$SF/_tmp_*
    else
      "$HERE/gen.sh" "$SF" "$N"
      echo "=== raw check $(date -Is)"
      t0=$(date +%s); $PY "$HERE/verify.py" raw "$SF"; echo "raw_check_s: $(( $(date +%s)-t0 ))"
    fi
    echo "=== convert $(date -Is)"; free -g | head -2
    t0=$(date +%s); $PY "$HERE/convert.py" "$SF" --workers 8 > $PQ/sf$SF/_convert.log 2>&1 \
      || { echo "CONVERT FAILED, see _convert.log"; tail -50 $PQ/sf$SF/_convert.log; exit 1; }
    grep -E '^\{"table"|convert wallclock' $PQ/sf$SF/_convert.log
    echo "convert_s: $(( $(date +%s)-t0 ))"
    echo "=== verify $(date -Is)"
    t0=$(date +%s); $PY "$HERE/verify.py" parquet "$SF" --workers 8; echo "verify_s: $(( $(date +%s)-t0 ))"
    $PY "$HERE/make_notes.py" "$SF" --extra "Generated with -parallel $N (children run concurrently via xargs -P $N). Pipeline log: _pipeline.log; Spark log: _convert.log." > /dev/null
    echo "=== SF$SF DONE $(date -Is)"; df -h /mnt/tpcds | tail -1
  ) 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  set -e
  [ "$rc" -eq 0 ] || { echo "SF$SF FAILED rc=$rc $(date -Is)" | tee -a "$LOG"; exit 1; }
done
echo "ALL DONE $(date -Is)"
