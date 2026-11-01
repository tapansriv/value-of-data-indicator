# Shared helpers for the numbered scripts in this directory. Source after env.sh:
#
#   AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
#   . "$AWS_DIR/env.sh"
#   . "$AWS_DIR/lib.sh"
#
# Nothing here creates a billable resource on its own.
#
# ── Isolation from the spark-scale experiment ────────────────────────────────────────
# Both experiments run in the same account and region, from the same env file. They are
# kept apart by tags, never by instance IDs typed by hand:
#
#   spark-scale selects   instances:  tag:project=vdi-spark-scale  [+ tag:vdi-cluster=<c>]
#                         AMIs:       tag:project=vdi-spark-scale + tag:vdi-image=spark-rg
#                         30_run.sh:  tag:vdi-cluster=<c> + tag:vdi-role=driver
#                         Names:      vdi-<cluster>-{driver,worker}, vdi-builder-<id>
#   placement (this dir)  instances:  tag:project=vdi-placement + tag:vdi-exp=placement
#                                     + tag:vdi-place-run=<run>
#                         AMIs:       tag:project=vdi-placement + tag:vdi-image=placement
#                         Names:      vdi-place-<run>-<i>, vdi-place-builder-<id>
#
# Placement resources never carry project=vdi-spark-scale, vdi-cluster or vdi-role, so no
# spark-scale filter can match them (and its `99_teardown.sh --all` cannot reach them).
# Every placement selector requires project=vdi-placement AND vdi-exp=placement, so it
# cannot match spark-scale resources. As a second line, vdi_place_guard re-reads the tags of
# every instance about to be touched and refuses unless all three placement tags and the
# Name prefix are present. Placement nodes also get their own security group
# (vdi-place-node, no inbound rules), so they cannot reach spark-scale nodes' Spark ports.
# Shared on purpose: the instance role (vdi-spark-node), the key pair, the default VPC
# subnet, the S3 gateway endpoint, the results bucket (under the placement*/ prefixes only)
# and the account's vCPU quota.

VDI_INSTANCE_PROFILE="${VDI_INSTANCE_PROFILE:-vdi-spark-node}"
VDI_PLACE_SG_NAME="${VDI_PLACE_SG_NAME:-vdi-place-node}"
VDI_AZ="${VDI_AZ:-${VDI_AWS_REGION}a}"
VDI_PLACE_NAME_PREFIX=vdi-place-
VDI_PLACE_EXP_KEY=vdi-exp
VDI_PLACE_EXP_VALUE=placement
VDI_PLACE_DATA_BUCKET="${VDI_PLACE_DATA_BUCKET:-vod-tpcds-10gb}"
VDI_PLACE_S3="s3://$VDI_RESULTS_BUCKET/placement"            # per-run results
VDI_PLACE_BUILD_S3="s3://$VDI_RESULTS_BUCKET/placement-build" # AMI build sources/logs
VDI_PLACE_DEFAULT_TYPE=m7g.2xlarge
VDI_PLACE_VCPU=8   # m7g.2xlarge

# On-demand list prices, us-east-2, $/hr. Used only for the cost lines printed before a
# launch; re-check before relying on them. Unknown types print no estimate.
vdi_price() {
    case "$1" in
        r7g.2xlarge) echo 0.4284 ;;
        m7g.2xlarge) echo 0.3264 ;;   # verify: from memory of the us-east-2 on-demand list
        *) echo "" ;;
    esac
}

die() { echo "error: $*" >&2; exit 1; }
log() { echo "[$(date '+%H:%M:%S')] $*" >&2; }

