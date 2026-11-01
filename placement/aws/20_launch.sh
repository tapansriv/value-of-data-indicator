#!/usr/bin/env bash
# Launch <count> independent single-node placement instances for one run, from the AMI
# built by 10_build_ami.sh, in one AZ. No master/worker: each node runs Spark in local
# mode on its own. Instance i (0-based, tag vdi-place-index) later gets value_iter i.
# BILLABLE: <count> instances until 99_teardown.sh, or until each node's dead-man's switch
# terminates it after <max-hours>.
#
# Usage: aws-vault exec vdi -- ./20_launch.sh <run-name> <count> <max-hours>
#   e.g. ./20_launch.sh cal1 1 2        (calibration)
#        ./20_launch.sh sweep1 5 24     (the sweep)
# Env overrides: VDI_AMI (default: newest placement AMI), VDI_TYPE (default m7g.2xlarge),
#   VDI_ROOT_GB (100), VDI_ROOT_IOPS (6000), VDI_ROOT_TPUT (300 MB/s), VDI_YES=1
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

[ $# = 3 ] || die "usage: $0 <run-name> <count> <max-hours>"
RUN=$1 COUNT=$2 MAX_HOURS=$3
vdi_valid_run "$RUN"
case "$RUN" in builder-*) die "run names starting with builder- are reserved for 10_build_ami.sh" ;; esac
[[ "$COUNT" =~ ^[0-9]+$ && "$COUNT" -ge 1 && "$COUNT" -le 16 ]] || die "count must be 1..16"
[[ "$MAX_HOURS" =~ ^[0-9]+$ && "$MAX_HOURS" -ge 1 ]] || die "max-hours must be a whole number >= 1"
vdi_check_account

TYPE="${VDI_TYPE:-$VDI_PLACE_DEFAULT_TYPE}"
ROOT_GB="${VDI_ROOT_GB:-100}"  # >= the AMI snapshot (builder root is 100 GB)
IOPS="${VDI_ROOT_IOPS:-6000}"
TPUT="${VDI_ROOT_TPUT:-300}"
AMI="${VDI_AMI:-$(vdi_latest_place_ami)}"
[ -n "$AMI" ] || die "no placement AMI; run 10_build_ami.sh"
# Never launch from a non-placement image (e.g. spark-scale's spark-rg AMI) by mistake.
ami_tag="$(aws ec2 describe-images --image-ids "$AMI" \
    --query "Images[0].Tags[?Key=='vdi-image']|[0].Value" --output text)"
[ "$ami_tag" = placement ] || die "$AMI is not a placement AMI (vdi-image=$ami_tag)"
SG_ID="$(vdi_sg_id)";      [ -n "$SG_ID" ]  || die "no security group; run 00_network.sh"
SUBNET="$(vdi_subnet_id)"; [ -n "$SUBNET" ] || die "no default subnet in $VDI_AZ"
[ -z "$(vdi_place_instances "$RUN")" ] || die "run '$RUN' already has live instances"
ROOT_DEV="$(aws ec2 describe-images --image-ids "$AMI" --query 'Images[0].RootDeviceName' --output text)"

price="$(vdi_price "$TYPE")"
cost=""
# gp3 extras: $0.08/GB-mo, $0.005/IOPS-mo over 3000, $0.04/MBps-mo over 125 (730 h/mo)
ebs_hr="$(python3 -c "print(($ROOT_GB*0.08 + max($IOPS-3000,0)*0.005 + max($TPUT-125,0)*0.04)/730)")"
[ -n "$price" ] && cost="$(python3 -c "
p=$price+$ebs_hr; n=$COUNT
print(f'\${n*p:.2f}/hr for {n} x ($TYPE \$$price + EBS \${$ebs_hr:.3f}); at most \${n*p*$MAX_HOURS:.2f} if left to the dead-man')")"
vdi_confirm "Launch placement run '$RUN': $COUNT x $TYPE (standalone), $AMI, ${ROOT_GB} GB gp3 (${IOPS} IOPS, ${TPUT} MB/s) each, $VDI_AZ.
  ${cost:-no price on file for $TYPE}
  vCPUs: $((COUNT * VDI_PLACE_VCPU)) of the account's shared Standard quota (spark-scale uses the same quota).
  Every node terminates itself after ${MAX_HOURS}h."

