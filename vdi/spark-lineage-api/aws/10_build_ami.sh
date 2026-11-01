#!/usr/bin/env bash
# Build the instrumented Spark + listener jars once, on a Graviton builder, and bake an AMI.
# BILLABLE: one r7g.2xlarge for the build (~1.5-2.5 h, ~$1), then AMI snapshot storage
# (~$0.05/GB-month).
#
# Sources are pinned by commit and shipped as git-archive tarballs through the results
# bucket, so the image records exactly what it was built from and the builder needs no
# GitHub key. Only COMMITTED state is built; uncommitted edits are refused.
#
# Usage: aws-vault exec vdi -- ./10_build_ami.sh
# Env overrides: VDI_SPARK_REPO, VDI_PARQUET_REPO (fork checkouts), VDI_SPARK_REF
#   (default rowgroup-dev), VDI_PARQUET_REF (default vod_rg), VDI_BUILD_MAX_HOURS (default 6)
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"
vdi_check_account

VDI_REPO="$(git -C "$AWS_DIR" rev-parse --show-toplevel)"
SPARK_REPO="${VDI_SPARK_REPO:-$VDI_REPO/../spark}"
PARQUET_REPO="${VDI_PARQUET_REPO:-$VDI_REPO/../parquet-java}"
SPARK_REF="${VDI_SPARK_REF:-rowgroup-dev}"
PARQUET_REF="${VDI_PARQUET_REF:-vod_rg}"
MAX_HOURS="${VDI_BUILD_MAX_HOURS:-6}"
TYPE=r7g.2xlarge

SPARK_SHA="$(git -C "$SPARK_REPO" rev-parse "$SPARK_REF^{commit}")"
PARQUET_SHA="$(git -C "$PARQUET_REPO" rev-parse "$PARQUET_REF^{commit}")"
VDI_SHA="$(git -C "$VDI_REPO" rev-parse HEAD)"
if [ -n "$(git -C "$VDI_REPO" status --porcelain -- spark-lineage-api/listener_versions_new spark-lineage-api/pom.xml spark-lineage-api/src)" ]; then
    die "uncommitted listener changes in $VDI_REPO; the build uses HEAD only. Commit first."
fi

SG_ID="$(vdi_sg_id)";        [ -n "$SG_ID" ]  || die "no security group; run 00_network.sh"
SUBNET="$(vdi_subnet_id)";   [ -n "$SUBNET" ] || die "no default subnet in $VDI_AZ"
BASE_AMI="$(vdi_ubuntu_arm64_ami)"
ROOT_DEV="$(aws ec2 describe-images --image-ids "$BASE_AMI" --query 'Images[0].RootDeviceName' --output text)"
BUILD_ID="$(date -u +%Y%m%d-%H%M%S)"
S3="s3://$VDI_RESULTS_BUCKET/build/$BUILD_ID"
price="$(vdi_price $TYPE)"

vdi_confirm "Build $BUILD_ID on one $TYPE (\$$price/hr; dead-man stop after ${MAX_HOURS}h):
  spark        $SPARK_REF  $SPARK_SHA
  parquet-java $PARQUET_REF  $PARQUET_SHA
  vdi          HEAD  $VDI_SHA
  base AMI     $BASE_AMI (Ubuntu 22.04 arm64)"

# ── Ship sources ──
log "uploading source archives to $S3/src/"
git -C "$SPARK_REPO"   archive --format=tar.gz "$SPARK_SHA"   | aws s3 cp - "$S3/src/spark.tar.gz" --quiet
git -C "$PARQUET_REPO" archive --format=tar.gz "$PARQUET_SHA" | aws s3 cp - "$S3/src/parquet-java.tar.gz" --quiet
git -C "$VDI_REPO"     archive --format=tar.gz "$VDI_SHA" spark-lineage-api | aws s3 cp - "$S3/src/vdi.tar.gz" --quiet

# ── Launch the builder ──
UD="$(mktemp)"; trap 'rm -f "$UD"' EXIT
{
    echo "#!/bin/bash"
    echo "VDI_BUCKET=$VDI_RESULTS_BUCKET VDI_BUILD_ID=$BUILD_ID VDI_REGION=$VDI_AWS_REGION"
    echo "VDI_MAX_MIN=$((MAX_HOURS * 60)) VDI_DATA_BUCKET=$VDI_DATA_BUCKET_TPCH"
    echo "VDI_SPARK_SHA=$SPARK_SHA VDI_PARQUET_SHA=$PARQUET_SHA VDI_VDI_SHA=$VDI_SHA"
    echo "export VDI_BUCKET VDI_BUILD_ID VDI_REGION VDI_MAX_MIN VDI_DATA_BUCKET VDI_SPARK_SHA VDI_PARQUET_SHA VDI_VDI_SHA"
    tail -n +2 "$AWS_DIR/node/build_ami.sh"
} > "$UD"

