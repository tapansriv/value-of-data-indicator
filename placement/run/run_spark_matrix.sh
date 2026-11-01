#!/usr/bin/env bash
# Spark version of run.sh: for one value assignment, run LRU, VoD static and VoD dynamic,
# all with a pre-filled cache, at each cache size. One SparkSession (process) per run.
#
#   ./run_spark_matrix.sh <value_iter> [sizes...]        default sizes: 2.75 3.5 5.0 7.5 13.75
#   ./run_spark_matrix.sh --calibrate <value_iter> <size>  VoD dynamic only, one size
#
# Results: results/spark/<value_iter>_<size>/{lru_hot_static,vod_hot_static,vod_hot_dynamic}
#          _spark_<size>.{json,breakdown.json,out}
# Env: SPARK_RUN_LOCAL=1 runs against $SPARK_DATA_DIR in local mode (testing);
#      SPARK_EXTRA_ARGS is appended to every run_spark.py call (e.g. "--queries 1,2,3").
set -uo pipefail
cd "$(dirname "$0")"
. ./spark_env.sh

CALIBRATE=0
if [ "${1:-}" = "--calibrate" ]; then CALIBRATE=1; shift; fi
[ $# -ge 1 ] || { echo "usage: $0 [--calibrate] <value_iter> [sizes...]" >&2; exit 2; }
ITER=$1; shift
if [ $# -gt 0 ]; then SIZES=("$@"); else SIZES=(2.75 3.5 5.0 7.5 13.75); fi
if [ $CALIBRATE = 1 ] && [ ${#SIZES[@]} -ne 1 ]; then echo "--calibrate takes one size" >&2; exit 2; fi

QV="../metadata/tpcds_query_values_custom.csv"
CACHE="${SPARK_CACHE_DIR:-../metadata/cache_spark}"
if [ "${SPARK_RUN_LOCAL:-0}" = 1 ]; then
    SRC=(--local-mode --data-dir "${SPARK_DATA_DIR:?set SPARK_DATA_DIR}")
    SIZE_FILE="${SPARK_SIZE_FILE:-../metadata/sizes_30gb/column_sizes.json}"
else
    SRC=(--s3-region us-east-2)
    SIZE_FILE="../metadata/sizes_30gb/column_sizes.json"
fi
read -r -a EXTRA <<< "${SPARK_EXTRA_ARGS:-}"

failures=0
run_one() {  # <name> <size> <run_spark.py args...>
    local name=$1 size=$2; shift 2
    local dir="results/spark/${ITER}_${size}"
    mkdir -p "$dir"
    if [ -f "$dir/${name}_spark_${size}.json" ]; then
        echo "[$(date '+%F %T')] skip $dir/$name (already done)"; return
    fi
    echo "[$(date '+%F %T')] start iter=$ITER size=$size $name"
    rm -rf "$CACHE"
    if python3 run_spark.py "${SRC[@]}" --max-cache-size "$size" --cache-dir "$CACHE" \
            --query-value-file "$QV" --size-file "$SIZE_FILE" \
            --value-iter "$ITER" --fill-cache "$@" "${EXTRA[@]}" \
            --outfile "$dir/${name}_spark_${size}.json" > "$dir/${name}_spark_${size}.out" 2>&1; then
        echo "[$(date '+%F %T')] done  iter=$ITER size=$size $name"
    else
        failures=$((failures + 1))
        rm -f "$dir/${name}_spark_${size}.json"
        echo "[$(date '+%F %T')] FAIL  iter=$ITER size=$size $name (see $dir/${name}_spark_${size}.out)"
    fi
    rm -rf "$CACHE"
    # On a node, push results to S3 after every config (aws/node/run_node.sh sets this).
    if [ -n "${VDI_PLACE_SYNC:-}" ]; then "$VDI_PLACE_SYNC" || true; fi
}

for size in "${SIZES[@]}"; do
    if [ $CALIBRATE = 1 ]; then
        run_one vod_hot_dynamic "$size" --policy vod --dynamic
        continue
    fi
    run_one lru_hot_static  "$size" --policy lru
    run_one vod_hot_static  "$size" --policy vod
    run_one vod_hot_dynamic "$size" --policy vod --dynamic
done
echo "[$(date '+%F %T')] finished iter=$ITER failures=$failures"
exit $((failures > 0))
