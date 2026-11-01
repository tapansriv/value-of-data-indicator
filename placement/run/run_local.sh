#!/bin/bash 

DATA_DIR="/Users/tapansriv/value_of_data/value-of-data-metric/spark-lineage-api/tpcds/parquet"

python3 run.py --local-mode --data-dir $DATA_DIR $@
