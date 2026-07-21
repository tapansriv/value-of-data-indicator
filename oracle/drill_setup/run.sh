#!/bin/bash 
#
# for i in {23..38}
for i in 2 9 11 16 29
do
    # ls ~/value-of-data-metric/tpch_queries/"$i"_drill2.sql
    ./drill-embedded -f ~/value-of-data-metric/tpch_queries/"$i"_drill2.sql
    mkdir tpch_"$i"
    cp ../log/* tpch_"$i"
done
