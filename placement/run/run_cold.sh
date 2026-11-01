#!/bin/bash

python3 run_cold.py --s3-region us-east-2 --max-cache-size 15 --policy lru --outfile cold_runtimes.json > cold_runtimes.out 2>&1 
