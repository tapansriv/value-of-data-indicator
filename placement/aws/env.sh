# Source from every script in aws/ before touching AWS:
#
#   . "$(dirname "$0")/env.sh"
#   vdi_check_account          # before anything that creates a billable resource
#
# Loads account-specific settings from outside the repo. This is the SAME file the
# spark-scale experiment uses (value_of_data/spark-scale/spark-lineage-api/aws/SECRETS.md):
# one account, one results bucket, one key pair. Nothing account-specific is committed here.
#
# Isolation from spark-scale (see lib.sh, "Isolation"): that file may set VDI_TAG_KEY /
# VDI_TAG_VALUE for spark-scale's own selectors. This experiment never uses them; its tag
# is hard-coded below and the inherited variables are unset so no helper can pick them up.

VDI_ENV_FILE="${VDI_ENV_FILE:-$HOME/.config/vdi-spark/env}"

if [ ! -r "$VDI_ENV_FILE" ]; then
    echo "error: $VDI_ENV_FILE not found. Copy aws/env.example there and fill it in." >&2
    return 1 2>/dev/null || exit 1
fi

set -a
. "$VDI_ENV_FILE"
set +a

for _v in VDI_AWS_ACCOUNT_ID VDI_AWS_REGION VDI_RESULTS_BUCKET VDI_KEY_PAIR_NAME VDI_SSH_KEY VDI_VPC_ID; do
    eval "_val=\${$_v:-}"
    if [ -z "$_val" ]; then
        echo "error: $_v is not set in $VDI_ENV_FILE" >&2
        return 1 2>/dev/null || exit 1
    fi
done
unset _v _val

export AWS_REGION="$VDI_AWS_REGION"

# ── Placement-experiment identity (NOT taken from the env file) ──
VDI_PLACE_TAG_KEY=project
VDI_PLACE_TAG_VALUE=vdi-placement
# If the shared file ever named this experiment's tag value as spark-scale's, spark-scale's
# selectors would match our instances. Refuse rather than proceed.
if [ "${VDI_TAG_VALUE:-}" = "$VDI_PLACE_TAG_VALUE" ]; then
    echo "error: $VDI_ENV_FILE sets VDI_TAG_VALUE=$VDI_PLACE_TAG_VALUE, which is the placement tag; spark-scale would select placement instances" >&2
    return 1 2>/dev/null || exit 1
fi
unset VDI_TAG_KEY VDI_TAG_VALUE

# Refuse to proceed if the active credentials belong to a different account than the
# config names, e.g. a stale profile or the wrong aws-vault entry.
vdi_check_account() {
    local actual
    actual="$(aws sts get-caller-identity --query Account --output text)" || {
        echo "error: no working AWS credentials (aws sts get-caller-identity failed)" >&2
        return 1
    }
    if [ "$actual" != "$VDI_AWS_ACCOUNT_ID" ]; then
        echo "error: credentials are for account $actual, config expects $VDI_AWS_ACCOUNT_ID" >&2
        return 1
    fi
}
