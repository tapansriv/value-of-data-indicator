#!/bin/bash
# Sorting experiment on Spark + Iceberg — the one entry point. See NODE_RUNBOOK.md.
#
#   ./run_phase.sh setup                  dirs, Iceberg jar, build runner jar, version checks
#   ./run_phase.sh check-source           row counts of SOURCE_DIR vs the SF30 counts used for ranking
#   ./run_phase.sh build-base [--rebuild T1,T2]  24 unsorted Iceberg tables, 32 x 128k-row files
#   ./run_phase.sh explain                EXPLAIN all 99 queries on base; must be 99/99 ok
#   ./run_phase.sh build-pilot            pilot table under modes s, ps, pz
#   ./run_phase.sh pilot                  base + base_rep + pilot arms   -> results/pilot.jsonl
#   ./run_phase.sh build-configs [MODE [K [C]]]  layouts the selected configurations need
#   ./run_phase.sh configs [MODE [K [C]]] nosort + one run per sorted-table set + repeats
#                                                                        -> results/configs_MODE.jsonl
#   ./run_phase.sh analyze [MODE [METRICS]]  pilot report, configuration utilities, paper CSVs
#   ./run_phase.sh plot [MODE [K [C]]]    workload_value.pdf from the paper CSVs
#
# MODE defaults to ps; K and C default to 2 (comma-separated lists or "all").
# Long steps (build-*, pilot, layouts, validate) belong inside tmux (TMUX.md). All of
# them are resumable: rerunning skips finished tables and finished (run, query) pairs.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/env.sh"
RUNNER_JAR="$HERE/runner/target/sorting-runner-1.0.0.jar"
# Per-workload inputs (WORKLOAD=tpcds by default -> manifest.json, SF30 row counts).
wl() { (cd "$HERE/../src" && python3 workload.py "$1"); }
MANIFEST="$(wl manifest)"
ROW_COUNTS="$(wl row_counts_json)"
echo "WORKLOAD=$WORKLOAD  manifest=$MANIFEST  warehouse=$WAREHOUSE" >&2
STEP="${1:-}"; shift || true

mkdir -p "$WAREHOUSE" "$RESULTS/eventlog" "$PLANS" "$SPARK_TMP" "$(dirname "$ICEBERG_JAR")"

SPARK_CONF=(
    --master 'local[*]'
    --driver-memory "$DRIVER_MEM"
    --jars "$ICEBERG_JAR"
    --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
    --conf spark.sql.catalog.vdi=org.apache.iceberg.spark.SparkCatalog
    --conf spark.sql.catalog.vdi.type=hadoop
    --conf "spark.sql.catalog.vdi.warehouse=file://$WAREHOUSE"
    --conf "spark.local.dir=$SPARK_TMP"
    --conf spark.speculation=false
    --conf spark.driver.maxResultSize=8g
    # Let DPP fire even when the dimension side is not a broadcast (default: broadcast only).
    --conf spark.sql.optimizer.dynamicPartitionPruning.reuseBroadcastOnly=false
    # When a join side turns out empty, AQE replaces the plan with an empty relation and
    # cancels running stages, so bytes read depend on timing (smoke test: one query varied
    # 69% between identical runs). Excluding that one rule keeps bytes deterministic.
    --conf spark.sql.adaptive.optimizer.excludedRules=org.apache.spark.sql.execution.adaptive.AQEPropagateEmptyRelation
    --conf spark.eventLog.enabled=true
    --conf "spark.eventLog.dir=file://$RESULTS/eventlog"
)

