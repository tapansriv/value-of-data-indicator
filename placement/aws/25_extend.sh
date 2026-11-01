#!/usr/bin/env bash
# Reset the dead-man's switch on every node of a placement run to <hours> from now (via
# SSM), for a run that will outlast the max-hours chosen at launch. Also updates the
# vdi-max-hours tag so 45_status.sh reports the new deadline. Keeps instances billing
# longer; creates nothing.
#
# Usage: aws-vault exec vdi -- ./25_extend.sh <run-name> <hours-from-now>
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

[ $# = 2 ] || die "usage: $0 <run-name> <hours-from-now>"
RUN=$1 HOURS=$2
vdi_valid_run "$RUN"
[[ "$HOURS" =~ ^[0-9]+$ && "$HOURS" -ge 1 ]] || die "hours must be a whole number >= 1"
vdi_check_account

read -r -a IDS <<< "$(vdi_place_instances "$RUN")"
[ ${#IDS[@]} -gt 0 ] || die "run '$RUN' has no live instances"
vdi_place_guard "$RUN" "${IDS[@]}"

price="$(vdi_price "$VDI_PLACE_DEFAULT_TYPE")"
vdi_confirm "Reset the dead-man on ${#IDS[@]} nodes of '$RUN' to ${HOURS}h from now (up to ~\$$(python3 -c "print(round(${#IDS[@]}*${price:-0}*$HOURS, 2))") more if left running)."

failed=""
for id in "${IDS[@]}"; do
    if vdi_ssm_run "$id" "set -e
systemctl stop 'vdi-deadman-*.timer'
systemd-run --unit=vdi-deadman-\$(date +%s) --on-active=$((HOURS * 60))min /bin/systemctl poweroff" 60 >/dev/null; then
        up_h="$(aws ec2 describe-instances --instance-ids "$id" --query 'Reservations[0].Instances[0].LaunchTime' --output text \
            | python3 -c "import sys,datetime as d; t=d.datetime.fromisoformat(sys.stdin.read().strip().replace('Z','+00:00')); print(int((d.datetime.now(d.timezone.utc)-t).total_seconds()//3600)+1)")"
        aws ec2 create-tags --resources "$id" --tags "Key=vdi-max-hours,Value=$((up_h + HOURS))"
        log "$id: dead-man reset to ${HOURS}h"
    else
        failed="$failed $id"
    fi
done
[ -z "$failed" ] || die "could not reset:$failed (their old deadline still applies)"
log "all nodes of '$RUN' now terminate in ${HOURS}h"
