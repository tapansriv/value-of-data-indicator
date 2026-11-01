# Source from every script in spark-lineage-api/aws/ before touching AWS:
#
#   . "$(dirname "$0")/env.sh"
#   vdi_check_account          # before anything that creates a billable resource
#
# Loads account-specific settings from outside the repo (see SECRETS.md).

VDI_ENV_FILE="${VDI_ENV_FILE:-$HOME/.config/vdi-spark/env}"

if [ ! -r "$VDI_ENV_FILE" ]; then
    echo "error: $VDI_ENV_FILE not found. Copy spark-lineage-api/aws/env.example there and fill it in." >&2
    return 1 2>/dev/null || exit 1
fi

set -a
. "$VDI_ENV_FILE"
set +a

for _v in VDI_AWS_ACCOUNT_ID VDI_AWS_REGION VDI_RESULTS_BUCKET VDI_KEY_PAIR_NAME VDI_SSH_KEY; do
    eval "_val=\${$_v:-}"
    if [ -z "$_val" ]; then
        echo "error: $_v is not set in $VDI_ENV_FILE" >&2
        return 1 2>/dev/null || exit 1
    fi
done
unset _v _val

export AWS_REGION="$VDI_AWS_REGION"

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
