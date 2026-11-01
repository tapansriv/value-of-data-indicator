#!/bin/bash
# R2D7: row-group capture through the instrumented Spark and the Sec 4.4 pipeline for TPC-DS.
# Everything for SF<N> lands in $RESULTS/sf<N>.
#
# Env (optional; defaults reproduce the first R2D7 run): PARQUET_ROOT (/mnt/tpcds/parquet),
# RESULTS (/mnt/tpcds/results), QUERY_DIR (tpcds_queries_spark), QUERIES (1-99: capture's
# default range and convert's --queries).
#
#   ./run_spark_sf.sh capture <SF> [first-last]  # long: run inside tmux (TMUX.md). Resumable:
#                                                # queries with rg/<N>.done are skipped.
#   ./run_spark_sf.sh convert <SF>               # cardinality, query columns, access.json
#   ./run_spark_sf.sh common <SF> <SF> ...       # queries completed at every listed SF
#   ./run_spark_sf.sh vdi <SF> <query_set.json>  # values -> VDI -> figures on that query set
#
# The SFs are compared on one common query set (Tapan, 2026-09-26) so every SF draws the
# same 1500-query history. AQE stays at Spark's default (on), also per Tapan.
set -euo pipefail

STEP="$1"; shift
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
SPARK_HOME="${SPARK_HOME:-/home/cc/value_of_data/spark}"
CAPTURE_JAR="${CAPTURE_JAR:-$HOME/spark-rowgroup-capture.jar}"
PY="${PY:-$HOME/vdi-venv/bin/python}"
QUERY_DIR="${QUERY_DIR:-$REPO/spark-lineage-api/benchmarking/tpcds_queries_spark}"
RESULTS="${RESULTS:-/mnt/tpcds/results}"
PARQUET_ROOT="${PARQUET_ROOT:-/mnt/tpcds/parquet}"
QUERIES="${QUERIES:-1-99}"
DRIVER_MEM="${DRIVER_MEM:-48g}"

case "$STEP" in
capture)
    SF="$1"; RANGE="${2:-$QUERIES}"; OUT="$RESULTS/sf$SF"
    mkdir -p "$OUT/capture" "$OUT/eventlog" "/mnt/tpcds/spark-tmp/sf$SF"
    "$SPARK_HOME/bin/spark-submit" \
        --class RowGroupCapture \
        --master 'local[*]' \
        --driver-memory "$DRIVER_MEM" \
        --conf spark.speculation=false \
        --conf spark.local.dir="/mnt/tpcds/spark-tmp/sf$SF" \
        --conf spark.eventLog.enabled=true \
        --conf spark.eventLog.dir="file://$OUT/eventlog" \
        "$CAPTURE_JAR" "$PARQUET_ROOT/sf$SF" "$QUERY_DIR" "$OUT/capture" "$RANGE" \
        2>&1 | tee -a "$OUT/capture/driver.log"
    ;;
convert)
    SF="$1"; OUT="$RESULTS/sf$SF"; cd "$HERE"
    "$PY" gen_cardinality.py --parquet-dir "$PARQUET_ROOT/sf$SF" \
        --out "$OUT/tpcds_cardinality.json"
    "$PY" tpcds_parse_columns_from_query.py --query-dir "$QUERY_DIR" \
        --pattern 'query{}.sql' --queries "$QUERIES" --out-dir "$OUT"
    "$PY" spark_rg_to_access.py --capture-dir "$OUT/capture" --out-dir "$OUT/logs" \
        --query-dir "$QUERY_DIR" --columns-in-queries "$OUT/tpcds_columns_in_queries.json"
    ;;
common)
    NAME="$RESULTS/common_completed_sf$(IFS=_; echo "$*").json"
    "$PY" - "$RESULTS" "$NAME" "$@" <<'EOF'
import json, sys
results, out, sfs = sys.argv[1], sys.argv[2], sys.argv[3:]
sets = {sf: set(json.load(open(f"{results}/sf{sf}/logs/tpcds_completed.json")))
        for sf in sfs}
common = sorted(set.intersection(*sets.values()))
for sf, s in sets.items():
    print(f"SF{sf}: {len(s)} completed, excluded from common set: {sorted(s - set(common))}")
json.dump(common, open(out, "w"))
print(f"{len(common)} queries in common -> {out}")
EOF
    ;;
vdi)
    SF="$1"; QSET="$2"; OUT="$RESULTS/sf$SF"; cd "$HERE"
    for distro in normal zipf; do
        "$PY" generate_oracle_vals.py "$distro" --tpcds-only --query-set "$QSET" \
            --logs-dir "$OUT/logs" --out-dir "$OUT/values"
    done
    "$PY" assign_val_to_de.py --tpcds-only --logs-dir "$OUT/logs" --query-set "$QSET" \
        --values-dir "$OUT/values" \
        --columns-in-queries "$OUT/tpcds_columns_in_queries.json" \
        --cardinality "$OUT/tpcds_cardinality.json" -o "$OUT/vdi"
    "$PY" graph_comp_oracles.py --tpcds-only --data-dir "$OUT/vdi" --fig-dir "$OUT/figs"
    ;;
*)
    echo "usage: $0 capture|convert|common|vdi ..."; exit 1 ;;
esac
