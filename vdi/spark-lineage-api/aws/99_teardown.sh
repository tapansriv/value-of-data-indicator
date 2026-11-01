#!/usr/bin/env bash
# Terminate a cluster's instances (or every instance tagged for this project with --all),
# then verify by listing that none remain. Teardown is judged by the listing, not by the
# exit status of the terminate call.
#
# Results are already in S3 (run_matrix.sh syncs after every variant); termination deletes
# the root volumes. AMIs, the security group, the S3 endpoint and the key pair are kept:
# none of them bills except AMI snapshot storage.
#
# Usage: aws-vault exec vdi -- ./99_teardown.sh <cluster> | --all
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

[ $# = 1 ] || die "usage: $0 <cluster> | --all"
if [ "$1" = --all ]; then CLUSTER=""; what="ALL $VDI_TAG_KEY=$VDI_TAG_VALUE instances"
else CLUSTER=$1; what="cluster '$CLUSTER'"; fi
vdi_check_account

read -r -a IDS <<< "$(vdi_instances "$CLUSTER")"
if [ ${#IDS[@]} = 0 ]; then
    log "nothing to terminate for $what"
else
    aws ec2 describe-instances --instance-ids "${IDS[@]}" \
        --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name,Tags[?Key==`Name`]|[0].Value]' \
        --output table >&2
    vdi_confirm "Terminate these ${#IDS[@]} instances ($what)?"
    aws ec2 terminate-instances --instance-ids "${IDS[@]}" >/dev/null
    aws ec2 wait instance-terminated --instance-ids "${IDS[@]}"
fi

# Verify: list everything this project still has running anywhere in the region.
left="$(vdi_instances "")"
if [ -n "$left" ]; then
    log "STILL LIVE (other clusters or builders):"
    aws ec2 describe-instances --instance-ids $left \
        --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`vdi-cluster`]|[0].Value]' \
        --output table >&2
    [ -z "$CLUSTER" ] && die "instances remain after --all teardown"
    for id in $left; do
        c="$(aws ec2 describe-instances --instance-ids "$id" \
            --query 'Reservations[0].Instances[0].Tags[?Key==`vdi-cluster`]|[0].Value' --output text)"
        [ "$c" = "$CLUSTER" ] && die "$id from '$CLUSTER' is still live"
    done
fi
[ -n "$CLUSTER" ] && rm -f "$(vdi_ssh_config "$CLUSTER")"
log "teardown of $what verified: no live instances"
