#!/usr/bin/env bash 
set -euo pipefail

QUERY_DIR_TPCH="./benchmarking/extra_queries/extra_tpch/spark"
QUERY_DIR_TPCDS="./benchmarking/extra_queries/extra_tpcds/spark"
DATA_PATH_TPCH="tpch/parquet"
DATA_PATH_TPCDS="tpcds/parquet"

RUN_JAR="target/spark-rowgroup-listener-1.0.0.jar"
CLASS_LISTENER="LineageAPI"

for dataset in tpch tpcds; do
  if [[ "$dataset" == "tpch" ]]; then
    QUERY_DIR="$QUERY_DIR_TPCH"; DATA_PATH="$DATA_PATH_TPCH"
  else
    QUERY_DIR="$QUERY_DIR_TPCDS"; DATA_PATH="$DATA_PATH_TPCDS"
  fi

  for query_file in "$QUERY_DIR"/*.sql; do
    query_name=$(basename "$query_file")
    echo "Run $dataset – $query_name"

    spark-submit --driver-memory 50g --class "$CLASS_LISTENER" \
      --conf spark.sql.adaptive.enabled=false \
      --conf spark.sql.execution.reuseSubquery=false \
      --conf spark.sql.exchange.reuse=false \
      "$RUN_JAR" \
      parquet "$DATA_PATH" "$query_file" usage_logs my_catalog \
      2>/dev/null
  done
done
