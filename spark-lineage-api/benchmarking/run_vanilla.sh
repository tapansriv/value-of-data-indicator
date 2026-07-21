#!/usr/bin/env bash
set -euo pipefail

# === Configuration ===
QUERY_DIR_TPCH="$HOME/tpch_queries_spark"
QUERY_DIR_TPCDS="$HOME/tpcds_queries_spark"
DATA_PATH_TPCH="/home/cc/tpch"
DATA_PATH_TPCDS="/home/cc/tpcds"
JAR_PATH="$HOME/query-runner.jar"
CLASS_NAME="QueryRunner"
OUTPUT="vanilla_results_r1to9.csv"

# === Header ===
[[ ! -f "$OUTPUT" ]] && echo "query,dataset,run_number,vanilla_time_sec" > "$OUTPUT"

# === Main loop: 9 runs x 2 datasets ===
for run_number in {1..9}; do
  for dataset in tpch tpcds; do
    if [[ "$dataset" == "tpch" ]]; then
      QUERY_DIR="$QUERY_DIR_TPCH"
      DATA_PATH="$DATA_PATH_TPCH"
    else
      QUERY_DIR="$QUERY_DIR_TPCDS"
      DATA_PATH="$DATA_PATH_TPCDS"
    fi

    for query_file in "$QUERY_DIR"/*.sql; do
      query_name=$(basename "$query_file")
      echo "Run $run_number – $dataset – $query_name"

      tmp=$(mktemp)
      if /usr/bin/time -o "$tmp" -f '%e' \
        spark-submit --driver-memory 50g --class "$CLASS_NAME" "$JAR_PATH" \
          "$query_file" "$DATA_PATH" >/dev/null 2>&1; then
        time_val=$(cat "$tmp")
      else
        echo "Vanilla FAILED for $query_name"
        time_val="fail"
      fi
      echo "$query_name,$dataset,$run_number,$time_val" >> "$OUTPUT"
      rm "$tmp"
    done
  done
done

echo "Vanilla baseline runs 1–9 completed → saved to $OUTPUT"
