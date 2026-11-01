#!/usr/bin/env bash
# One-time network setup in the default VPC. Idempotent; creates nothing that bills.
#
#   - security group $VDI_SG_NAME: inbound = all traffic from itself only (no port is open
#     to the internet; SSH arrives through SSM), outbound = all (builds, SSM, S3)
#   - S3 gateway endpoint on the default VPC's main route table (free; keeps S3 traffic
#     on AWS's network)
#   - key pair $VDI_KEY_PAIR_NAME, imported from $VDI_SSH_KEY.pub
#
# Usage: aws-vault exec vdi -- ./00_network.sh
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"
vdi_check_account

# Security group
SG_ID="$(vdi_sg_id)"
if [ -z "$SG_ID" ]; then
    SG_ID="$(aws ec2 create-security-group --group-name "$VDI_SG_NAME" \
        --description "VDI Spark scale-up: intra-cluster traffic only" \
        --vpc-id "$VDI_VPC_ID" \
        --tag-specifications "$(vdi_tagspec security-group Name=$VDI_SG_NAME)" \
        --query GroupId --output text)"
    log "created security group $SG_ID"
else
    log "security group exists: $SG_ID"
fi
perms="$(aws ec2 describe-security-groups --group-ids "$SG_ID" --query 'SecurityGroups[0].IpPermissions' --output json)"
self_rule="$(echo "$perms" | jq --arg sg "$SG_ID" \
    '[.[] | select(.IpProtocol == "-1") | .UserIdGroupPairs[] | select(.GroupId == $sg)] | length')"
if [ "$self_rule" = 0 ]; then
    aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
        --ip-permissions "IpProtocol=-1,UserIdGroupPairs=[{GroupId=$SG_ID}]" >/dev/null
    log "added self-referencing inbound rule"
fi
open_rules="$(echo "$perms" | jq '[.[] | (.IpRanges + .Ipv6Ranges + .PrefixListIds)[]] | length')"
[ "$open_rules" = 0 ] || die "$SG_ID has CIDR/prefix-list inbound rules; it must allow only itself. Inspect it."

# S3 gateway endpoint
EP_ID="$(aws ec2 describe-vpc-endpoints \
    --filters "Name=vpc-id,Values=$VDI_VPC_ID" "Name=service-name,Values=com.amazonaws.$VDI_AWS_REGION.s3" \
              "Name=vpc-endpoint-type,Values=Gateway" \
    --query 'VpcEndpoints[0].VpcEndpointId' --output text | grep -v '^None$' || true)"
if [ -z "$EP_ID" ]; then
    RT_ID="$(aws ec2 describe-route-tables \
        --filters "Name=vpc-id,Values=$VDI_VPC_ID" "Name=association.main,Values=true" \
        --query 'RouteTables[0].RouteTableId' --output text)"
    EP_ID="$(aws ec2 create-vpc-endpoint --vpc-id "$VDI_VPC_ID" --vpc-endpoint-type Gateway \
        --service-name "com.amazonaws.$VDI_AWS_REGION.s3" --route-table-ids "$RT_ID" \
        --tag-specifications "$(vdi_tagspec vpc-endpoint)" \
        --query 'VpcEndpoint.VpcEndpointId' --output text)"
    log "created S3 gateway endpoint $EP_ID on $RT_ID"
else
    log "S3 gateway endpoint exists: $EP_ID"
fi

# Key pair
[ -r "$VDI_SSH_KEY.pub" ] || die "$VDI_SSH_KEY.pub not found. Create it with: ssh-keygen -t ed25519 -f $VDI_SSH_KEY"
if aws ec2 describe-key-pairs --key-names "$VDI_KEY_PAIR_NAME" >/dev/null 2>&1; then
    log "key pair exists: $VDI_KEY_PAIR_NAME"
else
    aws ec2 import-key-pair --key-name "$VDI_KEY_PAIR_NAME" \
        --public-key-material "fileb://$VDI_SSH_KEY.pub" \
        --tag-specifications "$(vdi_tagspec key-pair)" >/dev/null
    log "imported key pair $VDI_KEY_PAIR_NAME"
fi

SUBNET="$(vdi_subnet_id)"
[ -n "$SUBNET" ] || die "no default subnet in $VDI_AZ"
log "cluster subnet: $SUBNET ($VDI_AZ)"
log "network ready"
