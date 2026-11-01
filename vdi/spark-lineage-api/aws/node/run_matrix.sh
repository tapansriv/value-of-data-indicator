#!/usr/bin/env bash
# The experiment harness. Runs ON THE DRIVER NODE, inside tmux (30_run.sh starts it).
#
# One spark-submit per (rep, variant). Each submit runs every query in --queries once, in
# sorted order, one at a time (the listeners enforce that). Timing comes from the
# listener's own results CSV (user-observed query latency), not from wall-clocking
# spark-submit, which would add JVM start and executor acquisition.
#
# Variant order alternates between reps (forward on odd reps, reversed on even), so slow
# drift over a multi-day run (S3 performance, time of day) doesn't line up with a variant.
#
# Resumable: a (rep, variant) with a DONE marker is skipped, so rerunning the same command
# after a crash continues where it stopped.
#
# Usage: run_matrix.sh --run-id ID --workers N --queries DIR [--reps 2]
#          [--variants "vanilla bare cols rowgroup"] [--local] [--driver-memory 16g] [--rep-only K]
# --rep-only K runs just rep K (in rep K's order: forward if odd, reversed if even), so one
# size's reps can run on separate clusters in parallel.
set -euo pipefail

RUN_ID="" WORKERS="" QUERIES="" REPS=2 VARIANTS="vanilla bare cols rowgroup" LOCAL=0 REP_ONLY=""
DRIVER_MEM=16g
EXEC_CORES=7 EXEC_MEM=48g          # REVISION_SCALEUP.md A5: identical at every cluster size
DATA="${VDI_DATA:-s3a://vod-tpch-1tb/}"
BUCKET="${VDI_BUCKET:?VDI_BUCKET must be set}"
while [ $# -gt 0 ]; do
    case "$1" in
        --run-id) RUN_ID=$2; shift 2 ;;
        --workers) WORKERS=$2; shift 2 ;;
        --queries) QUERIES=$2; shift 2 ;;
        --reps) REPS=$2; shift 2 ;;
        --variants) VARIANTS=$2; shift 2 ;;
        --local) LOCAL=1; shift ;;
        --driver-memory) DRIVER_MEM=$2; shift 2 ;;
        --rep-only) REP_ONLY=$2; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done
[ -n "$RUN_ID" ] && [ -n "$QUERIES" ] || { echo "--run-id and --queries are required" >&2; exit 2; }
[ "$LOCAL" = 1 ] || [ -n "$WORKERS" ] || { echo "--workers is required unless --local" >&2; exit 2; }
[ -d "$QUERIES" ] || { echo "no query dir $QUERIES" >&2; exit 2; }

SPARK_HOME="${SPARK_HOME:-/opt/spark}"   # overridable only for testing the harness
VDI_HOME="${VDI_HOME:-/opt/vdi}"
SPARK="$SPARK_HOME/bin/spark-submit"
JARS="$VDI_HOME/jars"
BASE="$HOME/vdi/runs/$RUN_ID"
S3="s3://$BUCKET/runs/$RUN_ID"
mkdir -p "$BASE"
log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$BASE/matrix.log"; }
sync_up() { aws s3 sync "$BASE" "$S3" --quiet || log "WARNING: s3 sync failed (will retry next sync)"; }

imds() {
    local t; t="$(curl -fsS -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')"
    curl -fsS -H "X-aws-ec2-metadata-token: $t" "http://169.254.169.254/latest/meta-data/$1"
}

if [ "$LOCAL" = 1 ]; then
    MASTER='local[*]'
    # In local mode the driver JVM is also the only executor.
    DRIVER_MEM="${DRIVER_MEM_LOCAL:-48g}"
    RES_ARGS=()
else
    MY_IP="$(imds local-ipv4)"
    MASTER="spark://$MY_IP:7077"
    # The master UI binds to SPARK_LOCAL_IP (the private IP), not localhost.
    alive_workers() { curl -fs --max-time 10 "http://$MY_IP:8080/json/" | jq -r .aliveworkers 2>/dev/null || echo unreachable; }
    alive="$(alive_workers)"
    if [ "$alive" != "$WORKERS" ]; then
        log "ABORT: master reports $alive alive workers, expected $WORKERS"; exit 1
    fi
    RES_ARGS=(--executor-cores "$EXEC_CORES" --executor-memory "$EXEC_MEM"
              --total-executor-cores $((EXEC_CORES * WORKERS))
              # Start the first query only once every executor has registered.
              --conf spark.scheduler.minRegisteredResourcesRatio=1.0
              --conf spark.scheduler.maxRegisteredResourcesWaitingTime=300s)
fi

COMMON_ARGS=(--master "$MASTER" --deploy-mode client --class LineageAPI
    --driver-memory "$DRIVER_MEM"
    ${RES_ARGS[@]+"${RES_ARGS[@]}"}
    --conf spark.speculation=false                      # A6: speculative tasks double-count row groups
    --conf spark.sql.adaptive.enabled=false             # as in the paper's existing Spark runs
    --conf spark.sql.exchange.reuse=false
    --conf spark.sql.execution.reuseSubquery=false
    --conf spark.eventLog.enabled=true
    --conf spark.eventLog.logStageExecutorMetrics=true) # driver/executor peak heap, for §1.1

