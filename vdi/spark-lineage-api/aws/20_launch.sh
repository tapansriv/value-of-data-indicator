#!/usr/bin/env bash
# Launch one standalone Spark cluster: 1 driver node (master + application driver, no
# worker) and N worker nodes, all from the AMI built by 10_build_ami.sh, in one AZ.
# BILLABLE: (N+1) instances until 99_teardown.sh, or until the dead-man's switch
# terminates them after <max-hours>.
#
# Usage: aws-vault exec vdi -- ./20_launch.sh <cluster-name> <workers> <max-hours>
#   e.g. ./20_launch.sh n4 4 8
# Env overrides: VDI_AMI (default: newest spark-rg AMI), VDI_TYPE (default r7g.2xlarge),
#   VDI_ROOT_GB (default 200), VDI_YES=1 (skip the confirmation)
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

[ $# = 3 ] || die "usage: $0 <cluster-name> <workers> <max-hours>"
CLUSTER=$1 WORKERS=$2 MAX_HOURS=$3
[[ "$CLUSTER" =~ ^[a-z0-9-]+$ ]] || die "cluster name must be [a-z0-9-]"
[[ "$WORKERS" =~ ^[0-9]+$ && "$WORKERS" -ge 1 ]] || die "workers must be >= 1"
[[ "$MAX_HOURS" =~ ^[0-9]+$ && "$MAX_HOURS" -ge 1 ]] || die "max-hours must be a whole number >= 1"
vdi_check_account

TYPE="${VDI_TYPE:-r7g.2xlarge}"
ROOT_GB="${VDI_ROOT_GB:-200}"
AMI="${VDI_AMI:-$(vdi_latest_spark_ami)}"
[ -n "$AMI" ] || die "no spark-rg AMI; run 10_build_ami.sh"
SG_ID="$(vdi_sg_id)";      [ -n "$SG_ID" ]  || die "no security group; run 00_network.sh"
SUBNET="$(vdi_subnet_id)"; [ -n "$SUBNET" ] || die "no default subnet in $VDI_AZ"
[ -z "$(vdi_instances "$CLUSTER")" ] || die "cluster '$CLUSTER' already has live instances"
ROOT_DEV="$(aws ec2 describe-images --image-ids "$AMI" --query 'Images[0].RootDeviceName' --output text)"

price="$(vdi_price "$TYPE")"
cost=""
[ -n "$price" ] && cost="$(python3 -c "print(f'\${($WORKERS+1)*$price:.2f}/hr; at most \${($WORKERS+1)*$price*$MAX_HOURS:.0f} if left to the dead-man')")"
vdi_confirm "Launch cluster '$CLUSTER': 1 driver + $WORKERS workers, $TYPE, $AMI, ${ROOT_GB} GB gp3 each, $VDI_AZ.
  ${cost:-no price on file for $TYPE}
  Every node terminates itself after ${MAX_HOURS}h."

# gp3 above baseline: shuffle spills to the root volume (r7g has no instance store).
# 300 MB/s is about r7g.2xlarge's baseline EBS bandwidth, so more would be wasted.
BDM="DeviceName=$ROOT_DEV,Ebs={VolumeSize=$ROOT_GB,VolumeType=gp3,Iops=6000,Throughput=300,DeleteOnTermination=true}"

launch() {  # role count user-data-file
    aws ec2 run-instances --image-id "$AMI" --instance-type "$TYPE" --count "$2" \
        --subnet-id "$SUBNET" --security-group-ids "$SG_ID" --key-name "$VDI_KEY_PAIR_NAME" \
        --iam-instance-profile "Name=$VDI_INSTANCE_PROFILE" \
        --metadata-options HttpTokens=required,HttpPutResponseHopLimit=1 \
        --instance-initiated-shutdown-behavior terminate \
        --block-device-mappings "$BDM" \
        --user-data "file://$3" \
        --tag-specifications \
            "$(vdi_tagspec instance Name=vdi-$CLUSTER-$1 vdi-role=$1 vdi-cluster=$CLUSTER vdi-max-hours=$MAX_HOURS vdi-workers=$WORKERS)" \
            "$(vdi_tagspec volume vdi-cluster=$CLUSTER)" \
        --query 'Instances[].InstanceId' --output text
}

userdata() {  # role [master-ip]
    local f; f="$(mktemp)"
    {
        echo "#!/bin/bash"
        echo "export VDI_ROLE=$1 VDI_CLUSTER=$CLUSTER VDI_MAX_MIN=$((MAX_HOURS * 60)) VDI_MASTER_IP=${2:-}"
        tail -n +2 "$AWS_DIR/node/boot.sh"
    } > "$f"
    echo "$f"
}

# Until the cluster is up, any failure (e.g. InsufficientInstanceCapacity on the workers)
# terminates whatever was already launched instead of leaving it to the dead-man.
LAUNCHED=""
cleanup_partial() {
    [ -n "$LAUNCHED" ] || return 0
    log "launch failed: terminating$LAUNCHED"
    aws ec2 terminate-instances --instance-ids $LAUNCHED >/dev/null || true
}
trap 'rc=$?; [ "$rc" = 0 ] || cleanup_partial' EXIT
trap 'exit 130' INT TERM

# ── Driver first: workers need the master's private IP ──
UD="$(userdata driver)"
DRIVER="$(launch driver 1 "$UD")"; rm -f "$UD"
LAUNCHED="$LAUNCHED $DRIVER"
log "driver $DRIVER launched"
aws ec2 wait instance-running --instance-ids "$DRIVER"
MASTER_IP="$(aws ec2 describe-instances --instance-ids "$DRIVER" \
    --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)"

UD="$(userdata worker "$MASTER_IP")"
read -r -a WORKER_IDS <<< "$(launch worker "$WORKERS" "$UD")"; rm -f "$UD"
LAUNCHED="$LAUNCHED ${WORKER_IDS[*]}"
[ "${#WORKER_IDS[@]}" = "$WORKERS" ] || die "asked for $WORKERS workers, got ${#WORKER_IDS[@]}"
log "workers launched: ${WORKER_IDS[*]}"

CONF="$(vdi_write_ssh_config "$CLUSTER" "$DRIVER" "${WORKER_IDS[@]}")"
log "ssh config: $CONF  (ssh -F $CONF driver)"

# ── Wait until the master reports every worker ALIVE ──
deadline=$(( $(date +%s) + 1200 ))
alive=0
while [ "$(date +%s)" -lt "$deadline" ]; do
    alive="$(ssh -F "$CONF" -o ConnectTimeout=20 driver \
        "curl -fs http://$MASTER_IP:8080/json/ | jq .aliveworkers" 2>/dev/null || echo 0)"
    [ "$alive" = "$WORKERS" ] && break
    log "waiting: ${alive:-0}/$WORKERS workers alive"
    sleep 30
done
if [ "$alive" != "$WORKERS" ]; then
    # Deliberately left up: this is the failure worth inspecting (worker logs, boot logs).
    # The dead-man still bounds it.
    trap - EXIT
    die "only $alive/$WORKERS workers registered after 20 min. Cluster left UP for inspection; tear down with 99_teardown.sh $CLUSTER"
fi
trap - EXIT

log "cluster '$CLUSTER' ready: master spark://$MASTER_IP:7077, $WORKERS workers"
# The UIs bind to SPARK_LOCAL_IP (the private IP), not localhost.
log "Spark UI: ssh -F $CONF -L 8080:$MASTER_IP:8080 -L 4040:$MASTER_IP:4040 driver"
