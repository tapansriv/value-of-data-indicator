set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────
# Define the BASE directory where all query parts are now located.
# The script will run through: $QUERY_BASE_DIR/part1, $QUERY_BASE_DIR/part2, etc.
QUERY_BASE_DIR="$HOME/tpcds_cols_remaining"

# Define the 5 specific query folders to iterate over
QUERY_PARTS=("part1" "part2" "part3" "part4" "part5")

# ── Data Paths ─────────────────────────────────────────────────────────
DATA_PATH_TPCH="/mnt/data_1tb/tpch"
DATA_PATH_TPCDS="/mnt/data_1tb/tpcds"

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

  # The inner loop is removed. The Spark job will now run ALL queries
  # contained in the "$query_folder" argument passed to the Scala application.

  echo "Running all queries in $(basename "$query_folder")"

  # --- Spark Submission Command ---
  # Memory changed to 50g
  if /usr/bin/time -o "$tmp" -f '%e' \
        spark-submit --driver-memory 50g --class "$class" \
          --conf spark.sql.adaptive.enabled=false \
          --conf spark.sql.execution.reuseSubquery=false \
          --conf spark.sql.exchange.reuse=false \
          "$jar" \
          parquet "$DATA_PATH" "$query_folder" /mnt/logs/usage_logs my_catalog \
    >/dev/null 2>&1; then
     cat "$tmp"
  else
    # Changed fail message to indicate which folder failed
    echo "fail - $(basename "$query_folder")"
  fi

  rm -f "$tmp"
}
# ───────────────────────────────────────────────────────────────────────


# ── Main Execution Loop ────────────────────────────────────────────────
for dataset in tpcds tpch; do
  if [[ "$dataset" == "tpch" ]]; then
    DATA_PATH="$DATA_PATH_TPCH"
  else
    DATA_PATH="$DATA_PATH_TPCDS"
  fi

  # --- New Outer Loop: Iterates through the 5 folders ---
  for part_folder in "${QUERY_PARTS[@]}"; do
    QUERY_DIR_FULL="$QUERY_BASE_DIR/$part_folder"

    echo ">>> STARTING FOLDER: $part_folder for $dataset <<<"

    # All calls pass the folder name as the third argument ($QUERY_DIR_FULL).

   #echo "vanilla", "$dataset"
   #run_variant "$VANILLA_JAR" "$CLASS_LISTENER" "$QUERY_DIR_FULL"

   #echo "bare", "$dataset"
   #run_variant "$BARE_JAR" "$CLASS_LISTENER" "$QUERY_DIR_FULL"

   # echo "nowrite", "$dataset"
   # run_variant "$NOWRITE_JAR" "$CLASS_LISTENER" "$QUERY_DIR_FULL"

    echo "full", "$dataset"
    run_variant "$FULL_JAR" "$CLASS_LISTENER" "$QUERY_DIR_FULL"

    #echo "register", "$dataset"
    #run_variant "$REGISTER_JAR" "$CLASS_LISTENER" "$QUERY_DIR_FULL"

    #echo "rowgroup", "$dataset"
    #run_variant "$RG_JAR" "$CLASS_LISTENER" "$QUERY_DIR_FULL"


  done
done

echo "All query parts and listener variants completed."