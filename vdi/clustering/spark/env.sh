# Paths for the sorting experiment on the Chameleon node. Sourced by run_phase.sh.
# Every value can be overridden from the environment. Confirm each one on the node
# before the first run (NODE_RUNBOOK.md, step 1) and edit here if it differs.

# The rowgroup-dev Spark fork (Scala 2.13, Java 17). Same build the R2D7 runs used.
export SPARK_HOME="${SPARK_HOME:-/home/cc/value_of_data/spark}"

# Which workload (clustering/src/workload.py): tpcds (default, the published setup) or
# imdb (Redbench IMDb, R3D4). A non-TPC-DS workload gets its own subtree under $WORK, so it
# can never touch the TPC-DS catalog, results or plans.
export WORKLOAD="${WORKLOAD:-tpcds}"

# Everything the experiment writes lives under one mounted disk.
export WORK="${WORK:-/mnt/tpcds/vdi_sort}"
if [ "$WORKLOAD" = tpcds ]; then _WL_DIR="$WORK"; else _WL_DIR="$WORK/$WORKLOAD"; fi

# Source Parquet: a directory holding <table>.parquet (file or directory) for every table.
# TPC-DS SF30 candidates seen before: /home/cc/tpcds_30gb (DuckDB-era run) and
# /mnt/tpcds/parquet/sf30 (R2D7). Either works: everything is rewritten into Iceberg.
# IMDb: redbench_imdb/load_imdb_parquet.py writes $WORK/imdb/source.
if [ "$WORKLOAD" = tpcds ]; then _SRC_DEFAULT=/mnt/tpcds/parquet/sf30; else _SRC_DEFAULT="$_WL_DIR/source"; fi
export SOURCE_DIR="${SOURCE_DIR:-$_SRC_DEFAULT}"

export WAREHOUSE="$_WL_DIR/warehouse"   # Iceberg Hadoop catalog
export RESULTS="$_WL_DIR/results"       # runner output, build stats, event logs, usage logs
export PLANS="$_WL_DIR/plans"
export SPARK_TMP="$WORK/spark-tmp"

# Iceberg runtime for Spark 3.5 / Scala 2.13. setup downloads it here.
export ICEBERG_VERSION="${ICEBERG_VERSION:-1.8.1}"
export ICEBERG_JAR="${ICEBERG_JAR:-$WORK/jars/iceberg-spark-runtime-3.5_2.13-$ICEBERG_VERSION.jar}"

# Rows per Parquet row group and the partition count P of the partition rule. Keep the
# defaults for real runs; they are parameters only so the pipeline can be smoke-tested.
export RG_ROWS="${RG_ROWS:-128000}"
export PARTITIONS="${PARTITIONS:-32}"

export DRIVER_MEM="${DRIVER_MEM:-48g}"
export PYSPARK_PYTHON="${PYSPARK_PYTHON:-python3}"

# Python for check-source, analyze and plot (needs pyarrow, pandas, matplotlib). On the
# Chameleon node the system python3 has none of them; /home/cc/vdi-venv has all three.
export ANALYSIS_PYTHON="${ANALYSIS_PYTHON:-/home/cc/vdi-venv/bin/python}"