# gp3 above baseline: the local cache tier lives on this volume; default gp3 (125 MB/s)
# would make 'local' barely faster than S3. 300 MB/s ~ m7g.2xlarge's baseline EBS bandwidth.
BDM="DeviceName=$ROOT_DEV,Ebs={VolumeSize=$ROOT_GB,VolumeType=gp3,Iops=$IOPS,Throughput=$TPUT,DeleteOnTermination=true}"

UD="$(mktemp)"
{
    echo "#!/bin/bash"
    echo "export VDI_PLACE_RUN=$RUN VDI_MAX_MIN=$((MAX_HOURS * 60))"
    tail -n +2 "$AWS_DIR/node/boot.sh"
} > "$UD"

LAUNCHED=""
cleanup_partial() {
    [ -n "$LAUNCHED" ] || return 0
    log "launch failed: terminating$LAUNCHED"
    # shellcheck disable=SC2086
    aws ec2 terminate-instances --instance-ids $LAUNCHED >/dev/null || true
}
trap 'rc=$?; rm -f "$UD"; [ "$rc" = 0 ] || cleanup_partial' EXIT
trap 'exit 130' INT TERM

# --count N means min = max = N: all or nothing on capacity.
read -r -a IDS <<< "$(aws ec2 run-instances --image-id "$AMI" --instance-type "$TYPE" --count "$COUNT" \
    --subnet-id "$SUBNET" --security-group-ids "$SG_ID" --key-name "$VDI_KEY_PAIR_NAME" \
    --iam-instance-profile "Name=$VDI_INSTANCE_PROFILE" \
    --metadata-options HttpTokens=required,HttpPutResponseHopLimit=1 \
    --instance-initiated-shutdown-behavior terminate \
    --block-device-mappings "$BDM" \
    --user-data "file://$UD" \
    --tag-specifications \
        "$(vdi_tagspec instance Name=${VDI_PLACE_NAME_PREFIX}$RUN vdi-place-run=$RUN vdi-place-role=node vdi-max-hours=$MAX_HOURS vdi-place-count=$COUNT)" \
        "$(vdi_tagspec volume Name=${VDI_PLACE_NAME_PREFIX}$RUN vdi-place-run=$RUN)" \
    --query 'Instances[].InstanceId' --output text)"
LAUNCHED=" ${IDS[*]:-}"
[ "${#IDS[@]}" = "$COUNT" ] || die "asked for $COUNT instances, got ${#IDS[@]}"
log "launched: ${IDS[*]}"

# Index = AmiLaunchIndex (0..count-1): stable, and set before anything runs on the nodes.
while read -r iid li; do
    aws ec2 create-tags --resources "$iid" \
        --tags "Key=vdi-place-index,Value=$li" "Key=Name,Value=${VDI_PLACE_NAME_PREFIX}$RUN-$li"
done < <(aws ec2 describe-instances --instance-ids "${IDS[@]}" \
    --query 'Reservations[].Instances[].[InstanceId,AmiLaunchIndex]' --output text)

aws ec2 wait instance-running --instance-ids "${IDS[@]}"
deadline=$(( $(date +%s) + 600 ))
while :; do
    pending=""
    for iid in "${IDS[@]}"; do vdi_ssm_online "$iid" || pending="$pending $iid"; done
    [ -z "$pending" ] && break
    if [ "$(date +%s)" -gt "$deadline" ]; then
        trap - EXIT; rm -f "$UD"
        die "not registered with SSM after 10 min:$pending. Left UP for inspection (dead-man still applies); tear down with 99_teardown.sh $RUN"
    fi
    log "waiting for SSM:$pending"
    sleep 20
done
trap - EXIT
rm -f "$UD"

vdi_place_by_index "$RUN" | while read -r idx iid st; do log "  index $idx  $iid  $st"; done
log "run '$RUN' ready: $COUNT nodes. Next: ./30_run.sh $RUN ..."
log "shell on a node: aws ssm start-session --target <instance-id>"
