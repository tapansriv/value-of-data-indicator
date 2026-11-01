#!/bin/bash
# Health probe, run ON THE DRIVER by 45_status.sh (piped over ssh; not installed). Read-only.
# Prints one "LEVEL|message" line per check, LEVEL in OK / WARN / ALERT.
#
# Args: <expected-workers> [run-id]   (expected-workers = 0 for a local-mode run)
EXPECTED=$1 RUN_ID=${2:-}
emit() { echo "$1|$2"; }
now=$(date +%s)
fmt_dur() { printf '%dh%02dm' $(($1 / 3600)) $(($1 % 3600 / 60)); }

# ── Cluster ──
if [ "$EXPECTED" != 0 ]; then
    # The master UI binds to the private IP (SPARK_LOCAL_IP), not localhost.
    alive=$(curl -fs --max-time 10 "http://$(hostname -I | awk '{print $1}'):8080/json/" | jq -r .aliveworkers 2>/dev/null)
    if [ "$alive" = "$EXPECTED" ]; then emit OK "master: $alive/$EXPECTED workers alive"
    else emit ALERT "master: ${alive:-unreachable}/$EXPECTED workers alive"; fi
fi

pct=$(df --output=pcent / | tail -1 | tr -dc 0-9)
if   [ "$pct" -ge 85 ]; then emit ALERT "driver disk ${pct}% used"
elif [ "$pct" -ge 70 ]; then emit WARN  "driver disk ${pct}% used"
else emit OK "driver disk ${pct}% used"; fi

pid=$(pgrep -f 'org.apache.spark.deploy.SparkSubmit' | head -1)
if [ -n "$pid" ]; then
    # Used heap against the maximum (-Xmx = --driver-memory), not the committed size,
    # which G1 grows on its own. A point sample: high values right before a GC are
    # normal, so only a sustained ALERT across checks means trouble.
    used_k=$(jcmd "$pid" GC.heap_info 2>/dev/null | awk '/heap/ && /used/ { for (i=1;i<=NF;i++) if ($i=="used") { u=$(i+1); gsub(/[K,]/,"",u); print u; exit } }')
    max_b=$(jcmd "$pid" VM.flags 2>/dev/null | tr ' ' '\n' | sed -n 's/^-XX:MaxHeapSize=//p')
    if [ -n "$used_k" ] && [ -n "$max_b" ]; then
        p=$(( used_k * 1024 * 100 / max_b ))
        lvl=OK; [ $p -ge 80 ] && lvl=WARN; [ $p -ge 92 ] && lvl=ALERT
        emit $lvl "driver heap $(( used_k / 1048576 ))G used of $(( max_b / 1073741824 ))G max (${p}%)"
    fi
else
    emit OK "no spark-submit running"
fi

[ -n "$RUN_ID" ] || exit 0

# ── Run ──
BASE="$HOME/vdi/runs/$RUN_ID"
[ -d "$BASE" ] || { emit ALERT "run $RUN_ID: no directory $BASE"; exit 0; }
if tmux has-session -t "vdi-$RUN_ID" 2>/dev/null; then tmux_up=yes; else tmux_up=no; fi
if [ -f "$BASE/MATRIX_DONE" ]; then
    emit OK "run $RUN_ID: MATRIX COMPLETE"
elif [ -z "$pid" ]; then
    if grep -q "MATRIX FINISHED WITH" "$BASE/matrix.log" 2>/dev/null; then
        emit ALERT "run $RUN_ID: finished with failures: $(grep 'MATRIX FINISHED' "$BASE/matrix.log" | tail -1)"
    elif grep -q ABORT "$BASE/matrix.log" 2>/dev/null; then
        emit ALERT "run $RUN_ID: $(grep ABORT "$BASE/matrix.log" | tail -1)"
    else
        emit ALERT "run $RUN_ID: not complete and no spark-submit running (tmux session up: $tmux_up)"
    fi
fi