submit_py() { "$SPARK_HOME/bin/spark-submit" "${SPARK_CONF[@]}" "$@"; }
submit_runner() {
    [ -f "$RUNNER_JAR" ] || { echo "runner jar missing: ./run_phase.sh setup"; exit 1; }
    "$SPARK_HOME/bin/spark-submit" "${SPARK_CONF[@]}" --class SortingRunner "$RUNNER_JAR" "$1"
}
plan_and_run() {  # phase [mode [k c]]
    local plan="$PLANS/$1${2:+_$2}${3:+_k$3}${4:+_c$4}.json"
    python3 "$HERE/make_runs.py" "$1" ${2:+--mode "$2"} ${3:+--k "$3"} ${4:+--c "$4"} \
        --manifest "$MANIFEST" --results "$RESULTS" --out "$plan"
    submit_runner "$plan" 2>&1 | tee -a "$RESULTS/$1${2:+_$2}.driver.log"
}
build() {  # base | layouts ...
    submit_py "$HERE/build_iceberg.py" "$@" --manifest "$MANIFEST" \
        --rg-rows "$RG_ROWS" --partitions "$PARTITIONS" \
        --base-props "$RESULTS/base_props.json" --stats "$RESULTS/build_stats.jsonl" \
        2>&1 | tee -a "$RESULTS/build.driver.log"
}

case "$STEP" in
setup)
    java -version 2>&1 | head -1
    "$SPARK_HOME/bin/spark-submit" --version 2>&1 | grep -E "version|Scala" | head -3
    if [ ! -f "$ICEBERG_JAR" ]; then
        curl -fL -o "$ICEBERG_JAR" "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.13/$ICEBERG_VERSION/iceberg-spark-runtime-3.5_2.13-$ICEBERG_VERSION.jar"
    fi
    ls -la "$ICEBERG_JAR"
    (cd "$HERE/runner" && mvn -q package)
    ls -la "$RUNNER_JAR"
    df -h "$WORK"
    ;;
check-source)
    "$ANALYSIS_PYTHON" - "$SOURCE_DIR" "$ROW_COUNTS" <<'EOF'
import json, os, sys
import pyarrow.parquet as pq
src, counts = sys.argv[1], json.load(open(sys.argv[2]))
bad = 0
for t, n in sorted(counts.items()):
    path = next((p for p in (f"{src}/{t}.parquet", f"{src}/{t}") if os.path.exists(p)), None)
    if path is None:
        print(f"MISSING {t}"); bad += 1; continue
    got = pq.ParquetDataset(path).read(columns=[]).num_rows
    flag = "" if got == n else f"  <-- expected {n:,}"
    bad += got != n
    print(f"{t:24s} {got:>12,}{flag}")
print("OK: row counts match" if not bad else f"{bad} MISMATCHES: stop and ask Tapan")
EOF
    ;;
build-base)    build base --source "$SOURCE_DIR" "$@" ;;
build-pilot)
    L=$(python3 -c "import json;print(json.load(open('$MANIFEST'))['pilot']['layout'])")
    build layouts --layouts "$L" --modes s,ps,pz ;;
build-layouts) build layouts --modes "${1:-ps}" ${2:+--layouts "$2"} "${@:3}" ;;
build-configs)
    L=$(python3 "$HERE/make_runs.py" configs --mode "${1:-ps}" --k "${2:-2}" --c "${3:-2}" \
        --print-layouts --manifest "$MANIFEST" --results "$RESULTS" --out /dev/null)
    echo "layouts needed: $L"
    build layouts --modes "${1:-ps}" --layouts "$L" ;;
explain)       plan_and_run explain ;;
pilot)         plan_and_run pilot ;;
configs)       plan_and_run configs "${1:-ps}" "${2:-2}" "${3:-2}" ;;
analyze)
    "$ANALYSIS_PYTHON" "$HERE/analyze_sweep.py" --manifest "$MANIFEST" --results "$RESULTS" \
        --mode "${1:-ps}" --metric "${2:-task_bytes_read,task_records_read}" ;;
plot)
    "$ANALYSIS_PYTHON" "$HERE/plot_workload_value.py" \
        --dir "$RESULTS/analysis/paper_${1:-ps}_k${2:-2}_c${3:-2}" ;;
*)
    sed -n '2,19p' "$0"; exit 1 ;;
esac
