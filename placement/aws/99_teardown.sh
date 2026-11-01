#!/usr/bin/env bash
# Terminate a placement run's instances (or every placement instance with --all), then
# verify by listing that none remain. Teardown is judged by the listing, not by the exit
# status of the terminate call.
#
# Isolation (lib.sh, "Isolation"): instances are selected ONLY by
#   tag:project=vdi-placement AND tag:vdi-exp=placement [AND tag:vdi-place-run=<run>],
# then vdi_place_guard re-reads every selected instance's tags and refuses the whole
# teardown if any one lacks those tags, lacks the vdi-place- Name prefix, carries
# spark-scale's vdi-cluster tag, or belongs to another run. spark-scale's instances
# (project=vdi-spark-scale) cannot be selected here, and --all means all PLACEMENT
# instances, never the account's.
#
# Results are already in S3 (run_node.sh syncs periodically and at the end); termination
# deletes the root volumes. AMIs and the security group are kept.
#
# Usage: aws-vault exec vdi -- ./99_teardown.sh <run-name> [--only I] | --all
#   --only I  terminate only node index I of the run (e.g. once its DONE results are fetched)
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

ONLY=""
if [ $# = 3 ] && [ "$2" = --only ]; then ONLY=$3; [[ "$ONLY" =~ ^[0-9]+$ ]] || die "bad index $ONLY"; set -- "$1"; fi
[ $# = 1 ] || die "usage: $0 <run-name> [--only I] | --all"
if [ "$1" = --all ]; then RUN=""; what="ALL placement instances (project=$VDI_PLACE_TAG_VALUE)"
else RUN=$1; vdi_valid_run "$RUN"; what="placement run '$RUN'"; fi
vdi_check_account

IDS=()
if [ -n "$ONLY" ]; then
    [ -n "$RUN" ] || die "--only needs a run name"
    what="node $ONLY of placement run '$RUN'"
    read -r -a IDS <<< "$(vdi_place_by_index "$RUN" | awk -v i="$ONLY" '$1 == i {print $2}')"
else
    read -r -a IDS <<< "$(vdi_place_instances "$RUN")"
fi
if [ ${#IDS[@]} = 0 ]; then
    log "nothing to terminate for $what"
else
    vdi_place_guard "$RUN" "${IDS[@]}"
    aws ec2 describe-instances --instance-ids "${IDS[@]}" \
        --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name,Tags[?Key==`Name`]|[0].Value,Tags[?Key==`project`]|[0].Value]' \
        --output table >&2
    if [ -n "$RUN" ]; then
        if [ -n "$ONLY" ]; then idxs=$ONLY
        else idxs=$(aws s3 ls "$VDI_PLACE_S3/$RUN/" 2>/dev/null | awk '$1 == "PRE" {print $2}' | tr -d / | grep -E '^[0-9]+$' || true); fi
        for i in $idxs; do
            aws s3 ls "$VDI_PLACE_S3/$RUN/$i/DONE" >/dev/null 2>&1 || log "note: node $i has no DONE marker (run still going, or failed)"
        done
    fi
    vdi_confirm "Terminate these ${#IDS[@]} instances ($what)?"
    aws ec2 terminate-instances --instance-ids "${IDS[@]}" >/dev/null
    aws ec2 wait instance-terminated --instance-ids "${IDS[@]}"
fi

# Verify
if [ -n "$ONLY" ]; then
    left="$(vdi_place_by_index "$RUN" | awk -v i="$ONLY" '$1 == i && $3 != "terminated" && $3 != "shutting-down" {print $2}')"
else
    left="$(vdi_place_instances "$RUN")"
fi
[ -z "$left" ] || die "still live after teardown of $what: $left"
others="$(vdi_place_instances "" | tr '\t' ' ')"
[ -z "$others" ] || log "other placement instances still live (not part of $what): $others"
log "teardown of $what verified: no live instances"
