#!/usr/bin/env bash
# Status of placement runs. Read-only; creates nothing.
#
# For every live placement instance (of one run, or of all runs): index, state, uptime,
# spend so far, dead-man time left; plus, from S3, the DONE / FAILED marker and the last
# HEARTBEAT (age, root-disk %) written by node/run_node.sh. Nodes whose instance is gone
# but whose S3 prefix exists are listed too, so a finished run still reports.
# Only placement-tagged instances are listed (project=vdi-placement, vdi-exp=placement);
# spark-scale's instances never appear here.
#
# Exit status: 0 all OK, 1 any WARN, 2 any ALERT.
# Usage: aws-vault exec vdi -- ./45_status.sh [run-name]
set -uo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh" || exit 2
. "$AWS_DIR/lib.sh"

RUN=${1:-}
[ -z "$RUN" ] || vdi_valid_run "$RUN"
vdi_check_account || exit 2

TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT
vdi_place_filters "$RUN"
aws ec2 describe-instances --filters "${VDI_FILTERS[@]}" --output json > "$TMPD/inst.json" || exit 2

# Runs to report on: the one asked for, or every run with a live instance.
if [ -n "$RUN" ]; then RUNS="$RUN"
else RUNS="$(jq -r '.Reservations[].Instances[] | (.Tags // [])[] | select(.Key == "vdi-place-run") | .Value' "$TMPD/inst.json" | sort -u)"; fi

# S3 state per (run, index): "run idx marker marker-text | heartbeat"
: > "$TMPD/s3.txt"
for r in $RUNS; do
    case "$r" in builder-*) continue ;; esac
    for idx in $(aws s3 ls "$VDI_PLACE_S3/$r/" 2>/dev/null | awk '$1 == "PRE" {print $2}' | tr -d / | grep -E '^[0-9]+$'); do
        ls_out="$(aws s3 ls "$VDI_PLACE_S3/$r/$idx/" 2>/dev/null)"
        marker=-
        echo "$ls_out" | grep -q ' FAILED$' && marker="FAILED:$(aws s3 cp "$VDI_PLACE_S3/$r/$idx/FAILED" - 2>/dev/null | tr ' ' '_')"
        echo "$ls_out" | grep -q ' DONE$' && marker="DONE:$(aws s3 cp "$VDI_PLACE_S3/$r/$idx/DONE" - 2>/dev/null | tr ' ' '_')"
        hb="$(aws s3 cp "$VDI_PLACE_S3/$r/$idx/HEARTBEAT" - 2>/dev/null | head -1)"
        echo "$r $idx $marker ${hb:-- - -}" >> "$TMPD/s3.txt"
    done
done

python3 - "$(vdi_price "$VDI_PLACE_DEFAULT_TYPE")" "$TMPD/inst.json" "$TMPD/s3.txt" "${RUN:-}" > "$TMPD/out" <<'EOF'
import json, sys, time, datetime as dt
price, inst_path, s3_path, only = float(sys.argv[1] or 0), sys.argv[2], sys.argv[3], sys.argv[4]
now = dt.datetime.now(dt.timezone.utc)
def hm(h): return f"{int(h)}h{int(h * 60) % 60:02d}m"
s3 = {}
for line in open(s3_path):
    p = line.split()
    if len(p) >= 6:
        s3[(p[0], p[1])] = (p[2], p[3], p[4], p[5])
rows, seen = [], set()
for r in json.load(open(inst_path))["Reservations"]:
    for i in r["Instances"]:
        t = {x["Key"]: x["Value"] for x in i.get("Tags", [])}
        run, idx = t.get("vdi-place-run", "?"), t.get("vdi-place-index", "?")
        up = (now - dt.datetime.fromisoformat(i["LaunchTime"].replace("Z", "+00:00"))).total_seconds() / 3600
        left = float(t["vdi-max-hours"]) - up if "vdi-max-hours" in t else None
        rows.append((run, idx, i["InstanceId"], i["State"]["Name"], up, left))
        seen.add((run, idx))
for (run, idx) in s3:
    if (run, idx) not in seen and (not only or run == only):
        rows.append((run, idx, "-", "gone", None, None))
rows.sort(key=lambda x: (x[0], int(x[1]) if x[1].isdigit() else 999))
total = 0.0
for run, idx, iid, state, up, left in rows:
    marker, hb_t, hb_disk, hb_state = s3.get((run, idx), ("-", "-", "-", "-"))
    lvl, notes = "OK", []
    if up is not None:
        total += up * price
        notes.append(f"up {hm(up)}")
        if state != "running": lvl = "ALERT"
        if left is not None:
            notes.append(f"dead-man in {hm(max(left, 0))}")
            if left < 2 and not marker.startswith("DONE"): lvl = "WARN" if left >= 0.5 else "ALERT"
    if marker.startswith("DONE"): notes.append("DONE " + marker[5:].replace("_", " "))
    elif marker.startswith("FAILED"): lvl = "ALERT"; notes.append("FAILED " + marker[7:].replace("_", " "))
    elif run.startswith("builder-"): notes.append("AMI builder")
    else: notes.append("no DONE marker")
    if hb_t not in ("-", ""):
        age = (time.time() - int(hb_t)) / 60
        notes.append(f"heartbeat {int(age)}m ago ({hb_state}), disk {hb_disk}%")
        if not marker.startswith(("DONE", "FAILED")) and state == "running" and age > 25: lvl = max(lvl, "WARN", key=["OK", "WARN", "ALERT"].index)
        if hb_disk.isdigit() and int(hb_disk) >= 85: lvl = "ALERT"
        elif hb_disk.isdigit() and int(hb_disk) >= 70: lvl = max(lvl, "WARN", key=["OK", "WARN", "ALERT"].index)
    elif state == "running" and not run.startswith("builder-"):
        notes.append("no heartbeat yet (not started?)")
    if state == "gone" and not marker.startswith("DONE"): lvl = "ALERT"
    print(f"{lvl}|{run:<14} node {idx:>2}  {iid:<20} {state:<9} " + "; ".join(notes))
if not rows:
    print(f"OK|no live placement instances{' for run ' + only if only else ''}")
print(f"INFO|spend so far on listed live instances (EC2 only): ~${total:.2f}")
EOF
[ -s "$TMPD/out" ] || exit 2
sed 's/^\([A-Z]*\)|/\1  /' "$TMPD/out"
if grep -q '^ALERT|' "$TMPD/out"; then exit 2; elif grep -q '^WARN|' "$TMPD/out"; then exit 1; else exit 0; fi
