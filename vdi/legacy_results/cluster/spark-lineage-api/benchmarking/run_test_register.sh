#!/bin/bash
set -u

# ── Configuration ──────────────────────────────────────────────────────
QUERY_BASE_DIR="$HOME/tpcds_register_remaining"
QUERY_PARTS=("part1" "part2" "part3" "part4" "part5")

# ── Data Paths ─────────────────────────────────────────────────────────
DATA_PATH_TPCH="/mnt/tpch_1tb/data"
DATA_PATH_TPCDS="/mnt/tpcds_1tb/parquet"

# ── JARs & classes ─────────────────────────────────────────────────────
VANILLA_JAR="$HOME/spark-vanilla.jar"
BARE_JAR="$HOME/spark-bare-listener.jar"
NOWRITE_JAR="$HOME/spark-query-api-no-write.jar"
FULL_JAR="$HOME/spark-lineage-api.jar"
REGISTER_JAR="$HOME/spark-listener-just-register.jar"
RG_JAR="$HOME/spark-rowgroup.jar"
CLASS_LISTENER="LineageAPI"

# ───────────────────────────────────────────────────────────────────────
run_variant () {
  local jar=$1 class=$2 query_file=$3
  local query_name=$(basename "$query_file")
  local tmp_time=$(mktemp)
  local tmp_log=$(mktemp)

  # ── TRICK THE JAR (Wrapper Directory) ──
  local temp_isolation_dir="/tmp/spark_isolation_${query_name%.*}"
  rm -rf "$temp_isolation_dir"
  mkdir -p "$temp_isolation_dir"
  cp "$query_file" "$temp_isolation_dir/"

  echo -n "Running $query_name ... "

  # ── RUN SPARK (SAFE NODE HOG MODE) ──
  # We construct the command as a single array to avoid backslash/space errors.

  CMD=(
    spark-submit
    --master "spark://controller:7077"
    --driver-memory "4g"
    --executor-memory "45g"
    --executor-cores "30"
    --conf "spark.task.cpus=30"
    --class "$class"
    --conf "spark.sql.shuffle.partitions=2000"
    --conf "spark.memory.offHeap.enabled=true"
    --conf "spark.memory.offHeap.size=4g"
    --conf "spark.sql.autoBroadcastJoinThreshold=-1"
    --conf "spark.task.maxFailures=10"
    --conf "spark.executor.heartbeatInterval=200s"
    --conf "spark.network.timeout=3600s"
    --conf "spark.shuffle.io.maxRetries=20"
    --conf "spark.shuffle.io.retryWait=60s"
    --conf "spark.reducer.maxSizeInFlight=24m"
    --conf "spark.rpc.askTimeout=600s"
    --conf "spark.sql.adaptive.enabled=false"
    --conf "spark.sql.execution.reuseSubquery=false"
    --conf "spark.sql.exchange.reuse=false"
    "$jar"
    parquet
    "$DATA_PATH"
    "$temp_isolation_dir"
    "/mnt/logs/usage_logs"
    "my_catalog"
  )

  # Run the command and capture time
  /usr/bin/time -o "$tmp_time" -f '%e' "${CMD[@]}" > "$tmp_log" 2>&1

  SPARK_EXIT_CODE=$?

  # ── VALIDATION ──
  if [ $SPARK_EXIT_CODE -eq 0 ] && ! grep -q "Query failed:" "$tmp_log"; then
     local duration=$(cat "$tmp_time")
     echo "SUCCESS ($duration s)"
  else
     echo "FAILED"
     # Uncomment the next line to see why it failed if needed
     # head -n 20 "$tmp_log"
  fi

  # ── CLEANUP ──
  rm -rf "$temp_isolation_dir"
  rm -f "$tmp_time"
  rm -f "$tmp_log"
}

# ── Main Execution Loop ────────────────────────────────────────────────
for dataset in tpcds; do
  if [[ "$dataset" == "tpch" ]]; then
    DATA_PATH="$DATA_PATH_TPCH"
  else
    DATA_PATH="$DATA_PATH_TPCDS"
  fi

  for part_folder in "${QUERY_PARTS[@]}"; do
    QUERY_DIR_FULL="$QUERY_BASE_DIR/$part_folder"
    if [ ! -d "$QUERY_DIR_FULL" ]; then
        continue
    fi

    echo ">>> FOLDER: $part_folder <<<"
    for query_file in "$QUERY_DIR_FULL"/*.sql; do
        run_variant "$REGISTER_JAR" "$CLASS_LISTENER" "$query_file"
    done
  done
done

echo "Benchmark completed."
