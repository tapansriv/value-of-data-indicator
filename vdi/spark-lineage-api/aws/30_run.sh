#!/usr/bin/env bash
# Start run_matrix.sh on a cluster's driver node inside tmux, so the run survives any
# disconnect, including this session ending (TMUX.md). Returns as soon as it has started.
# Not billable by itself; the cluster already is.
#
# Usage: aws-vault exec vdi -- ./30_run.sh <cluster> <run-id> [--queries-local DIR] [run_matrix args...]
#   e.g. ./30_run.sh n4 n4-main --reps 2
#        ./30_run.sh val e-local --queries-local /path/to/q_subset --local --variants rowgroup --reps 1
# --workers is filled in from the cluster's intended size (the vdi-workers tag set at
# launch) unless --local is given, so a cluster that has already lost a worker fails the
# harness's alive-worker check instead of passing it.
#
# Watch:  ssh -F ~/.config/vdi-spark/ssh/<cluster>.conf -t driver tmux -CC attach -t vdi-<run-id>
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

[ $# -ge 2 ] || die "usage: $0 <cluster> <run-id> [--queries-local DIR] [run_matrix args...]"
CLUSTER=$1 RUN_ID=$2; shift 2
[[ "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]] || die "run-id must be [A-Za-z0-9._-]"
QLOCAL="$AWS_DIR/../benchmarking/tpch22"
if [ "${1:-}" = --queries-local ]; then QLOCAL=$2; shift 2; fi
[ -d "$QLOCAL" ] || die "no query dir $QLOCAL"
EXTRA=("$@")
vdi_check_account

CONF="$(vdi_ssh_config "$CLUSTER")"
[ -f "$CONF" ] || die "no ssh config for '$CLUSTER'; was it launched with 20_launch.sh?"
[ -n "$(vdi_instances "$CLUSTER")" ] || die "cluster '$CLUSTER' has no live instances"

is_local=0
for a in "${EXTRA[@]+"${EXTRA[@]}"}"; do [ "$a" = --local ] && is_local=1; done
if [ $is_local = 0 ]; then
    n="$(aws ec2 describe-instances --filters "Name=tag:vdi-cluster,Values=$CLUSTER" \
        "Name=tag:vdi-role,Values=driver" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].Tags[?Key==`vdi-workers`]|[0].Value' --output text)"
    [[ "$n" =~ ^[0-9]+$ ]] || die "driver of '$CLUSTER' has no vdi-workers tag"
    EXTRA+=(--workers "$n")
fi

SESSION="vdi-$RUN_ID"
if ssh -F "$CONF" driver "tmux has-session -t $SESSION" 2>/dev/null; then
    die "tmux session $SESSION is already running on $CLUSTER's driver"
fi

QNAME="$(basename "$QLOCAL")"
ssh -F "$CONF" driver "mkdir -p ~/vdi/queries/$QNAME"
scp -F "$CONF" -q "$AWS_DIR/node/run_matrix.sh" driver:vdi/run_matrix.sh
scp -F "$CONF" -q "$QLOCAL"/*.sql "driver:vdi/queries/$QNAME/"

cmd="VDI_BUCKET=$(printf %q "$VDI_RESULTS_BUCKET") VDI_CLUSTER=$(printf %q "$CLUSTER") bash ~/vdi/run_matrix.sh --run-id $(printf %q "$RUN_ID") --queries ~/vdi/queries/$(printf %q "$QNAME")"
for a in "${EXTRA[@]+"${EXTRA[@]}"}"; do cmd="$cmd $(printf %q "$a")"; done
# The shell stays open after the harness exits, so its last output can be inspected.
ssh -F "$CONF" driver "tmux new-session -d -s $SESSION $(printf %q "$cmd; exec bash")"

log "started $SESSION on $CLUSTER: $cmd"
log "attach:  ssh -F $CONF -t driver tmux -CC attach -t $SESSION"
log "results: s3://$VDI_RESULTS_BUCKET/runs/$RUN_ID/  (synced after every variant)"
