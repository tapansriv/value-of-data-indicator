#!/bin/bash
# Draws-ordering check on the 7-table display set (the tables §4.4 now shows and names),
# reusing the existing 2000-draw pools in $R/draws_pool. The original num_draws/ run checked
# only FIGURE_TABLES_TPCDS (the old 6-table figure). Analysis only: no pool rebuild, ~4 min.
#
# From the laptop:
#   scp oracle/scripts/draws_convergence.py node:value_of_data/value-of-data-metric/oracle/scripts/draws_convergence_tables.py
#   scp r2d7_results/rg128k/run_scripts/draws_disp7.sh node:
#   ssh node 'tmux new -d -s draws7 "bash ~/draws_disp7.sh"'
#   # when done:
#   rsync -av node:/mnt/tpcds/results_rg128k/num_draws_disp7/ r2d7_results/rg128k/num_draws_disp7/
set -euo pipefail
R=/mnt/tpcds/results_rg128k
PY=$HOME/vdi-venv/bin/python
DISP=date_dim,item,store_sales,tpcds.customer,store,catalog_returns,inventory
OUT=$R/num_draws_disp7
mkdir -p $OUT
cd $HOME/value_of_data/value-of-data-metric/oracle/scripts
# The pool must already exist; build_pool() skips when manifest.json is present.
for SF in 30 60 100; do test -f $R/draws_pool/sf$SF/vdi/manifest.json || { echo "missing pool sf$SF"; exit 1; }; done
$PY draws_convergence_tables.py --results $R --query-set $R/query_set_131.json \
    --pool-root $R/draws_pool --out-dir $OUT --tables "$DISP" 2>&1 | tee $OUT/run.log
echo "DONE $(date -u +%FT%TZ)" | tee -a $OUT/run.log
