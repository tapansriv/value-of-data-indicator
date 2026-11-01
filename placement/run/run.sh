#!/bin/bash

# Run LRU and VoD both with and without pre-populating the cache and both with
# and without dynamically updating the data values as the workload runs.

QV="../metadata/tpcds_query_values_custom.csv"
DV="../metadata/data_val_cols_custom.json"
ITER=0

SIZES=(2.75 3.5 5.0 7.5 13.75)

for size in ${SIZES[@]}; do
    mkdir customv3_"$ITER"_"$size"
    python3 run.py --s3-region us-east-2 --max-cache-size $size --policy lru \
                   --query-value-file $QV --value-file $DV --fill-cache  \
                   --value-iter $ITER \
                   --outfile lru_hot_static_30gb_aws_custom_$size.json > lru_hot_static_30gb_aws_custom_$size.out 2>&1
    rm -rf ../metadata/cache

    python3 run.py --s3-region us-east-2 --max-cache-size $size --policy vod \
                   --query-value-file $QV --value-file $DV --fill-cache \
                   --value-iter $ITER \
                   --outfile vod_hot_static_30gb_aws_custom_$size.json > vod_hot_static_30gb_aws_custom_$size.out 2>&1
    rm -rf ../metadata/cache

    python3 run.py --s3-region us-east-2 --max-cache-size $size --policy vod \
                   --query-value-file $QV --value-file $DV --fill-cache  \
                   --value-iter $ITER \
                   --outfile vod_hot_dynamic_30gb_aws_custom_$size.json --dynamic > vod_hot_dynamic_30gb_aws_custom_$size.out 2>&1
    rm -rf ../metadata/cache
    mv *.out *.json customv3_"$ITER"_"$size"
done

