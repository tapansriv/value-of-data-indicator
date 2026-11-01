#!/usr/bin/env bash
# One-time network setup for the placement nodes. Idempotent; creates nothing that bills.
#
#   - security group $VDI_PLACE_SG_NAME (vdi-place-node), tagged project=vdi-placement:
#     NO inbound rules at all (each node is standalone; shell access is SSM, which is
#     outbound-only), outbound = all (S3, SSM, package mirrors). Deliberately not
#     spark-scale's vdi-spark-cluster group, whose self-referencing rule would let
#     placement nodes reach spark-scale's Spark ports.
#   - checks (does not create) what spark-scale's 00_network.sh already set up and this
#     experiment shares: the S3 gateway endpoint, the key pair, the default subnet.
#
# Usage: aws-vault exec vdi -- ./00_network.sh
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"
vdi_check_account

SG_ID="$(vdi_sg_id)"
if [ -z "$SG_ID" ]; then
    SG_ID="$(aws ec2 create-security-group --group-name "$VDI_PLACE_SG_NAME" \
        --description "VDI placement: standalone nodes, no inbound" \
        --vpc-id "$VDI_VPC_ID" \
        --tag-specifications "$(vdi_tagspec security-group Name=$VDI_PLACE_SG_NAME)" \
        --query GroupId --output text)"
    log "created security group $SG_ID"
else
    log "security group exists: $SG_ID"
fi
n_in="$(aws ec2 describe-security-groups --group-ids "$SG_ID" \
    --query 'length(SecurityGroups[0].IpPermissions)' --output text)"
[ "$n_in" = 0 ] || die "$SG_ID has $n_in inbound rules; it must have none. Inspect it."

EP_ID="$(aws ec2 describe-vpc-endpoints \
    --filters "Name=vpc-id,Values=$VDI_VPC_ID" "Name=service-name,Values=com.amazonaws.$VDI_AWS_REGION.s3" \
              "Name=vpc-endpoint-type,Values=Gateway" \
    --query 'VpcEndpoints[0].VpcEndpointId' --output text | grep -v '^None$' || true)"
[ -n "$EP_ID" ] || die "no S3 gateway endpoint in the default VPC; run spark-scale's 00_network.sh (it owns that endpoint)"
log "S3 gateway endpoint: $EP_ID"

aws ec2 describe-key-pairs --key-names "$VDI_KEY_PAIR_NAME" >/dev/null 2>&1 \
    || die "key pair $VDI_KEY_PAIR_NAME missing; run spark-scale's 00_network.sh"
log "key pair: $VDI_KEY_PAIR_NAME"

SUBNET="$(vdi_subnet_id)"
[ -n "$SUBNET" ] || die "no default subnet in $VDI_AZ"
log "subnet: $SUBNET ($VDI_AZ)"
log "network ready"
