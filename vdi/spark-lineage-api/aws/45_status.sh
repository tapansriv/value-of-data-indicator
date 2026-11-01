#!/usr/bin/env bash
# Health report for a cluster and (optionally) a run. Read-only; creates nothing.
# Each line is OK / WARN / ALERT. Exit status: 0 all OK, 1 any WARN, 2 any ALERT,
# so a scheduled check can act on the code alone.
#
# Usage: aws-vault exec vdi -- ./45_status.sh <cluster> [run-id]
set -uo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh" || exit 2
. "$AWS_DIR/lib.sh"

[ $# -ge 1 ] || die "usage: $0 <cluster> [run-id]"
CLUSTER=$1 RUN_ID=${2:-}
vdi_check_account || exit 2

OUT="$(mktemp)"; trap 'rm -f "$OUT"' EXIT
emit() { echo "$1|$2" >> "$OUT"; }

# ── Instances: uptime, spend so far, dead-man time left, strays ──
aws ec2 describe-instances \
    --filters "Name=tag:$VDI_TAG_KEY,Values=$VDI_TAG_VALUE" \
              "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down" \
    --output json > "$OUT.inst"
python3 - "$CLUSTER" "$(vdi_price r7g.2xlarge)" "$OUT.inst" >> "$OUT" <<'EOF'
import json, sys, datetime as dt
cluster, price, path = sys.argv[1], float(sys.argv[2] or 0), sys.argv[3]
now = dt.datetime.now(dt.timezone.utc)
mine, other = [], []
for r in json.load(open(path))["Reservations"]:
    for i in r["Instances"]:
        tags = {t["Key"]: t["Value"] for t in i.get("Tags", [])}
        up = (now - dt.datetime.fromisoformat(i["LaunchTime"].replace("Z", "+00:00"))).total_seconds() / 3600
        (mine if tags.get("vdi-cluster") == cluster else other).append((i, tags, up))
def hm(h): return f"{int(h)}h{int(h * 60) % 60:02d}m"
if not mine:
    print(f"WARN|cluster {cluster}: no live instances")
else:
    states = sorted({i["State"]["Name"] for i, _, _ in mine})
    n_w = sum(1 for _, t, _ in mine if t.get("vdi-role") == "worker")
    intended = next((int(t["vdi-workers"]) for _, t, _ in mine if t.get("vdi-role") == "driver" and "vdi-workers" in t), None)
    if intended is not None and intended != n_w:
        print(f"ALERT|cluster {cluster}: {n_w} worker instances live, launched with {intended}")
        n_w = intended
    up = max(u for _, _, u in mine)
    cost = sum(u for _, _, u in mine) * price
    lvl = "OK" if states == ["running"] else "ALERT"
    print(f"{lvl}|cluster {cluster}: {len(mine)} instances (1 driver + {n_w} workers), states {states}, up {hm(up)}, ~${cost:.2f} so far")
    left = [float(t["vdi-max-hours"]) - u for _, t, u in mine if "vdi-max-hours" in t]
    if left:
        m = min(left)
        lvl = "ALERT" if m < 0.5 else "WARN" if m < 2 else "OK"   # extend with 25_extend.sh
        print(f"{lvl}|cluster {cluster}: dead-man switch fires in {hm(max(m, 0))}")
    print(f"INFO|workers={n_w}")  # intended size: the master check compares against it
for i, t, u in other:
    print(f"WARN|other live project instance {i['InstanceId']} ({t.get('vdi-cluster', 'untagged')}, {i['State']['Name']}, up {hm(u)})")
EOF
rm -f "$OUT.inst"
WORKERS="$(sed -n 's/^INFO|workers=//p' "$OUT")"
sed -i '' '/^INFO|workers=/d' "$OUT"

# ── Driver-side probe and worker disks ──
CONF="$(vdi_ssh_config "$CLUSTER")"
if [ -n "$WORKERS" ] && [ -f "$CONF" ]; then
    expected="$WORKERS"
    [ -n "$RUN_ID" ] && grep -q '^mode=local' <(aws s3 cp "s3://$VDI_RESULTS_BUCKET/runs/$RUN_ID/run_metadata.txt" - 2>/dev/null) && expected=0
    if ! ssh -F "$CONF" -o ConnectTimeout=30 driver "bash -s -- $expected $RUN_ID" \
            < "$AWS_DIR/node/status_remote.sh" >> "$OUT" 2>/dev/null; then
        emit ALERT "driver unreachable over SSM/SSH"
    fi
    # Worker root disks (shuffle spills there), probed in parallel
    tmpd="$(mktemp -d)"
    i=1
    while [ "$i" -le "$WORKERS" ]; do
        ( ssh -F "$CONF" -o ConnectTimeout=30 "w$i" "df --output=pcent / | tail -1" > "$tmpd/w$i" 2>/dev/null || echo X > "$tmpd/w$i" ) &
        i=$((i + 1))
    done
    wait
    worst=0 worst_w="" unreach=""
    for f in "$tmpd"/w*; do
        p="$(tr -dc '0-9X' < "$f")"
        if [ "$p" = X ] || [ -z "$p" ]; then unreach="$unreach $(basename "$f")"; continue; fi
        [ "$p" -gt "$worst" ] && { worst=$p; worst_w=$(basename "$f"); }
    done
    rm -rf "$tmpd"
    [ -n "$unreach" ] && emit WARN "workers unreachable for disk check:$unreach"
    lvl=OK; [ "$worst" -ge 70 ] && lvl=WARN; [ "$worst" -ge 85 ] && lvl=ALERT
    emit $lvl "worker disks: fullest ${worst}% (${worst_w:-n/a})"
elif [ -n "$WORKERS" ]; then
    emit WARN "no ssh config at $CONF; skipped driver/worker probes"
fi

# ── Listener evidence in S3 (cols / rowgroup write usage logs) ──
if [ -n "$RUN_ID" ]; then
    n_obj="$(aws s3 ls --recursive "s3://$VDI_RESULTS_BUCKET/runs/$RUN_ID/usage_logs/" 2>/dev/null | grep -c '\.parquet$' || true)"
    emit OK "run $RUN_ID: ${n_obj:-0} usage-log parquet objects in S3"
fi

# ── Report ──
for lvl in ALERT WARN OK INFO; do grep "^$lvl|" "$OUT" | sed "s/^$lvl|/$(printf '%-5s' $lvl) /"; done
if grep -q '^ALERT|' "$OUT"; then exit 2; elif grep -q '^WARN|' "$OUT"; then exit 1; else exit 0; fi