vdi_valid_run() { [[ "$1" =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "run name must be [a-z0-9-] (got '$1')"; }

# --tag-specifications value for one resource type: always the two placement tags, plus
# extra Key=Value pairs.
vdi_tagspec() {
    local rtype=$1; shift
    local tags="{Key=$VDI_PLACE_TAG_KEY,Value=$VDI_PLACE_TAG_VALUE},{Key=$VDI_PLACE_EXP_KEY,Value=$VDI_PLACE_EXP_VALUE}"
    local kv
    for kv in "$@"; do
        tags="$tags,{Key=${kv%%=*},Value=${kv#*=}}"
    done
    echo "ResourceType=$rtype,Tags=[$tags]"
}

vdi_sg_id() {
    aws ec2 describe-security-groups \
        --filters "Name=vpc-id,Values=$VDI_VPC_ID" "Name=group-name,Values=$VDI_PLACE_SG_NAME" \
                  "Name=tag:$VDI_PLACE_TAG_KEY,Values=$VDI_PLACE_TAG_VALUE" \
        --query 'SecurityGroups[0].GroupId' --output text | grep -v '^None$' || true
}

# The default VPC's default subnet in $VDI_AZ (same choice as spark-scale).
vdi_subnet_id() {
    aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$VDI_VPC_ID" "Name=availability-zone,Values=$VDI_AZ" \
                  "Name=default-for-az,Values=true" \
        --query 'Subnets[0].SubnetId' --output text | grep -v '^None$' || true
}

# Latest Canonical Ubuntu 22.04 arm64 image (describe-images: the operator policy denies
# Parameter Store).
vdi_ubuntu_arm64_ami() {
    aws ec2 describe-images --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd*/ubuntu-jammy-22.04-arm64-server-*" \
                  "Name=state,Values=available" \
        --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text
}

# Newest AMI produced by 10_build_ami.sh.
vdi_latest_place_ami() {
    aws ec2 describe-images --owners self \
        --filters "Name=tag:$VDI_PLACE_TAG_KEY,Values=$VDI_PLACE_TAG_VALUE" \
                  "Name=tag:$VDI_PLACE_EXP_KEY,Values=$VDI_PLACE_EXP_VALUE" \
                  "Name=tag:vdi-image,Values=placement" "Name=state,Values=available" \
        --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text | grep -v '^None$' || true
}

# Placement instances that are not yet terminated: of one run, or of every run with "".
vdi_place_filters() {
    local run=${1:-}
    VDI_FILTERS=("Name=tag:$VDI_PLACE_TAG_KEY,Values=$VDI_PLACE_TAG_VALUE"
                 "Name=tag:$VDI_PLACE_EXP_KEY,Values=$VDI_PLACE_EXP_VALUE"
                 "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down")
    if [ -n "$run" ]; then VDI_FILTERS+=("Name=tag:vdi-place-run,Values=$run"); fi
}
vdi_place_instances() {
    vdi_place_filters "${1:-}"
    aws ec2 describe-instances --filters "${VDI_FILTERS[@]}" \
        --query 'Reservations[].Instances[].InstanceId' --output text
}

# "<index> <instance-id> <state>" per live instance of a run, sorted by index.
vdi_place_by_index() {
    vdi_place_filters "$1"
    aws ec2 describe-instances --filters "${VDI_FILTERS[@]}" --output json \
        | jq -r '.Reservations[].Instances[]
                 | [ ((.Tags // []) | map(select(.Key == "vdi-place-index")) | .[0].Value // "?"),
                     .InstanceId, .State.Name ] | @tsv' \
        | sort -n
}

# Refuse unless EVERY given instance carries the placement tags, the Name prefix and (if
# a run is given) that run's tag. Call right before anything that changes an instance.
vdi_place_guard() {
    local run=$1; shift
    [ $# -gt 0 ] || return 0
    local bad
    bad="$(aws ec2 describe-instances --instance-ids "$@" --output json | jq -r \
        --arg k "$VDI_PLACE_TAG_KEY" --arg v "$VDI_PLACE_TAG_VALUE" \
        --arg ek "$VDI_PLACE_EXP_KEY" --arg ev "$VDI_PLACE_EXP_VALUE" \
        --arg p "$VDI_PLACE_NAME_PREFIX" --arg run "$run" '
        .Reservations[].Instances[]
        | ((.Tags // []) | map({(.Key): .Value}) | add // {}) as $t
        | select(($t[$k] != $v) or ($t[$ek] != $ev)
                 or (($t.Name // "") | startswith($p) | not)
                 or ($t["vdi-cluster"] != null)
                 or ($run != "" and $t["vdi-place-run"] != $run))
        | "\(.InstanceId) Name=\($t.Name // "-") \($k)=\($t[$k] // "-") \($ek)=\($t[$ek] // "-") vdi-place-run=\($t["vdi-place-run"] // "-")"')"
    if [ -n "$bad" ]; then
        echo "$bad" >&2
        die "ISOLATION GUARD: the instances above are not placement instances${run:+ of run '$run'}; refusing to touch anything"
    fi
}

vdi_ssm_online() {   # instance-id -> exit 0 if the SSM agent has registered
    [ "$(aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$1" \
        --query 'length(InstanceInformationList)' --output text 2>/dev/null || echo 0)" = 1 ]
}

# Run a bash script on one instance via SSM (AWS-RunShellScript, as root) and wait for it.
# The script travels base64-encoded so bash-isms and quoting survive the document's sh.
# Prints the command's stdout; stderr goes to stderr. Status 0 iff the command succeeded.
# Usage: vdi_ssm_run <instance-id> <script> [timeout-seconds]
vdi_ssm_run() {
    local iid=$1 script=$2 to=${3:-300} params cid out st
    params="$(mktemp)"
    jq -n --arg c "echo $(printf '%s' "$script" | base64 | tr -d '\n') | base64 -d | bash" \
          --arg t "$to" '{commands: [$c], executionTimeout: [$t]}' > "$params"
    cid="$(aws ssm send-command --instance-ids "$iid" --document-name AWS-RunShellScript \
        --parameters "file://$params" --query Command.CommandId --output text)" || { rm -f "$params"; return 1; }
    rm -f "$params"
    while :; do
        sleep 3
        out="$(aws ssm get-command-invocation --command-id "$cid" --instance-id "$iid" --output json 2>/dev/null)" || continue
        st="$(echo "$out" | jq -r .Status)"
        case "$st" in
            Pending|InProgress|Delayed) continue ;;
        esac
        echo "$out" | jq -r '.StandardOutputContent'
        echo "$out" | jq -r '.StandardErrorContent' | sed '/^$/d' >&2
        [ "$st" = Success ]
        return
    done
}

# Tarball of a git working tree (tracked + untracked-but-not-ignored files), so uncommitted
# harness edits ship too. Writes <out>.info with the commit and whether the tree was dirty.
# Usage: vdi_pack_tree <dir> <out.tar.gz> [extra git pathspec excludes...]
vdi_pack_tree() {
    local dir=$1 out=$2; shift 2
    local sha dirty
    sha="$(git -C "$dir" rev-parse HEAD)"
    dirty="$(git -C "$dir" status --porcelain -- . | wc -l | tr -d ' ')"
    git -C "$dir" ls-files -co --exclude-standard -z -- . "$@" \
        | tar -C "$dir" --null -T - -czf "$out"
    printf 'path=%s\ncommit=%s\nuncommitted_paths=%s\npacked_utc=%s\n' \
        "$dir" "$sha" "$dirty" "$(date -u +%FT%TZ)" > "$out.info"
}

# Ask for an explicit "yes" before anything billable, unless VDI_YES=1.
vdi_confirm() {
    echo "$1" >&2
    [ "${VDI_YES:-0}" = 1 ] && return 0
    local ans
    read -r -p "Type yes to continue: " ans
    [ "$ans" = yes ] || die "aborted"
}
