# Shared helpers for the numbered scripts in this directory. Source after env.sh:
#
#   AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
#   . "$AWS_DIR/env.sh"
#   . "$AWS_DIR/lib.sh"
#
# Nothing here creates a billable resource on its own.

VDI_INSTANCE_PROFILE="${VDI_INSTANCE_PROFILE:-vdi-spark-node}"
VDI_SG_NAME="${VDI_SG_NAME:-vdi-spark-cluster}"
VDI_AZ="${VDI_AZ:-${VDI_AWS_REGION}a}"
VDI_TAG_KEY="${VDI_TAG_KEY:-project}"
VDI_TAG_VALUE="${VDI_TAG_VALUE:-vdi-spark-scale}"
VDI_SSH_DIR="${VDI_SSH_DIR:-$HOME/.config/vdi-spark/ssh}"

# On-demand list prices, us-east-2, $/hr. Used only for the cost line printed before a
# launch; re-check before relying on them. Unknown types print no estimate.
vdi_price() {
    case "$1" in
        r7g.2xlarge) echo 0.4284 ;;
        *) echo "" ;;
    esac
}

die() { echo "error: $*" >&2; exit 1; }
log() { echo "[$(date '+%H:%M:%S')] $*" >&2; }

# --tag-specifications value for one resource type, plus extra Key=Value pairs.
vdi_tagspec() {
    local rtype=$1; shift
    local tags="{Key=$VDI_TAG_KEY,Value=$VDI_TAG_VALUE}"
    local kv
    for kv in "$@"; do
        tags="$tags,{Key=${kv%%=*},Value=${kv#*=}}"
    done
    echo "ResourceType=$rtype,Tags=[$tags]"
}

vdi_sg_id() {
    aws ec2 describe-security-groups \
        --filters "Name=vpc-id,Values=$VDI_VPC_ID" "Name=group-name,Values=$VDI_SG_NAME" \
        --query 'SecurityGroups[0].GroupId' --output text | grep -v '^None$' || true
}

# The default VPC's default subnet in $VDI_AZ. Every node of a cluster goes in one AZ:
# cross-AZ shuffle traffic is billed and slower, which would confound the node-count axis.
vdi_subnet_id() {
    aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$VDI_VPC_ID" "Name=availability-zone,Values=$VDI_AZ" \
                  "Name=default-for-az,Values=true" \
        --query 'Subnets[0].SubnetId' --output text | grep -v '^None$' || true
}

# Latest Canonical Ubuntu 22.04 arm64 image. Looked up with describe-images because the
# operator policy denies Parameter Store (iam/README.md).
vdi_ubuntu_arm64_ami() {
    aws ec2 describe-images --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd*/ubuntu-jammy-22.04-arm64-server-*" \
                  "Name=state,Values=available" \
        --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text
}

# Newest AMI produced by 10_build_ami.sh.
vdi_latest_spark_ami() {
    aws ec2 describe-images --owners self \
        --filters "Name=tag:$VDI_TAG_KEY,Values=$VDI_TAG_VALUE" "Name=tag:vdi-image,Values=spark-rg" \
                  "Name=state,Values=available" \
        --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text | grep -v '^None$' || true
}

# Instance IDs of a cluster (or every tagged instance when cluster is empty) that are not
# yet terminated.
vdi_instances() {
    local cluster=${1:-}
    local filters=("Name=tag:$VDI_TAG_KEY,Values=$VDI_TAG_VALUE"
                   "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down")
    [ -n "$cluster" ] && filters+=("Name=tag:vdi-cluster,Values=$cluster")
    aws ec2 describe-instances --filters "${filters[@]}" \
        --query 'Reservations[].Instances[].InstanceId' --output text
}

# SSH config for one cluster. Hosts are tunneled through SSM (AWS-StartSSHSession), so no
# inbound port is open. Use as: ssh -F "$(vdi_ssh_config <cluster>)" <host>
vdi_ssh_config() { echo "$VDI_SSH_DIR/$1.conf"; }

vdi_write_ssh_config() {
    local cluster=$1 driver_id=$2; shift 2
    mkdir -p "$VDI_SSH_DIR" && chmod 700 "$VDI_SSH_DIR"
    local f; f="$(vdi_ssh_config "$cluster")"
    {
        echo "# written by 20_launch.sh for cluster $cluster, $(date -u +%FT%TZ)"
        echo "Host *"
        echo "    User ubuntu"
        echo "    IdentityFile $VDI_SSH_KEY"
        echo "    IdentitiesOnly yes"
        echo "    StrictHostKeyChecking accept-new"
        echo "    UserKnownHostsFile $VDI_SSH_DIR/known_hosts"
        echo "    ServerAliveInterval 30"
        echo "    ProxyCommand aws ssm start-session --target %h --document-name AWS-StartSSHSession --parameters portNumber=%p --region $VDI_AWS_REGION"
        echo "Host driver"
        echo "    HostName $driver_id"
        local i=1 w
        for w in "$@"; do
            echo "Host w$i"
            echo "    HostName $w"
            i=$((i + 1))
        done
    } > "$f"
    chmod 600 "$f"
    echo "$f"
}

# Ask for an explicit "yes" before anything billable, unless VDI_YES=1.
vdi_confirm() {
    echo "$1" >&2
    [ "${VDI_YES:-0}" = 1 ] && return 0
    local ans
    read -r -p "Type yes to continue: " ans
    [ "$ans" = yes ] || die "aborted"
}
