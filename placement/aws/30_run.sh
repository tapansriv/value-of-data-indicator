#!/usr/bin/env bash
# Start the placement harness on a run's nodes via SSM. On each target node this starts
# node/run_node.sh as the transient systemd unit `vdi-place-run` (user ubuntu), which runs
#   cd /opt/vdi-place/s3-column-cache/run && ./run_spark_matrix.sh <args>
# and uploads run/results/spark/ to s3://$VDI_RESULTS_BUCKET/placement/<run>/<index>/.
# A systemd unit rather than tmux: it is outside the SSM agent's process tree, so neither
# the command returning nor an agent restart can kill it. Returns once all have started.
# Not billable by itself; the instances already are.
#
# Usage: aws-vault exec vdi -- ./30_run.sh <run-name> [options] <size>...
#          sweep: node i runs `./run_spark_matrix.sh <value_iter_i> <size>...`,
#                 value_iter_i = i (node 0 -> iter 0, ... as in the original 5-node split)
#        aws-vault exec vdi -- ./30_run.sh <run-name> [options] --calibrate <value_iter> <size>
#          one node (index 0 unless --only) runs `./run_spark_matrix.sh --calibrate <value_iter> <size>`
# Options:
#   --iters "a b c ..."  value_iter for node 0, 1, 2, ... instead of 0, 1, 2, ...
#   --only I             start only on node index I (e.g. to restart one failed node)
#   --no-refresh         run the harness copy baked into the AMI instead of shipping the
#                        current working tree of this repo
#   --force              start even if the node already has a DONE marker in S3
#
# Watch:  ./45_status.sh <run-name>
#         aws ssm start-session --target <id>, then: tail -f /home/ubuntu/vdi-place/run_node.log
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

[ $# -ge 2 ] || die "usage: $0 <run-name> [--iters \"..\"] [--only I] [--no-refresh] [--force] (<size>... | --calibrate <value_iter> <size>)"
RUN=$1; shift
vdi_valid_run "$RUN"
ITERS="" ONLY="" REFRESH=1 FORCE=0 CAL=0 CAL_ITER=""
SIZES=()
while [ $# -gt 0 ]; do
    case "$1" in
        --iters) ITERS=$2; shift 2 ;;
        --only) ONLY=$2; shift 2 ;;
        --no-refresh) REFRESH=0; shift ;;
        --force) FORCE=1; shift ;;
        --calibrate) CAL=1; CAL_ITER=$2; shift 2 ;;
        -*) die "unknown option $1" ;;
        *) SIZES+=("$1"); shift ;;
    esac
