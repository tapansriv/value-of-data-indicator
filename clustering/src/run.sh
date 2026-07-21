#!/bin/bash


# ITERS=(0 1 2 3 4)
ITERS=(0)

for iter in ${ITERS[@]}
do
    rm -rf ~/tpcds_cluster_freq
    rm -rf ~/tpcds_cluster_rand
    rm -rf ~/tpcds_cluster_value
    

    python3 cluster.py --value-iter $iter > cluster_"$iter"
    python3 validate_tables.py > validate_"$iter"
    python3 rewrite_queries.py --value-iter $iter > rewrite_"$iter"
    python3 validate_rewritten_queries.py > validate_qs_"$iter"

    echo "========================"

    python3 run.py --value-iter $iter > run_"$iter"
    rm test
done

