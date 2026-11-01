#!/bin/bash

echo "Starting 6-script TPCDS sequence..."

./run_test_vanilla.sh && \

./run_test_bare.sh && \

./run_test_register.sh && \

./run_test_nowrite.sh && \

./run_test_cols.sh && \

./run_test_rowgroup.sh