n_done=$(find "$BASE" -name DONE | wc -l | tr -d ' ')
# Failed = the latest attempt finished (run_info.txt written) without DONE. A retry
# recreates the directory, so a failure that was later retried successfully drops out.
failed_list=""
for d in "$BASE"/rep*/*; do
    [ -f "$d/run_info.txt" ] && [ ! -f "$d/DONE" ] && failed_list="$failed_list ${d#$BASE/}"
done
emit OK "run $RUN_ID: $n_done (rep, variant) runs done"
[ -n "$failed_list" ] && emit WARN "run $RUN_ID: failed, not yet retried:$failed_list"

# Current (rep, variant): newest run dir without DONE
CUR=""
for d in $(ls -td "$BASE"/rep*/* 2>/dev/null); do [ -f "$d/DONE" ] || { CUR=$d; break; }; done
if [ -n "$CUR" ] && [ -n "$pid" ]; then
    label="${CUR#$BASE/}"
    v=$(basename "$CUR")
    started_csv=$(ls "$CUR"/spark_*_queries_started.csv 2>/dev/null | head -1)
    res_csv="$CUR/spark_internal_listener_${v}_results.csv"
    n_started=0; n_res=0
    [ -f "$started_csv" ] && n_started=$(( $(wc -l < "$started_csv") - 1 ))
    [ -f "$res_csv" ] && n_res=$(( $(wc -l < "$res_csv") - 1 ))
    if [ -f "$started_csv" ]; then
        q=$(tail -1 "$started_csv")
        age=$(( now - $(stat -c %Y "$started_csv") ))
        # Stall rule: the current query has run 3x longer than its slowest completed time
        # anywhere in this run, or 3h if it has no history yet (floor 30 min).
        hist=$(cat "$BASE"/rep*/*/spark_internal_listener_*_results.csv 2>/dev/null \
            | awk -F, -v q="$q" '$1 == q && $3 > 0 && $3 > m { m = $3 } END { print int(m / 1000) }')
        if [ "${hist:-0}" -gt 0 ]; then limit=$(( 3 * hist )); [ $limit -lt 1800 ] && limit=1800; basis="3x its slowest ($(fmt_dur "$hist"))"
        else limit=10800; basis="no history, 3h"; fi
        msg="$label: query $n_started ($q) running $(fmt_dur $age); $n_res results written"
        if [ $age -gt $limit ]; then emit ALERT "$msg; STALLED? over $basis"
        else emit OK "$msg; stall limit $(fmt_dur $limit) [$basis]"; fi
    else
        emit OK "$label: starting (loading data / waiting for executors)"
    fi

    # Red flags in the current driver log
    log="$CUR/driver.log"
    if [ -f "$log" ]; then
        c() { grep -c -E "$1" "$log" 2>/dev/null || true; }
        oom=$(c 'OutOfMemoryError'); lost=$(c 'Lost executor|Executor lost|Removing executor')
        slow=$(c 'SlowDown|Status Code: 503|503 Slow'); qf=$(c 'Query failed')
        lt=$(c 'WARNING: listener did not finish')
        [ "$oom" -gt 0 ] && emit ALERT "$label: $oom OutOfMemoryError in driver.log"
        [ "$lost" -gt 0 ] && emit ALERT "$label: $lost lost/removed-executor lines in driver.log"
        [ "$slow" -gt 0 ] && emit WARN "$label: $slow S3 throttling (503 SlowDown) lines"
        [ "$qf" -gt 0 ] && emit WARN "$label: $qf 'Query failed' lines"
        [ "$lt" -gt 0 ] && emit WARN "$label: $lt listener timeouts"
    fi
fi

# Across completed runs: failed queries and listener timeouts
bad=$(cat "$BASE"/rep*/*/spark_internal_listener_*_results.csv 2>/dev/null | awk -F, '$1 != "query" && $3 < 0' | wc -l | tr -d ' ')
tos=$(cat "$BASE"/rep*/*/spark_internal_listener_*_results.csv 2>/dev/null | awk -F, '$4 == "true"' | wc -l | tr -d ' ')
[ "$bad" -gt 0 ] && emit WARN "run $RUN_ID: $bad query results are -1 (failed)"
[ "$tos" -gt 0 ] && emit WARN "run $RUN_ID: $tos rows flagged listener_timeout (rerun them and the next query)"

tail -3 "$BASE/matrix.log" 2>/dev/null | sed 's/^/INFO|/'
