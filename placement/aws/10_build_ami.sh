#!/usr/bin/env bash
# Bake the placement AMI on one Graviton builder (m7g.2xlarge, arm64, Ubuntu 22.04):
#   /opt/spark                            forked Spark 3.5.5 (rowgroup-dev), Scala 2.13
#   /opt/jars/iceberg-spark-runtime.jar   iceberg-spark-runtime-3.5_2.13-1.8.1 (Maven Central)
#   /opt/jars/vdi-listener.jar            value-of-data-metric/spark-lineage-api (PlacementUsageListener)
#   /opt/vdi-place/s3-column-cache        this repo (refreshed again by 30_run.sh at run time)
#   /opt/vdi-place/venv                   Python 3.11 + pyarrow pandas numpy matplotlib (no DuckDB)
#   /etc/profile.d/vdi-place.sh           SPARK_HOME JAVA_HOME VDI_ICEBERG_JAR VDI_LISTENER_JAR ...
#
# BILLABLE: one m7g.2xlarge (~$0.33/hr) for ~0.3 h (Spark reused) or ~1.5-2.5 h (Spark
# built from source), then AMI snapshot storage (~$0.05/GB-month, ~10 GB).
#
# Spark, two ways (same artifact either way):
#   default      build from the fork exactly as spark-scale's node/build_ami.sh does
#                (parquet-java vod_rg -> ~/.m2, then make-distribution -Pscala-2.13
#                -Phadoop-cloud), from git-archive tarballs of COMMITTED refs.
#   VDI_SPARK_FROM_BUILD=<spark-scale build id>
#                reuse the dist tarball spark-scale's builder already backed up to
#                s3://$VDI_RESULTS_BUCKET/build/<id>/artifacts/ (read-only use of that prefix).
#
# The listener and this repo ship as WORKING-TREE tarballs (tracked + untracked, minus
# gitignored), because both have uncommitted work; the commit and dirty count are recorded
# in /opt/vdi-place/BUILD_INFO. Build sources go to s3://$VDI_RESULTS_BUCKET/placement-build/<id>/.
#
# Usage: aws-vault exec vdi -- ./10_build_ami.sh
# Env overrides: VDI_SPARK_FROM_BUILD, VDI_SPARK_REPO, VDI_PARQUET_REPO, VDI_SPARK_REF
#   (rowgroup-dev), VDI_PARQUET_REF (vod_rg), VDI_LISTENER_DIR, VDI_BUILD_MAX_HOURS (default 4)
set -euo pipefail
AWS_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$AWS_DIR/env.sh"
. "$AWS_DIR/lib.sh"
vdi_check_account

PLACE_REPO="$(git -C "$AWS_DIR" rev-parse --show-toplevel)"
LISTENER_DIR="${VDI_LISTENER_DIR:-$HOME/value_of_data/value-of-data-metric/spark-lineage-api}"
SPARK_FROM_BUILD="${VDI_SPARK_FROM_BUILD:-}"
MAX_HOURS="${VDI_BUILD_MAX_HOURS:-4}"
TYPE=m7g.2xlarge
[ -f "$LISTENER_DIR/pom.xml" ] || die "no listener at $LISTENER_DIR (set VDI_LISTENER_DIR)"
[ -f "$LISTENER_DIR/src/main/scala/PlacementUsageListener.scala" ] \
    || log "WARNING: $LISTENER_DIR has no src/main/scala/PlacementUsageListener.scala; the builder fails unless the class is defined elsewhere"

SG_ID="$(vdi_sg_id)";        [ -n "$SG_ID" ]  || die "no security group; run 00_network.sh"
SUBNET="$(vdi_subnet_id)";   [ -n "$SUBNET" ] || die "no default subnet in $VDI_AZ"
BASE_AMI="$(vdi_ubuntu_arm64_ami)"
ROOT_DEV="$(aws ec2 describe-images --image-ids "$BASE_AMI" --query 'Images[0].RootDeviceName' --output text)"
BUILD_ID="$(date -u +%Y%m%d-%H%M%S)"
S3="$VDI_PLACE_BUILD_S3/$BUILD_ID"
price="$(vdi_price $TYPE)"

TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT
if [ -n "$SPARK_FROM_BUILD" ]; then
    SPARK_MODE=reuse
    SPARK_SRC="s3://$VDI_RESULTS_BUCKET/build/$SPARK_FROM_BUILD"
    aws s3 ls "$SPARK_SRC/BUILD_OK" >/dev/null || die "$SPARK_SRC has no BUILD_OK"
    aws s3 ls "$SPARK_SRC/artifacts/" | grep -q 'spark-.*-bin-vod-rg\.tgz' || die "no Spark dist tarball under $SPARK_SRC/artifacts/"
    SPARK_SHA="see spark-scale BUILD_INFO ($SPARK_FROM_BUILD)" PARQUET_SHA="$SPARK_SHA"
    spark_line="spark        reused from spark-scale build $SPARK_FROM_BUILD"
else
    SPARK_MODE=source
    SPARK_SRC="$S3/src"
    SPARK_REPO="${VDI_SPARK_REPO:-$HOME/value_of_data/spark}"
    PARQUET_REPO="${VDI_PARQUET_REPO:-$HOME/value_of_data/parquet-java}"
    # rowgroup-dev (multiscan merged, = spark-scale build #8's Spark) and vod_rg (capture
    # fix merged). The placement harness also needs RowGroupMetricsRegistry.keys to be
    # thread-safe (TPC-DS q6), in rowgroup-dev since e9174562ee3. The guard below refuses a
    # ref without it.
    SPARK_REF="${VDI_SPARK_REF:-rowgroup-dev}"
    PARQUET_REF="${VDI_PARQUET_REF:-vod_rg}"
    SPARK_SHA="$(git -C "$SPARK_REPO" rev-parse "$SPARK_REF^{commit}")"
    PARQUET_SHA="$(git -C "$PARQUET_REPO" rev-parse "$PARQUET_REF^{commit}")"
    git -C "$SPARK_REPO" show "$SPARK_SHA:sql/core/src/main/scala/org/apache/spark/sql/execution/datasources/parquet/RowGroupMetricsRegistry.scala" \
        | grep -q 'synchronizedList' \
        || die "Spark $SPARK_REF ($SPARK_SHA) lacks the thread-safe RowGroupMetricsRegistry.keys fix (commit it on rowgroup-dev-placement and fast-forward rowgroup-dev, or set VDI_SPARK_REF)"
    spark_line="spark        $SPARK_REF $SPARK_SHA (built from source)
  parquet-java $PARQUET_REF $PARQUET_SHA"
fi

vdi_pack_tree "$LISTENER_DIR" "$TMPD/listener.tar.gz" ':!target' ':!*/target/*'
vdi_pack_tree "$PLACE_REPO" "$TMPD/s3-column-cache.tar.gz" ':!data/spark' ':!run/results' ':!aws'

vdi_confirm "Build placement AMI $BUILD_ID on one $TYPE (\$$price/hr; dead-man stop after ${MAX_HOURS}h):
  $spark_line
  listener     $(sed -n 's/^commit=//p' "$TMPD/listener.tar.gz.info") (+$(sed -n 's/^uncommitted_paths=//p' "$TMPD/listener.tar.gz.info") uncommitted paths)  $LISTENER_DIR
  harness      $(sed -n 's/^commit=//p' "$TMPD/s3-column-cache.tar.gz.info") (+$(sed -n 's/^uncommitted_paths=//p' "$TMPD/s3-column-cache.tar.gz.info") uncommitted paths)  $PLACE_REPO
  base AMI     $BASE_AMI (Ubuntu 22.04 arm64)
  sources to   $S3/src/"

# ── Ship sources ──
log "uploading source archives to $S3/src/"
for f in listener.tar.gz listener.tar.gz.info s3-column-cache.tar.gz s3-column-cache.tar.gz.info; do
    aws s3 cp "$TMPD/$f" "$S3/src/$f" --quiet
done
if [ "$SPARK_MODE" = source ]; then
    git -C "$SPARK_REPO"   archive --format=tar.gz "$SPARK_SHA"   | aws s3 cp - "$S3/src/spark.tar.gz" --quiet
    git -C "$PARQUET_REPO" archive --format=tar.gz "$PARQUET_SHA" | aws s3 cp - "$S3/src/parquet-java.tar.gz" --quiet
fi

