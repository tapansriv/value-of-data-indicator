#!/bin/bash

# Run LRU and VoD both with and without pre-populating the cache and both with
# and without dynamically updating the data values as the workload runs.

python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy lru --outfile lru_cold_static_30gb_aws.json > lru_cold_static_30gb_aws.out 2>&1 
rm -rf ../metadata/cache
python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy vod --outfile vod_cold_static_30gb_aws.json > vod_cold_static_30gb_aws.out 2>&1
rm -rf ../metadata/cache                                                                                                                       
python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy vod --outfile vod_cold_dynamic_30gb_aws.json --dynamic > vod_cold_dynamic_30gb_aws.out 2>&1 
rm -rf ../metadata/cache


python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy lru --fill-cache --outfile lru_hot_static_30gb_aws.json > lru_hot_static_30gb_aws.out 2>&1
rm -rf ../metadata/cache
python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy vod --fill-cache --outfile vod_hot_static_30gb_aws.json > vod_hot_static_30gb_aws.out 2>&1
rm -rf ../metadata/cache
python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy vod --fill-cache --outfile vod_hot_dynamic_30gb_aws.json --dynamic > vod_hot_dynamic_30gb_aws.out 2>&1
rm -rf ../metadata/cache


ZIPFQV="../metadata/tpcds_query_values_zipf.csv"
ZIPFDV="../metadata/data_val_cols_zipf.json"

python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy lru --query-value-file $ZIPFQV --value-file $ZIPFDV --outfile lru_cold_static_30gb_aws_zipf.json > lru_cold_static_30gb_aws_zipf.out 2>&1 
rm -rf ../metadata/cache
python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy vod --query-value-file $ZIPFQV --value-file $ZIPFDV --outfile vod_cold_static_30gb_aws_zipf.json > vod_cold_static_30gb_aws_zipf.out 2>&1
rm -rf ../metadata/cache                                                                                                                       
python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy vod --query-value-file $ZIPFQV --value-file $ZIPFDV --outfile vod_cold_dynamic_30gb_aws_zipf.json --dynamic > vod_cold_dynamic_30gb_aws_zipf.out 2>&1 
rm -rf ../metadata/cache


python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy lru --query-value-file $ZIPFQV --value-file $ZIPFDV --fill-cache --outfile lru_hot_static_30gb_aws_zipf.json > lru_hot_static_30gb_aws_zipf.out 2>&1
rm -rf ../metadata/cache
python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy vod --query-value-file $ZIPFQV --value-file $ZIPFDV --fill-cache --outfile vod_hot_static_30gb_aws_zipf.json > vod_hot_static_30gb_aws_zipf.out 2>&1
rm -rf ../metadata/cache
python3 run_sim.py --s3-region us-east-2 --max-cache-size 2.75 --policy vod --query-value-file $ZIPFQV --value-file $ZIPFDV --fill-cache --outfile vod_hot_dynamic_30gb_aws_zipf.json --dynamic > vod_hot_dynamic_30gb_aws_zipf.out 2>&1
rm -rf ../metadata/cache