IID="$(aws ec2 run-instances --image-id "$BASE_AMI" --instance-type $TYPE --count 1 \
    --subnet-id "$SUBNET" --security-group-ids "$SG_ID" --key-name "$VDI_KEY_PAIR_NAME" \
    --iam-instance-profile "Name=$VDI_INSTANCE_PROFILE" \
    --metadata-options HttpTokens=required,HttpPutResponseHopLimit=1 \
    --instance-initiated-shutdown-behavior stop \
    --block-device-mappings "DeviceName=$ROOT_DEV,Ebs={VolumeSize=100,VolumeType=gp3,DeleteOnTermination=true}" \
    --user-data "file://$UD" \
    --tag-specifications \
        "$(vdi_tagspec instance Name=vdi-builder-$BUILD_ID vdi-role=builder vdi-cluster=builder-$BUILD_ID)" \
        "$(vdi_tagspec volume vdi-cluster=builder-$BUILD_ID)" \
    --query 'Instances[0].InstanceId' --output text)"
log "builder $IID launched; build log (updated every 5 min): $S3/build.log"

terminate_builder() {
    aws ec2 terminate-instances --instance-ids "$IID" >/dev/null
    aws ec2 wait instance-terminated --instance-ids "$IID"
    log "builder $IID terminated"
}
# Any error or Ctrl-C from here on terminates the builder rather than leaving it to the
# dead-man (which only stops it, so it would sit there costing EBS indefinitely).
trap 'rc=$?; rm -f "$UD"; if [ "$rc" != 0 ]; then log "aborting (exit $rc): terminating builder"; terminate_builder; fi' EXIT
trap 'exit 130' INT TERM

# ── Wait for the build ──
deadline=$(( $(date +%s) + MAX_HOURS * 3600 + 900 ))
ssm_seen=no
while :; do
    if aws s3 ls "$S3/BUILD_OK" >/dev/null 2>&1; then result=ok; break; fi
    if aws s3 ls "$S3/BUILD_FAILED" >/dev/null 2>&1; then result=failed; break; fi
    state="$(aws ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].State.Name' --output text)"
    if [ "$ssm_seen" = no ] && [ "$(aws ssm describe-instance-information \
            --filters "Key=InstanceIds,Values=$IID" --query 'length(InstanceInformationList)' \
            --output text 2>/dev/null || echo 0)" = 1 ]; then
        ssm_seen=yes; log "builder registered with SSM"
    fi
    if [ "$state" = stopped ] || [ "$(date +%s)" -gt "$deadline" ]; then result=nomarker; break; fi
    log "building ($state)..."
    sleep 120
done

if [ "$result" != ok ]; then
    log "build did not succeed ($result). Tail of the log:"
    aws s3 cp "$S3/build.log" - 2>/dev/null | tail -40 >&2 || true
    exit 1   # the EXIT trap terminates the builder
fi

# ── Image the stopped builder ──
log "build OK; waiting for the builder to stop"
aws ec2 wait instance-stopped --instance-ids "$IID"
AMI="$(aws ec2 create-image --instance-id "$IID" --name "vdi-spark-rg-$BUILD_ID" \
    --description "VDI instrumented Spark; spark=$SPARK_SHA parquet=$PARQUET_SHA vdi=$VDI_SHA" \
    --tag-specifications \
        "$(vdi_tagspec image vdi-image=spark-rg vdi-build=$BUILD_ID spark-sha=$SPARK_SHA parquet-sha=$PARQUET_SHA vdi-sha=$VDI_SHA)" \
        "$(vdi_tagspec snapshot vdi-build=$BUILD_ID)" \
    --query ImageId --output text)"
log "creating $AMI"
while :; do
    st="$(aws ec2 describe-images --image-ids "$AMI" --query 'Images[0].State' --output text)"
    [ "$st" = available ] && break
    [ "$st" = failed ] || [ "$st" = error ] && die "image $AMI is $st"
    sleep 30
done
log "$AMI available"
terminate_builder
trap - EXIT
rm -f "$UD"
echo "$AMI"
