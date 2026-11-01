#!/usr/bin/env bash
# Pull one run's results from S3 into the worktree. Not billable (in-region reads to the
# laptop are tiny; event logs, which can be large, are skipped unless --eventlogs).
#
# Usage: aws-vault exec vdi -- ./40_fetch.sh <run-id> [--eventlogs]
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

[ $# -ge 1 ] || die "usage: $0 <run-id> [--eventlogs]"
RUN_ID=$1
EXCLUDES=(--exclude 'usage_logs/*')
[ "${2:-}" = --eventlogs ] || EXCLUDES+=(--exclude '*/eventlog/*')
vdi_check_account

DEST="$AWS_DIR/../benchmarking/data/ec2/$RUN_ID"
mkdir -p "$DEST"
aws s3 sync "s3://$VDI_RESULTS_BUCKET/runs/$RUN_ID" "$DEST" "${EXCLUDES[@]}"
log "fetched to $DEST"
[ -f "$DEST/MATRIX_DONE" ] && log "run complete" || log "run not complete yet (no MATRIX_DONE)"
grep -h "end rep" "$DEST/matrix.log" 2>/dev/null | tail -20 || true