# ── Launch the builder ──
UD="$TMPD/userdata.sh"
{
    echo "#!/bin/bash"
    echo "VDI_BUCKET=$VDI_RESULTS_BUCKET VDI_BUILD_ID=$BUILD_ID VDI_REGION=$VDI_AWS_REGION"
    echo "VDI_BUILD_S3=$S3 VDI_MAX_MIN=$((MAX_HOURS * 60)) VDI_DATA_BUCKET=$VDI_PLACE_DATA_BUCKET"
    echo "VDI_SPARK_MODE=$SPARK_MODE VDI_SPARK_SRC=$SPARK_SRC"
    echo "VDI_SPARK_SHA='$SPARK_SHA' VDI_PARQUET_SHA='$PARQUET_SHA'"
    echo "export VDI_BUCKET VDI_BUILD_ID VDI_REGION VDI_BUILD_S3 VDI_MAX_MIN VDI_DATA_BUCKET VDI_SPARK_MODE VDI_SPARK_SRC VDI_SPARK_SHA VDI_PARQUET_SHA"
    tail -n +2 "$AWS_DIR/node/build_ami.sh"
} > "$UD"
[ "$(wc -c < "$UD")" -lt 16000 ] || die "user-data is over EC2's 16 KB limit; shorten node/build_ami.sh"

IID="$(aws ec2 run-instances --image-id "$BASE_AMI" --instance-type $TYPE --count 1 \
    --subnet-id "$SUBNET" --security-group-ids "$SG_ID" --key-name "$VDI_KEY_PAIR_NAME" \
    --iam-instance-profile "Name=$VDI_INSTANCE_PROFILE" \
    --metadata-options HttpTokens=required,HttpPutResponseHopLimit=1 \
    --instance-initiated-shutdown-behavior stop \
    --block-device-mappings "DeviceName=$ROOT_DEV,Ebs={VolumeSize=100,VolumeType=gp3,DeleteOnTermination=true}" \
    --user-data "file://$UD" \
    --tag-specifications \
        "$(vdi_tagspec instance Name=${VDI_PLACE_NAME_PREFIX}builder-$BUILD_ID vdi-place-run=builder-$BUILD_ID vdi-place-role=builder)" \
        "$(vdi_tagspec volume vdi-place-run=builder-$BUILD_ID)" \
    --query 'Instances[0].InstanceId' --output text)"
log "builder $IID launched; build log (updated every minute): $S3/build.log"

terminate_builder() {
    vdi_place_guard "builder-$BUILD_ID" "$IID"
    aws ec2 terminate-instances --instance-ids "$IID" >/dev/null
    aws ec2 wait instance-terminated --instance-ids "$IID"
    log "builder $IID terminated"
}
# Any error or Ctrl-C from here on terminates the builder rather than leaving it to the
# dead-man (which only stops it, so its EBS would keep billing).
trap 'rc=$?; rm -rf "$TMPD"; if [ "$rc" != 0 ]; then log "aborting (exit $rc): terminating builder"; terminate_builder; fi' EXIT
trap 'exit 130' INT TERM

# ── Wait for the build ──
deadline=$(( $(date +%s) + MAX_HOURS * 3600 + 900 ))
ssm_seen=no
while :; do
    if aws s3 ls "$S3/BUILD_OK" >/dev/null 2>&1; then result=ok; break; fi
    if aws s3 ls "$S3/BUILD_FAILED" >/dev/null 2>&1; then result=failed; break; fi
    state="$(aws ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].State.Name' --output text)"
    if [ "$ssm_seen" = no ] && vdi_ssm_online "$IID"; then ssm_seen=yes; log "builder registered with SSM"; fi
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
AMI="$(aws ec2 create-image --instance-id "$IID" --name "${VDI_PLACE_NAME_PREFIX}$BUILD_ID" \
    --description "VDI placement node; spark=$SPARK_MODE build=$BUILD_ID" \
    --tag-specifications \
        "$(vdi_tagspec image Name=${VDI_PLACE_NAME_PREFIX}$BUILD_ID vdi-image=placement vdi-place-build=$BUILD_ID)" \
        "$(vdi_tagspec snapshot vdi-place-build=$BUILD_ID)" \
    --query ImageId --output text)"
log "creating $AMI"
while :; do
    st="$(aws ec2 describe-images --image-ids "$AMI" --query 'Images[0].State' --output text)"
    [ "$st" = available ] && break
    if [ "$st" = failed ] || [ "$st" = error ]; then die "image $AMI is $st"; fi
    sleep 30
done
log "$AMI available"
terminate_builder
trap - EXIT
rm -rf "$TMPD"
echo "$AMI"