N_QUERIES=$(ls "$QUERIES"/*.sql | wc -l | tr -d ' ')

# ── Metadata, once per run id ──
META="$BASE/run_metadata.txt"
if [ ! -f "$META" ]; then
    {
        echo "run_id=$RUN_ID"
        echo "started_utc=$(date -u +%FT%TZ)"
        echo "cluster=${VDI_CLUSTER:-unknown}"
        echo "mode=$([ "$LOCAL" = 1 ] && echo local || echo standalone)"
        echo "workers=${WORKERS:-0}"
        echo "instance_type=$(imds instance-type)"
        echo "ami_id=$(imds ami-id)"
        echo "availability_zone=$(imds placement/availability-zone)"
        echo "data=$DATA"
        echo "reps=$REPS${REP_ONLY:+ (this run: rep $REP_ONLY only)}"
        echo "variants=$VARIANTS"
        echo "seed=n/a (no randomized component: fixed queries, fixed order)"
        echo "spark_submit_args=${COMMON_ARGS[*]}"
        echo "--- BUILD_INFO"; cat "$VDI_HOME/BUILD_INFO"
        echo "--- spark-defaults.conf"; cat "$SPARK_HOME/conf/spark-defaults.conf"
        echo "--- queries (sha256)"; (cd "$QUERIES" && sha256sum ./*.sql)
    } > "$META"
fi
sync_up

# ── The matrix ──
read -r -a FWD <<< "$VARIANTS"
n_failed=0
REP_LIST=$(seq 1 "$REPS"); [ -n "$REP_ONLY" ] && REP_LIST=$REP_ONLY
for rep in $REP_LIST; do
    if [ $((rep % 2)) = 1 ]; then ORDER=("${FWD[@]}")
    else ORDER=(); for ((i=${#FWD[@]}-1; i>=0; i--)); do ORDER+=("${FWD[$i]}"); done
    fi
    log "rep $rep order: ${ORDER[*]}"
    for v in "${ORDER[@]}"; do
        RUN="$BASE/rep$rep/$v"
        if [ -f "$RUN/DONE" ]; then log "skip rep$rep/$v (DONE)"; continue; fi
        # A lost worker would silently shrink the cluster for every later submit (they would
        # wait maxRegisteredResourcesWaitingTime, then run on fewer executors). Stop instead.
        if [ "$LOCAL" = 0 ]; then
            alive="$(alive_workers)"
            if [ "$alive" != "$WORKERS" ]; then
                log "ABORT before rep$rep/$v: master reports $alive alive workers, expected $WORKERS"
                sync_up; exit 1
            fi
        fi
        # Retry of a failed attempt: clear its S3 output too. s3 sync never deletes, and the
        # usage logs are written in append mode, so old and new rows would otherwise mix.
        if [ -d "$RUN" ]; then
            log "clearing previous attempt of rep$rep/$v"
            aws s3 rm --recursive --quiet "$S3/rep$rep/$v/" || true
            aws s3 rm --recursive --quiet "$S3/usage_logs/rep$rep/$v/" || true
        fi
        rm -rf "$RUN"; mkdir -p "$RUN/eventlog"
        log "start rep$rep/$v"
        start=$(date -u +%FT%TZ)
        set +e
        (cd "$RUN" && "$SPARK" "${COMMON_ARGS[@]}" \
            --conf "spark.eventLog.dir=file://$RUN/eventlog" \
            "$JARS/$v.jar" \
            parquet "$DATA" "$QUERIES" "s3a://$BUCKET/runs/$RUN_ID/usage_logs/rep$rep/$v" my_catalog \
            > "$RUN/driver.log" 2>&1)
        rc=$?
        set -e
        {
            echo "variant=$v"; echo "rep=$rep"; echo "exit_code=$rc"
            echo "start_utc=$start"; echo "end_utc=$(date -u +%FT%TZ)"
        } > "$RUN/run_info.txt"
        # A crashed submit may leave no CSV; that must not stop the rest of the matrix.
        csv="$RUN/spark_internal_listener_${v}_results.csv"
        ok=0 fail=0 to=0
        if [ -f "$csv" ]; then
            read -r ok fail to < <(awk -F, 'NR>1 { if ($3 >= 0) ok++; else fail++; if ($4 == "true") to++ }
                END { printf "%d %d %d\n", ok, fail, to }' "$csv")
        fi
        log "end rep$rep/$v exit=$rc ok=$ok/$N_QUERIES failed=$fail listener_timeouts=$to"
        # DONE only for a complete, clean pass. The listeners catch query exceptions and exit
        # 0, so the exit code alone would accept a pass where every query failed. No DONE
        # means rerunning the same command retries this (rep, variant).
        if [ "$rc" = 0 ] && [ "$ok" = "$N_QUERIES" ] && [ "$fail" = 0 ] && [ "$to" = 0 ]; then
            touch "$RUN/DONE"
        else
            n_failed=$((n_failed + 1))
            log "FAILED rep$rep/$v (exit=$rc ok=$ok/$N_QUERIES failed=$fail timeouts=$to); continuing, see $RUN/driver.log"
        fi
        sync_up
    done
done
if [ "$n_failed" = 0 ]; then
    log "MATRIX COMPLETE"
    touch "$BASE/MATRIX_DONE"
else
    log "MATRIX FINISHED WITH $n_failed FAILED (rep, variant) runs; rerun the same command to retry them"
fi
sync_up
[ "$n_failed" = 0 ]
