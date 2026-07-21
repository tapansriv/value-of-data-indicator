#!/usr/bin/env bash
set -euo pipefail

# ── Paths to query folders ─────────────────────────────────────────────
QUERY_DIR_TPCH="$HOME/tpch_queries_spark"
QUERY_DIR_TPCDS="$HOME/tpcds_queries_spark"
DATA_PATH_TPCH="/mnt/data_1tb/tpch"
DATA_PATH_TPCDS="/mnt/data_1tb/tpcds"

# ── JARs & classes ─────────────────────────────────────────────────────
VANILLA_JAR="$HOME/spark-vanilla.jar"
BARE_JAR="$HOME/spark-bare-listener.jar"
NOWRITE_JAR="$HOME/spark-query-api-no-write.jar"
FULL_JAR="$HOME/spark-lineage-api.jar"
REGISTER_JAR="$HOME/spark-listener-just-register.jar"
RG_JAR="$HOME/spark-rowgroup.jar"

CLASS_LISTENER="LineageAPI"

# ── Queries to skip ────────────────────────────────────────────────
SKIP_QUERIES=("query64.sql" "query85.sql" "query17.sql" "query131.sql" "query112.sql" "query39.sql" "query58.sql" "query36.sql" "query121.sql" "query115.sql" "query20.sql" "query22.sql" "query24.sql" "query49.sql" "query83.sql" "query71.sql" "query108.sql" "query11.sql" "query125.sql" "query5.sql" "query116.sql" "query6.sql" "query92.sql" "query104.sql" "query88.sql"
)

# ── Main loop: runs 1–3 ────────────────────────────────────────────────
for dataset in tpcds; do
  if [[ "$dataset" == "tpch" ]]; then
    QUERY_DIR="$QUERY_DIR_TPCH"; DATA_PATH="$DATA_PATH_TPCH"
  else
    QUERY_DIR="$QUERY_DIR_TPCDS"; DATA_PATH="$DATA_PATH_TPCDS"
  fi

  run_variant () {
    local jar=$1 class=$2
    local tmp=$(mktemp)
    for query in "$QUERY_DIR"/*.sql; do
      query_name=$(basename "$query")
      for skip_query in "${SKIP_QUERIES[@]}"; do
  if [[ "$query_name" == "$skip_query" ]]; then
    echo "Skipping $query_name"
    continue 2
  fi
done
    if /usr/bin/time -o "$tmp" -f '%e' \
         spark-submit --driver-memory 58g --class "$class" \
           --conf spark.sql.adaptive.enabled=false \
           --conf spark.sql.execution.reuseSubquery=false \
           --conf spark.sql.exchange.reuse=false \
           "$jar" \
           parquet "$DATA_PATH" "$QUERY_DIR" /mnt/logs/usage_logs my_catalog \
	   >/dev/null 2>&1; then
      cat "$tmp"
    else
      echo "fail"
    fi
    done
    rm -f "$tmp"
  }

  echo "vanilla", "$dataset"
  run_variant "$VANILLA_JAR" "$CLASS_LISTENER"

  echo "bare", "$dataset"
  run_variant "$BARE_JAR" "$CLASS_LISTENER"

  echo "nowrite", "$dataset"
  run_variant "$NOWRITE_JAR" "$CLASS_LISTENER"

  echo "full", "$dataset"
  run_variant "$FULL_JAR" "$CLASS_LISTENER"

  echo "register", "$dataset"
  run_variant "$REGISTER_JAR" "$CLASS_LISTENER"

  echo "rowgroup", "$dataset"
  run_variant "$RG_JAR" "$CLASS_LISTENER"
done

echo "Runs 1–3 completed for all listener variants."

