#!/bin/bash
# §7 step 3: capture + convert all SFs, all 163 queries, with a driver-RSS / event-log monitor.
R=/mnt/tpcds/results_rg128k
export PARQUET_ROOT=/mnt/tpcds/parquet_rg128k RESULTS=$R QUERIES=1-163
mkdir -p $R/sf30 $R/sf60 $R/sf100
( while true; do
    pid=$(pgrep -f 'RowGroupCapture' | head -1)
    rss=$( [ -n "$pid" ] && ps -o rss= -p $pid 2>/dev/null | tr -d ' ' )
    el=$(du -sb $R/sf*/eventlog 2>/dev/null | awk '{printf "%s=%s ", $2, $1}')
    echo "$(date -u +%FT%TZ) pid=${pid:-none} rss_kb=${rss:-0} $(free -m | awk '/Mem/{print "avail_mb=" $7}') $el"
    sleep 30
  done ) > $R/capture_monitor.log 2>&1 &
MON=$!
cd $HOME/value_of_data/value-of-data-metric
oracle/scripts/run_capture_all.sh 30 60 100
kill $MON
