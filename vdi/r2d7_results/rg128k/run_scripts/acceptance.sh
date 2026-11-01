#!/bin/bash
# Spark acceptance check for authored queries 132-163 (+ their 8 bases), REVISION_R2D7_RG128K.md §5.3.
# Same engine, jar and Spark conf as the capture (run_spark_sf.sh capture), no event log, separate out dir.
# Usage: acceptance.sh <SF>
set -euo pipefail
SF=$1
R=/mnt/tpcds/results_rg128k
QD=$R/sf$SF/acceptance/queries
OUT=$R/sf$SF/acceptance/capture
SRC=$HOME/value_of_data/value-of-data-metric/spark-lineage-api/benchmarking/tpcds_queries_spark
rm -rf "$QD" "$OUT"; mkdir -p "$QD" "$OUT" /mnt/tpcds/spark-tmp/sf$SF
for q in 3 12 20 22 84 91 30 26 $(seq 132 163); do cp "$SRC/query$q.sql" "$QD/"; done
/home/cc/value_of_data/spark/bin/spark-submit --class RowGroupCapture --master 'local[*]' --driver-memory 48g \
  --conf spark.speculation=false --conf spark.local.dir=/mnt/tpcds/spark-tmp/sf$SF \
  $HOME/spark-rowgroup-capture.jar /mnt/tpcds/parquet_rg128k/sf$SF "$QD" "$OUT" 1-163 > "$OUT/driver.log" 2>&1
cd $HOME/value_of_data/value-of-data-metric/oracle/scripts
$HOME/vdi-venv/bin/python rg_selective_accept.py --capture-dir "$OUT" --parquet-dir /mnt/tpcds/parquet_rg128k/sf$SF \
  --calib $R/sf30/rg_selective_calibration.json --out $R/sf$SF/acceptance/rg_selective_acceptance.json
