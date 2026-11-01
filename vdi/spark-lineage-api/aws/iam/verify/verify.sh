#!/usr/bin/env bash
# Re-run the full verification battery on vdi-spark-scale-setup.yaml.
# Needs a Python env with: cfn-lint yamllint parliament
#   python3 -m venv .venv && .venv/bin/pip install cfn-lint yamllint parliament
#   VENV=.venv ./verify.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; T="$HERE/../vdi-spark-scale-setup.yaml"
BIN="${VENV:?set VENV to a venv with cfn-lint, yamllint, parliament}/bin"
OUT="$(mktemp -d)"; rc=0
echo "== yamllint (120 cols)";  "$BIN/yamllint" -d '{extends: default, rules: {line-length: {max: 120}, document-start: disable, truthy: {check-keys: false}}}' "$T" && echo ok || rc=1
echo "== cfn-lint";             "$BIN/cfn-lint" --regions us-east-2 -- "$T" && echo ok || rc=1
echo "== render";               "$BIN/python" "$HERE/render.py" "$T" "$OUT" || rc=1
echo "== claims audit";         "$BIN/python" "$HERE/claims_audit.py" "$OUT" | grep -v '^PASS' || rc=1
echo "== parliament (expected: see README, Verification)"
for f in node-role-inline operator; do
  # stdin from /dev/null: parliament refuses --string when it thinks stdin is piped
  echo "-- $f"; "$BIN/parliament" --include-community-auditors --string "$(cat "$OUT/$f.json")" < /dev/null 2>&1
done
exit $rc
