#!/usr/bin/env bash
set -euo pipefail

# ── Paths to query folders ─────────────────────────────────────────────
QUERY_DIR_TPCH="$HOME/tpch_queries_spark"
QUERY_DIR_TPCDS="$HOME/tpcds_queries_spark"
DATA_PATH_TPCH="/home/cc/tpch"
DATA_PATH_TPCDS="/home/cc/tpcds"

# ── JARs & classes ─────────────────────────────────────────────────────
BARE_JAR="$HOME/spark-bare-listener.jar"
NOWRITE_JAR="$HOME/spark-query-api-no-write.jar"
FULL_JAR="$HOME/spark-lineage-api.jar"
REGISTER_JAR="$HOME/spark-listener-just-register.jar"
# RG_JAR="$HOME/spark-rowgroup.jar"

CLASS_LISTENER="LineageAPI"

# ── Output CSVs ─────────────────────────────────────────────────────────
OUT_BARE="listener_bare_results_r1to9.csv"
OUT_NOWRITE="listener_nowrite_results_r1to9.csv"
OUT_FULL="listener_full_results_r1to9.csv"
OUT_REGISTER="listener_register_results_r1to9.csv"
# OUT_RG="listener_rg_results_r1to9.csv"

[[ ! -f "$OUT_BARE"     ]] && echo "query,dataset,run_number,listener_bare_time"      > "$OUT_BARE"
[[ ! -f "$OUT_NOWRITE"  ]] && echo "query,dataset,run_number,listener_nowrite_time"   > "$OUT_NOWRITE"
[[ ! -f "$OUT_FULL"     ]] && echo "query,dataset,run_number,listener_time_sec"       > "$OUT_FULL"
[[ ! -f "$OUT_REGISTER" ]] && echo "query,dataset,run_number,listener_register_time"  > "$OUT_REGISTER"
# [[ ! -f "$OUT_RG"       ]] && echo "query,dataset,run_number,listener_register_time"  > "$OUT_RG"

# ── Main loop: runs 1–9 ────────────────────────────────────────────────
for run_number in {1..9}; do
  for dataset in tpch tpcds; do
    if [[ "$dataset" == "tpch" ]]; then
      QUERY_DIR="$QUERY_DIR_TPCH"; DATA_PATH="$DATA_PATH_TPCH"
    else
      QUERY_DIR="$QUERY_DIR_TPCDS"; DATA_PATH="$DATA_PATH_TPCDS"
    fi
    # log_basedir="$dataset"_logs
    # mkdir -p $log_basedir

    for query_file in "$QUERY_DIR"/*.sql; do
      query_name=$(basename "$query_file")
      echo "Run $run_number – $dataset – $query_name"
      # log_dir="$log_basedir"/"$query_name"
      # mkdir -p $log_dir

      run_variant () {
        local jar=$1 class=$2
        local tmp=$(mktemp)
        if /usr/bin/time -o "$tmp" -f '%e' \
             spark-submit --driver-memory 50g --class "$class" \
               --conf spark.sql.adaptive.enabled=false \
               --conf spark.sql.execution.reuseSubquery=false \
               --conf spark.sql.exchange.reuse=false \
               "$jar" \
               parquet "$DATA_PATH" "$query_file" /tmp/iceberg/warehouse/usage_logs my_catalog \
               >/dev/null 2>&1; then
          cat "$tmp"
        else
          echo "fail"
        fi
        rm -f "$tmp"
      }

      # Bare
      bare_time=$(run_variant "$BARE_JAR" "$CLASS_LISTENER")
      echo "$query_name,$dataset,$run_number,$bare_time" >> "$OUT_BARE"

      # No-write
      nowrite_time=$(run_variant "$NOWRITE_JAR" "$CLASS_LISTENER")
      echo "$query_name,$dataset,$run_number,$nowrite_time" >> "$OUT_NOWRITE"

      # Full
      full_time=$(run_variant "$FULL_JAR" "$CLASS_LISTENER")
      echo "$query_name,$dataset,$run_number,$full_time" >> "$OUT_FULL"

      # Just-register (do-nothing)
      register_time=$(run_variant "$REGISTER_JAR" "$CLASS_LISTENER")
      echo "$query_name,$dataset,$run_number,$register_time" >> "$OUT_REGISTER"

      # # Rowgroup 
      # register_time=$(run_variant "$RG_JAR" "$CLASS_LISTENER")
      # echo "$query_name,$dataset,$run_number,$register_time" >> "$OUT_RG"
      # echo "Finished $query_name (run $run_number)"

      # if [ $run_number -eq 1 ]; then 
      #     mv /tmp/iceberg/warehouse/usage_logs $log_dir > /dev/null 2>&1 || true
      # fi
    done
  done
done

echo "Runs 1–9 completed for all listener variants."
echo "  • $OUT_REGISTER"
echo "  • $OUT_BARE"
echo "  • $OUT_NOWRITE"
echo "  • $OUT_FULL"
# echo "  • $OUT_RG"
