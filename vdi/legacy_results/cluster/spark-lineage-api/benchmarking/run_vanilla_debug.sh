set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────
# Define the BASE directory where all query parts are now located.
# The script will run through: $QUERY_BASE_DIR/part1, $QUERY_BASE_DIR/part2, etc.
QUERY_BASE_DIR="$HOME/tpcds_queries_spark"

# Define the 5 specific query folders to iterate over
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
# Use the correct JARs from your existing script here.

CLASS_LISTENER="LineageAPI"

# ── Queries to skip (MUST match the filename format found in the part folders) ──
# This array is no longer used for query-by-query skipping since the inner loop is removed.
# SKIP_QUERIES=("64.sql" "85.sql" "17.sql")

# ───────────────────────────────────────────────────────────────────────
run_variant () {
  local jar=$1 class=$2 query_folder=$3
  local tmp=$(mktemp)
  local log_file="query17_debug.log"

  echo "Running Query 17 in $query_folder"

  # Added stability configs for TPC-DS Query 17
  if /usr/bin/time -o "$tmp" -f '%e' \
        spark-submit --master spark://controller:7077 \
        --driver-memory 50g \
        --executor-memory 50g \
        --executor-cores 4 \
        --class "$class" \
        --conf spark.sql.adaptive.enabled=false \
        --conf spark.sql.execution.reuseSubquery=false \
        --conf spark.sql.exchange.reuse=false \
        --conf spark.sql.shuffle.partitions=2000 \
        --conf spark.sql.broadcastTimeout=3600 \
        --conf spark.driver.maxResultSize=4g \
        "$jar" \
        parquet "$DATA_PATH" "$query_folder" /mnt/logs/usage_logs my_catalog \
    2>&1 | tee "$log_file"; then
     echo "Success! Time taken: $(cat "$tmp")s"
  else
    echo "FAILED - Check $log_file for the stack trace."
    echo "Top Error Clues:"
    grep -Ei "exception|error|caused by" "$log_file" | tail -n 5
  fi

  rm -f "$tmp"
}
# ───────────────────────────────────────────────────────────────────────


# ── Main Execution Loop ────────────────────────────────────────────────
for dataset in tpcds; do
  DATA_PATH="$DATA_PATH_TPCDS"

  # We only care about the folder where query17.sql lives (likely part1 or part2)
  # Update this folder name to whichever 'part' contains query17.sql
  part_folder="part1"
  QUERY_DIR_FULL="$QUERY_BASE_DIR/$part_folder"

  echo ">>> TARGETING QUERY 17 in $part_folder <<<"
  run_variant "$VANILLA_JAR" "$CLASS_LISTENER" "$QUERY_DIR_FULL"
  done

