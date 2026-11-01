#!/usr/bin/env bash
# Reset the dead-man's switch on every node of a cluster to <hours> from now, for a run
# that will outlast the max-hours chosen at launch. Also updates the vdi-max-hours tag so
# 45_status.sh reports the new deadline. Extending keeps instances billing longer; it
# creates nothing new.
#
# Usage: aws-vault exec vdi -- ./25_extend.sh <cluster> <hours-from-now>
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

[ $# = 2 ] || die "usage: $0 <cluster> <hours-from-now>"
CLUSTER=$1 HOURS=$2
[[ "$HOURS" =~ ^[0-9]+$ && "$HOURS" -ge 1 ]] || die "hours must be a whole number >= 1"
vdi_check_account

CONF="$(vdi_ssh_config "$CLUSTER")"
[ -f "$CONF" ] || die "no ssh config for '$CLUSTER'"
read -r -a IDS <<< "$(vdi_instances "$CLUSTER")"
[ ${#IDS[@]} -gt 0 ] || die "cluster '$CLUSTER' has no live instances"

price="$(vdi_price r7g.2xlarge)"
vdi_confirm "Reset the dead-man on ${#IDS[@]} nodes of '$CLUSTER' to ${HOURS}h from now (up to ~\$$(python3 -c "print(round(${#IDS[@]}*${price:-0}*$HOURS))") more if left running)."

hosts="driver $(grep -o '^Host w[0-9]*' "$CONF" | awk '{print $2}' | tr '\n' ' ')"
failed=""
for h in $hosts; do
    if ssh -F "$CONF" -o ConnectTimeout=30 "$h" "sudo systemctl stop 'vdi-deadman-*.timer' && sudo systemd-run --unit=vdi-deadman-\$(date +%s) --on-active=$((HOURS * 60))min /bin/systemctl poweroff" 2>/dev/null; then
        log "$h: dead-man reset to ${HOURS}h"
    else
        failed="$failed $h"
    fi
done
# vdi-max-hours is measured from launch time: new value = current uptime + HOURS
for id in "${IDS[@]}"; do
    up_h="$(aws ec2 describe-instances --instance-ids "$id" --query 'Reservations[0].Instances[0].LaunchTime' --output text \
        | python3 -c "import sys,datetime as d; t=d.datetime.fromisoformat(sys.stdin.read().strip().replace('Z','+00:00')); print(int((d.datetime.now(d.timezone.utc)-t).total_seconds()//3600)+1)")"
    aws ec2 create-tags --resources "$id" --tags "Key=vdi-max-hours,Value=$((up_h + HOURS))"
done
[ -z "$failed" ] || die "could not reach:$failed (their old deadline still applies)"
log "all nodes of '$CLUSTER' now terminate in ${HOURS}h"
