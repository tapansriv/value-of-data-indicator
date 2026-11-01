#!/bin/bash
# §7 step 4 + §8: query set, VDI, and every downstream analysis/figure for the rg128k rerun.
# Same commands as r2d7_results/SEC44_RERUN_NOTE.md "Reproducing", pointed at $R and query_set_131.json.
# Per-SF single-threaded jobs run concurrently (40 cores). Run inside tmux. Logs: $R/logs_downstream/.
set -uo pipefail
R=/mnt/tpcds/results_rg128k
PY=$HOME/vdi-venv/bin/python
export PARQUET_ROOT=/mnt/tpcds/parquet_rg128k RESULTS=$R QUERIES=1-163
QS=$R/query_set_131.json
L=$R/logs_downstream; mkdir -p $L
S=$HOME/value_of_data/value-of-data-metric/oracle/scripts
cd $S
ts() { date -u +%FT%TZ; }
fail=0
step() { local name=$1; shift; echo "$(ts) START $name"; local t0=$(date +%s)
         if "$@" > $L/$name.log 2>&1; then echo "$(ts) OK $name $(( $(date +%s)-t0 ))s";
         else echo "$(ts) FAIL $name rc=$? (see $L/$name.log)"; fail=1; fi; }

# 1. common set and the 131-query VDI set: common ∩ (1-99 ∪ 132-163)  (§6)
step common ./run_spark_sf.sh common 30 60 100
$PY - $R/common_completed_sf30_60_100.json $QS <<'EOF'
import json, sys
common = json.load(open(sys.argv[1]))
want = set(range(1, 100)) | set(range(132, 164))
qs = sorted(q for q in common if q in want)
json.dump(qs, open(sys.argv[2], "w"))
print(f"common {len(common)}; query_set_131: {len(qs)} queries; missing from 1-99 ∪ 132-163: "
      f"{sorted(want - set(qs))}; excluded (100-131): {sorted(set(common) - want)}")
EOF

# 2. VDI per SF, concurrently
for SF in 30 60 100; do step vdi_sf$SF ./run_spark_sf.sh vdi $SF $QS & done; wait

# 3. concurrently: compare_sf + figures + summaries | history sweep per SF | draws pool per SF
(
  step compare_sf $PY compare_sf.py --results $R --out $R/sf_comparison.json
  for SF in 30 60 100; do
    step fig_sf$SF $PY graph_comp_oracles.py --distro zipf --tpcds-only --ylim 1.0 \
        --data-dir $R/sf$SF/vdi --fig-dir $R/sec44_after/figs_sf$SF
    step summary_sf$SF $PY sec44_summary.py --data-dir $R/sf$SF/vdi --tpcds-only --label spark_sf$SF \
        --out $R/sec44_after/sec44_numbers_spark_sf$SF.csv
  done
) &
for SF in 30 60 100; do
  ( step sweep_sf$SF $PY sweep_history.py --seeds 42 43 44 45 46 --distro zipf --no-plots --tpcds-only \
        --logs-dir $R/sf$SF/logs --values-dir $R/sf$SF/values \
        --columns-in-queries $R/sf$SF/tpcds_columns_in_queries.json \
        --cardinality $R/sf$SF/tpcds_cardinality.json --query-set $QS \
        --data-root $R/sweep/r2d7_sf$SF --fig-root $R/sweep_figs/r2d7_sf$SF
    step sweep_analyze_sf$SF $PY analyze_history_sweep.py --tpcds-only --data-root $R/sweep/r2d7_sf$SF \
        --out-dir $R/history_sweep/sf$SF ) &
  step draws_pool_sf$SF $PY draws_convergence.py --results $R --query-set $QS --sfs $SF --build-only \
      --pool-root $R/draws_pool --out-dir $R/num_draws &
done
wait

# 4. draws analysis (all SFs), display set, candidate paper figures
step draws $PY draws_convergence.py --results $R --query-set $QS --pool-root $R/draws_pool --out-dir $R/num_draws
step select_display $PY select_display_tables.py $R
DISP=$(grep '^DISPLAY SET:' $L/select_display.log | sed 's/^DISPLAY SET: //')
echo "display set: $DISP"
for SF in 30 60 100; do
  step paper_fig_sf$SF $PY graph_comp_oracles.py --distro zipf --tpcds-only --ylim 1.0 --tables "$DISP" \
      --data-dir $R/sf$SF/vdi --fig-dir $R/paper_figs/sf$SF
  step convergence_sf$SF $PY convergence_figure.py --sf $SF --tables "$DISP" --results $R \
      --pool-root $R/draws_pool --sweep-root $R/sweep --out-dir $R/paper_figs/convergence
done
echo "$(ts) DOWNSTREAM DONE fail=$fail"
