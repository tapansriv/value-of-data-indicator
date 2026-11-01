#!/bin/bash
# Runs ON A PLACEMENT NODE as user ubuntu, as the transient systemd unit vdi-place-run
# (30_run.sh starts it via SSM). Wraps the harness's run/run_spark_matrix.sh:
#
#   1. optionally refreshes /opt/vdi-place/s3-column-cache from a tarball in S3 (extracted
#      over the top, so an existing run/results/ survives a restart);
#   2. runs `cd .../run && ./run_spark_matrix.sh <args...>`;
#   3. syncs run/results/spark/ to s3://<bucket>/placement/<run>/<index>/results/spark/
#      every $VDI_PLACE_SYNC_MIN minutes (default 10), whenever the harness calls
#      $VDI_PLACE_SYNC (e.g. after each config), and at the end;
#   4. writes <index>/DONE (exit 0) or <index>/FAILED (non-zero) in S3.
#
# Every sync also writes <index>/HEARTBEAT ("<epoch> <root-disk-%> <state>"), which
# 45_status.sh reads, and uploads this wrapper's log as <index>/run_node.log.
#
# Usage: run_node.sh --run R --index I --bucket B [--repo-tar s3://...] -- <matrix args...>
set -uo pipefail

RUN="" IDX="" BUCKET="" REPO_TAR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --run) RUN=$2; shift 2 ;;
        --index) IDX=$2; shift 2 ;;
        --bucket) BUCKET=$2; shift 2 ;;
        --repo-tar) REPO_TAR=$2; shift 2 ;;
        --) shift; break ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done
[ -n "$RUN" ] && [ -n "$IDX" ] && [ -n "$BUCKET" ] || { echo "--run, --index, --bucket are required" >&2; exit 2; }

# shellcheck disable=SC1091
. /etc/profile.d/vdi-place.sh
PLACE=/opt/vdi-place
REPO=$PLACE/s3-column-cache
RESULTS=$REPO/run/results/spark
DEST="s3://$BUCKET/placement/$RUN/$IDX"
WORK=/home/ubuntu/vdi-place
LOG=$WORK/run_node.log
mkdir -p "$WORK"
log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG"; }

# The sync helper is a file so the harness can call it too: "$VDI_PLACE_SYNC".
SYNC=$PLACE/sync_results.sh
cat > "$SYNC" <<EOF
#!/bin/bash
# Upload placement results for run $RUN, node $IDX. Safe to call any time, concurrently.
state=\${1:-running}
exec 9>$WORK/.sync.lock; flock 9
mkdir -p $RESULTS
aws s3 sync $RESULTS $DEST/results/spark --quiet --no-progress || echo "WARNING: s3 sync failed (retried next sync)" >&2
aws s3 cp $LOG $DEST/run_node.log --quiet || true
echo "\$(date +%s) \$(df --output=pcent / | tail -1 | tr -dc 0-9) \$state" | aws s3 cp - $DEST/HEARTBEAT --quiet || true
EOF
chmod +x "$SYNC"
export VDI_PLACE_SYNC=$SYNC VDI_PLACE_RUN=$RUN VDI_PLACE_INDEX=$IDX

log "run_node start: run=$RUN index=$IDX args: $*"
aws s3 rm "$DEST/FAILED" --quiet 2>/dev/null || true
aws s3 rm "$DEST/DONE" --quiet 2>/dev/null || true

if [ -n "$REPO_TAR" ]; then
    log "refreshing $REPO from $REPO_TAR"
    mkdir -p "$REPO"
    if ! aws s3 cp "$REPO_TAR" - --quiet | tar xz -C "$REPO"; then
        log "ABORT: could not fetch/extract $REPO_TAR"
        echo "exit=97 repo refresh failed $(date -u +%FT%TZ)" | aws s3 cp - "$DEST/FAILED" --quiet
        "$SYNC" failed; exit 97
    fi
    aws s3 cp "$REPO_TAR.info" "$REPO/REPO_INFO" --quiet || true
fi

# Run metadata, once per start (numbered so restarts keep earlier ones)
imds() {
    local t; t="$(curl -fsS -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')"
    curl -fsS -H "X-aws-ec2-metadata-token: $t" "http://169.254.169.254/latest/meta-data/$1"
}
META="$WORK/node_info.$(date -u +%Y%m%dT%H%M%SZ).txt"
{
    echo "run=$RUN"; echo "index=$IDX"; echo "started_utc=$(date -u +%FT%TZ)"
    echo "matrix_args=$*"
    echo "instance_id=$(imds instance-id)"; echo "instance_type=$(imds instance-type)"
    echo "ami_id=$(imds ami-id)"; echo "availability_zone=$(imds placement/availability-zone)"
    echo "nproc=$(nproc)"; echo "mem=$(free -g | awk '/^Mem:/ {print $2}')G"
    echo "root_disk=$(df -h --output=size,avail / | tail -1)"
    echo "--- BUILD_INFO"; cat "$PLACE/BUILD_INFO" 2>/dev/null
    echo "--- REPO_INFO (harness actually run)"; cat "$REPO/REPO_INFO" 2>/dev/null
} > "$META"
aws s3 cp "$META" "$DEST/$(basename "$META")" --quiet || true
"$SYNC" starting

# Periodic sync while the harness runs
SYNC_MIN="${VDI_PLACE_SYNC_MIN:-10}"
( while sleep $((SYNC_MIN * 60)); do "$SYNC" running; done ) &
SYNC_PID=$!

cd "$REPO/run" || { log "ABORT: no $REPO/run"; rc=98; }
if [ "${rc:-0}" = 0 ]; then
    if [ ! -x ./run_spark_matrix.sh ]; then
        log "ABORT: $REPO/run/run_spark_matrix.sh missing or not executable"; rc=98
    else
        log "start ./run_spark_matrix.sh $*"
        ./run_spark_matrix.sh "$@" 2>&1 | tee -a "$LOG"
        rc=${PIPESTATUS[0]}
        log "run_spark_matrix.sh exit=$rc"
    fi
fi

kill "$SYNC_PID" 2>/dev/null; wait "$SYNC_PID" 2>/dev/null
cd /
if [ "$rc" = 0 ]; then
    "$SYNC" done
    echo "exit=0 $(date -u +%FT%TZ)" | aws s3 cp - "$DEST/DONE" --quiet
    log "DONE"
else
    "$SYNC" failed
    echo "exit=$rc $(date -u +%FT%TZ)" | aws s3 cp - "$DEST/FAILED" --quiet
    log "FAILED (exit $rc)"
fi
aws s3 cp "$LOG" "$DEST/run_node.log" --quiet || true
exit "$rc"
