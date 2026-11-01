#!/bin/bash
# Capture SF30, SF60, SF100 back to back, converting each as it finishes. Run inside tmux.
# A failed SF does not stop the others; rerunning resumes each SF where it left off.
# Usage: run_capture_all.sh [SF ...]   (default: 30 60 100)
# Env (optional, passed through to run_spark_sf.sh): PARQUET_ROOT, RESULTS, QUERY_DIR, QUERIES.
cd "$(dirname "$0")"
RESULTS="${RESULTS:-/mnt/tpcds/results}"
QUERIES="${QUERIES:-1-99}"
SFS=("$@"); [ ${#SFS[@]} -gt 0 ] || SFS=(30 60 100)
for SF in "${SFS[@]}"; do
    echo "=== SF$SF capture start $(date -u +%FT%TZ)"
    ./run_spark_sf.sh capture "$SF" "$QUERIES" > "$RESULTS/sf${SF}_capture_console.log" 2>&1
    echo "=== SF$SF capture exit=$? $(date -u +%FT%TZ)"
    ./run_spark_sf.sh convert "$SF" 2>&1 | tail -3
done
echo "=== all done $(date -u +%FT%TZ)"
