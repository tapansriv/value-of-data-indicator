#!/usr/bin/env bash
# Pull one placement run's results from S3 into data/spark/<run-name>/ in this repo.
# Not billable in any meaningful way (small objects). Only that run's directory is written,
# so other runs' local files are never touched; within it, `aws s3 sync` only downloads
# objects that are new or changed, so rerunning mid-run just tops it up. The shipped
# source tarballs (src/, node/) are skipped.
#
# Usage: aws-vault exec vdi -- ./40_fetch.sh <run-name>
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"

[ $# = 1 ] || die "usage: $0 <run-name>"
RUN=$1
vdi_valid_run "$RUN"
vdi_check_account

REPO="$(git -C "$AWS_DIR" rev-parse --show-toplevel)"
DEST="$REPO/data/spark/$RUN"
SRC="$VDI_PLACE_S3/$RUN"
aws s3 ls "$SRC/" >/dev/null 2>&1 || die "nothing at $SRC/"
mkdir -p "$DEST"
aws s3 sync "$SRC" "$DEST" --exclude 'src/*' --exclude 'node/*' --no-progress
log "fetched to $DEST"

for d in "$DEST"/*/; do
    [ -d "$d" ] || continue
    i="$(basename "$d")"
    if   [ -f "$d/DONE" ];   then s="DONE   $(cat "$d/DONE")"
    elif [ -f "$d/FAILED" ]; then s="FAILED $(cat "$d/FAILED")"
    else s="in progress (no DONE/FAILED marker yet)"; fi
    n="$(find "$d/results" -type f 2>/dev/null | wc -l | tr -d ' ')"
    log "node $i: $s; $n result files"
done