done
[ ${#SIZES[@]} -ge 1 ] || die "give at least one size"
for a in "${SIZES[@]}" $ITERS $CAL_ITER $ONLY; do
    [[ "$a" =~ ^[A-Za-z0-9._-]+$ ]] || die "bad argument '$a' (allowed: [A-Za-z0-9._-])"
done
if [ $CAL = 1 ]; then
    [ ${#SIZES[@]} = 1 ] || die "--calibrate takes exactly one size"
    [ -n "$ONLY" ] || ONLY=0
fi
vdi_check_account

# ── Targets: (index, instance) of running nodes ──
ROWS=()
while IFS= read -r line; do ROWS+=("$line"); done < <(vdi_place_by_index "$RUN")
[ ${#ROWS[@]} -gt 0 ] || die "run '$RUN' has no live instances"
read -r -a ITER_LIST <<< "${ITERS:-$(seq -s ' ' 0 $((${#ROWS[@]} - 1)))}"
TARGETS=()   # "idx iid matrix-args"
for row in "${ROWS[@]}"; do
    read -r idx iid st <<< "$row"
    [ -n "$ONLY" ] && [ "$idx" != "$ONLY" ] && continue
    [ "$st" = running ] || die "node $idx ($iid) is $st"
    [[ "$idx" =~ ^[0-9]+$ ]] || die "$iid has no vdi-place-index tag"
    if [ $CAL = 1 ]; then
        margs="--calibrate $CAL_ITER ${SIZES[0]}"
    else
        [ "$idx" -lt ${#ITER_LIST[@]} ] || die "no value_iter for node $idx (--iters has ${#ITER_LIST[@]})"
        margs="${ITER_LIST[$idx]} ${SIZES[*]}"
    fi
    TARGETS+=("$idx $iid $margs")
done
[ ${#TARGETS[@]} -gt 0 ] || die "no node matches --only $ONLY"
ids=(); for t in "${TARGETS[@]}"; do ids+=("$(echo "$t" | awk '{print $2}')"); done
vdi_place_guard "$RUN" "${ids[@]}"

S3RUN="$VDI_PLACE_S3/$RUN"
for t in "${TARGETS[@]}"; do
    read -r idx iid margs <<< "$t"
    if [ $FORCE = 0 ] && aws s3 ls "$S3RUN/$idx/DONE" >/dev/null 2>&1; then
        die "node $idx already has $S3RUN/$idx/DONE; pass --force to rerun it"
    fi
    vdi_ssm_online "$iid" || die "node $idx ($iid) is not registered with SSM"
done

# ── Ship the wrapper and (unless --no-refresh) the current harness tree ──
aws s3 cp "$AWS_DIR/node/run_node.sh" "$S3RUN/node/run_node.sh" --quiet
REPO_ARG=""
if [ $REFRESH = 1 ]; then
    TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT
    REPO="$(git -C "$AWS_DIR" rev-parse --show-toplevel)"
    vdi_pack_tree "$REPO" "$TMPD/s3-column-cache.tar.gz" ':!data/spark' ':!run/results' ':!aws'
    [ -f "$REPO/run/run_spark_matrix.sh" ] || die "$REPO/run/run_spark_matrix.sh does not exist yet"
    [ -x "$REPO/run/run_spark_matrix.sh" ] || die "$REPO/run/run_spark_matrix.sh is not executable (chmod +x)"
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    aws s3 cp "$TMPD/s3-column-cache.tar.gz" "$S3RUN/src/$stamp/s3-column-cache.tar.gz" --quiet
    aws s3 cp "$TMPD/s3-column-cache.tar.gz.info" "$S3RUN/src/$stamp/s3-column-cache.tar.gz.info" --quiet
    REPO_ARG="--repo-tar $S3RUN/src/$stamp/s3-column-cache.tar.gz"
    log "harness: $(sed -n 's/^commit=//p' "$TMPD/s3-column-cache.tar.gz.info") + $(sed -n 's/^uncommitted_paths=//p' "$TMPD/s3-column-cache.tar.gz.info") uncommitted paths"
fi

# ── Start ──
for t in "${TARGETS[@]}"; do
    read -r idx iid margs <<< "$t"
    # shellcheck disable=SC2086
    script="set -euo pipefail
if systemctl is-active --quiet vdi-place-run; then echo 'vdi-place-run is already active on this node' >&2; exit 3; fi
systemctl reset-failed vdi-place-run 2>/dev/null || true
aws s3 cp $S3RUN/node/run_node.sh /opt/vdi-place/run_node.sh --quiet
chown ubuntu:ubuntu /opt/vdi-place/run_node.sh
systemd-run --unit=vdi-place-run --uid=ubuntu --gid=ubuntu --setenv=HOME=/home/ubuntu \
    --property=WorkingDirectory=/home/ubuntu \
    /bin/bash /opt/vdi-place/run_node.sh --run $RUN --index $idx --bucket $VDI_RESULTS_BUCKET $REPO_ARG -- $margs
sleep 3; systemctl is-active vdi-place-run || { journalctl -u vdi-place-run --no-pager | tail -20; exit 1; }"
    if vdi_ssm_run "$iid" "$script" 120 >/dev/null; then
        log "node $idx ($iid): started ./run_spark_matrix.sh $margs"
    else
        die "node $idx ($iid): start failed (see output above); other nodes already started keep running"
    fi
done
log "results: $S3RUN/<index>/results/spark/  (synced every 10 min and at the end; DONE/FAILED markers per node)"
log "status:  ./45_status.sh $RUN"
