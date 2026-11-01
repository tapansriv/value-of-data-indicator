#!/bin/bash
# Runs ONCE on the AMI builder as root, as EC2 user-data. 10_build_ami.sh prepends:
#   VDI_BUCKET VDI_BUILD_ID VDI_REGION VDI_MAX_MIN VDI_SPARK_SHA VDI_PARQUET_SHA VDI_VDI_SHA
# Sources arrive as git-archive tarballs in s3://$VDI_BUCKET/build/$VDI_BUILD_ID/src/, so the
# build is pinned to exact commits and needs no GitHub access.
#
# Ends by writing BUILD_OK or BUILD_FAILED next to the sources and powering off. The
# builder's shutdown behaviour is "stop", so 10_build_ami.sh can image the stopped disk.
set -euo pipefail

# Run the build as its own systemd service, outside cloud-init's cgroup, so nothing that
# happens to cloud-init can reach it. (Added while chasing the "power-off at +30 min",
# which turned out to be finish() itself: see the note there.)
if [ "${VDI_UNDER_SYSTEMD:-0}" != 1 ]; then
    cp "$0" /root/vdi_build.sh
    systemd-run --unit=vdi-build --property=TimeoutStartSec=infinity --setenv=VDI_UNDER_SYSTEMD=1 \
        --setenv=VDI_BUCKET="$VDI_BUCKET" --setenv=VDI_BUILD_ID="$VDI_BUILD_ID" \
        --setenv=VDI_REGION="$VDI_REGION" --setenv=VDI_MAX_MIN="$VDI_MAX_MIN" \
        --setenv=VDI_DATA_BUCKET="$VDI_DATA_BUCKET" --setenv=VDI_SPARK_SHA="$VDI_SPARK_SHA" \
        --setenv=VDI_PARQUET_SHA="$VDI_PARQUET_SHA" --setenv=VDI_VDI_SHA="$VDI_VDI_SHA" \
        /bin/bash /root/vdi_build.sh
    exit 0
fi

exec >/var/log/vdi-build.log 2>&1
set -x

S3="s3://$VDI_BUCKET/build/$VDI_BUILD_ID"
SRC=/root/src
DIST_NAME=vod-rg
export HOME=/root
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64
export DEBIAN_FRONTEND=noninteractive

finish() {
    local rc=$?
    set +e
    # The AWS CLI (Python) dies at startup if the working directory no longer exists. The
    # cleanup below deletes the smoke-test directory the script was in, which silently
    # killed these uploads on builds 1-4: BUILD_OK never landed, and the laptop terminated
    # three good builders.
    cd /
    if [ -x /usr/local/bin/aws ]; then
        aws s3 cp /var/log/vdi-build.log "$S3/build.log" --quiet
        if [ $rc = 0 ]; then marker=BUILD_OK; else marker=BUILD_FAILED; fi
        echo "exit=$rc $(date -u +%FT%TZ)" | aws s3 cp - "$S3/$marker" --quiet
    fi
    echo "finish: exit=$rc at $(date -u +%FT%TZ)"
    if [ $rc = 0 ]; then
        # Leave no builder state in the image: cloud-init re-runs user-data on every
        # new instance anyway, and this drops the builder's copy of it.
        cloud-init clean --logs
    fi
    shutdown -h now
}
trap finish EXIT
# Name the signal if something terminates the build, with a process listing, so an
# unexplained stop leaves evidence. (EXIT then runs finish as usual.)
on_signal() {
    set +x
    echo "!!! received SIG$1 at $(date -u +%FT%TZ)"
    ps -eo pid,ppid,user,etime,cmd --forest | grep -v ' \[' | tail -60
    exit $((128 + $2))
}
trap 'on_signal TERM 15' TERM
trap 'on_signal HUP 1' HUP
trap 'on_signal INT 2' INT

# No package changes behind our back: disabled here, so also disabled in the AMI. No package
# may change on a node during a multi-day benchmark.
systemctl disable --now unattended-upgrades.service apt-daily.timer apt-daily-upgrade.timer || true
systemctl stop apt-daily.service apt-daily-upgrade.service || true
# Snap refreshes would restart the SSM agent and add background load mid-run.
snap refresh --hold=forever || true

# Dead-man's switch: power off (= stop) after VDI_MAX_MIN even if the build hangs.
systemd-run --unit="vdi-deadman-$(date +%s)" --on-active="${VDI_MAX_MIN}min" /bin/systemctl poweroff

# ── Packages ──────────────────────────────────────────────────────────────
apt-get -o DPkg::Lock::Timeout=600 update -q
apt-get -o DPkg::Lock::Timeout=600 install -y -q openjdk-17-jdk-headless maven thrift-compiler \
    unzip curl tmux python3 python3-pip jq
curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip -o /tmp/awscli.zip
unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install
aws --version

# Every 60 s: the build log, plus diagnostics (journal, disk, memory, SSM agent log), so
# progress is visible and an unexplained power-off leaves its last minute behind.
( set +e +x
  while sleep 60; do
    aws s3 cp /var/log/vdi-build.log "$S3/build.log" --quiet
    { echo "== $(date -u +%FT%TZ) uptime: $(uptime)"; df -h /; free -m
      echo "== journal"; journalctl -b --no-pager -n 300
      echo "== ssm agent"; tail -n 80 /var/log/amazon/ssm/amazon-ssm-agent.log 2>/dev/null
    } 2>&1 | aws s3 cp - "$S3/diag.txt" --quiet
  done ) &

# ── Sources ───────────────────────────────────────────────────────────────
mkdir -p "$SRC"/{spark,parquet-java,vdi}
for r in spark parquet-java vdi; do
    aws s3 cp "$S3/src/$r.tar.gz" - --quiet | tar xz -C "$SRC/$r"
done

# ── 1. Thrift: not built from source ──────────────────────────────────────
# With -pl parquet-hadoop nothing invokes thrift (parquet-format-structures 1.13.1 comes
# from Maven Central). jammy's thrift-compiler (0.16.0) is installed above only as
# insurance; record its version.
thrift --version || true

# ── 2. parquet-java @ vod_rg -> ~/.m2 (same coordinates as upstream 1.13.1) ──
cd "$SRC/parquet-java"
MAVEN_OPTS="--add-opens java.base/java.lang=ALL-UNNAMED" \
    mvn -B -q clean install -pl parquet-hadoop -DskipTests

# ── 3. Spark @ rowgroup-dev, Scala 2.13 ───────────────────────────────────
# make-distribution (which runs its own `clean package`) produces the SPARK_HOME tarball;
# -Phadoop-cloud bundles hadoop-aws and the AWS SDK bundle at the versions Hadoop 3.3.4
# pins. Then install only sql/core and its upstream modules into ~/.m2, without clean,
# for the listener build (step 4): one full Spark build instead of two.
cd "$SRC/spark"
./dev/change-scala-version.sh 2.13
./dev/make-distribution.sh --name "$DIST_NAME" --tgz -Pscala-2.13 -Phadoop-cloud
./build/mvn -B -DskipTests -Pscala-2.13 -Phadoop-cloud install -pl sql/core -am
TGZ="$(ls "$SRC"/spark/spark-*-bin-$DIST_NAME.tgz)"
tar xzf "$TGZ" -C /opt
ln -sfn "/opt/$(basename "$TGZ" .tgz)" /opt/spark
J=/opt/spark/jars

# Guard against the trap in REVISION_SCALEUP.md §3: a stock SPARK_HOME would make every
# variant collapse onto vanilla. Fail the build unless the instrumentation is really there.
# (unzip with a member name, not `unzip -l | grep -q`: grep -q closes the pipe early, unzip
# dies of SIGPIPE, and pipefail would fail a good build)
for c in RowGroupAccumulator RowGroupMetricsRegistry; do
    unzip -l $J/spark-sql_2.13-*.jar "org/apache/spark/sql/execution/datasources/parquet/$c.class" >/dev/null
done
cmp $J/parquet-hadoop-1.13.1.jar \
    /root/.m2/repository/org/apache/parquet/parquet-hadoop/1.13.1/parquet-hadoop-1.13.1.jar
ls $J/hadoop-aws-3.3.4.jar $J/aws-java-sdk-bundle-*.jar
/opt/spark/bin/spark-submit --version 2>&1 | tee /tmp/spark-version.txt
grep -q 'Scala version 2.13.8' /tmp/spark-version.txt

# ── 4. Listener jars (the four configurations in the matrix) ──────────────
mkdir -p /opt/vdi/jars
cd "$SRC/vdi/spark-lineage-api"
declare -A VARIANT_SRC=(
    [vanilla]=LineageAPI_vanilla.scala
    [bare]=LineageAPI_bare.scala
    [cols]=LineageAPI.scala
    [rowgroup]=LineageAPI_rgs.scala
)
for v in vanilla bare cols rowgroup; do
    cp "listener_versions_new/${VARIANT_SRC[$v]}" src/main/scala/LineageAPI.scala
    # Pin to the Scala Spark was built with (2.13.8, Spark's pom.xml); the listener pom
    # says 2.13.16, and 2.13 is not forward binary compatible.
    mvn -B -q -Dscala.version=2.13.8 clean package
    cp target/spark-rowgroup-listener-1.0.0.jar "/opt/vdi/jars/$v.jar"
done

# ── 5. Runtime config baked into the image ────────────────────────────────
# Infrastructure settings only, identical on every node and size. Experiment settings
# (executor sizing, speculation, AQE, reuse) are passed explicitly by run_matrix.sh so
# they are recorded with each run.
cat > /opt/spark/conf/spark-defaults.conf <<EOF
spark.hadoop.fs.s3a.aws.credentials.provider  org.apache.hadoop.fs.s3a.auth.IAMInstanceCredentialsProvider
spark.hadoop.fs.s3a.endpoint                  s3.$VDI_REGION.amazonaws.com
spark.hadoop.fs.s3a.experimental.input.fadvise random
spark.hadoop.fs.s3a.connection.maximum        200
spark.hadoop.fs.s3a.threads.max               64
spark.speculation                             false
EOF
cat > /opt/spark/conf/spark-env.sh <<'EOF'
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64
export SPARK_LOCAL_DIRS=/home/ubuntu/spark-local
export SPARK_LOG_DIR=/home/ubuntu/spark-logs
export SPARK_WORKER_DIR=/home/ubuntu/spark-work
# SPARK_MASTER_HOST / SPARK_LOCAL_IP are appended per instance by boot.sh
EOF

cat > /opt/vdi/BUILD_INFO <<EOF
build_id=$VDI_BUILD_ID
built_at=$(date -u +%FT%TZ)
spark_sha=$VDI_SPARK_SHA
parquet_java_sha=$VDI_PARQUET_SHA
value_of_data_metric_sha=$VDI_VDI_SHA
spark_dist=$(basename "$TGZ")
java=$(java -version 2>&1 | head -1)
arch=$(uname -m)
EOF
cat /opt/vdi/BUILD_INFO

# ── 6. Smoke test: local mode, real data, real S3 write ───────────────────
# Exercises the instance role over s3a (read the dataset, write the results bucket),
# hadoop-aws on the classpath, the listener jar, and row-group capture end to end, on
# the two tiny TPC-H tables. Cheap; catches a broken image before any cluster exists.
mkdir -p /root/smoke/q
echo "select n_name, r_name from nation, region where n_regionkey = r_regionkey" \
    > /root/smoke/q/q_smoke.sql
for v in vanilla bare cols rowgroup; do
    mkdir -p "/root/smoke/$v" && cd "/root/smoke/$v"
    /opt/spark/bin/spark-submit --master 'local[4]' --driver-memory 8g --class LineageAPI \
        "/opt/vdi/jars/$v.jar" \
        parquet "s3a://${VDI_DATA_BUCKET:-vod-tpch-1tb}/" /root/smoke/q \
        "s3a://$VDI_BUCKET/build/$VDI_BUILD_ID/smoke/usage_logs/$v" my_catalog
    cat "spark_internal_listener_${v}_results.csv"
    # runtime > 0 and listener_timeout = false
    awk -F, 'NR==2 { exit !($3 > 0 && $4 == "false") }' "spark_internal_listener_${v}_results.csv"
    aws s3 cp "spark_internal_listener_${v}_results.csv" "$S3/smoke/" --quiet
done
# The listeners that log usage must have written to S3
for v in cols rowgroup; do
    aws s3 ls --recursive "$S3/smoke/usage_logs/$v/" | grep '\.parquet$' >/dev/null
done

# ── Backup of the artifacts, then shrink the image ────────────────────────
aws s3 cp "$TGZ" "$S3/artifacts/" --quiet
aws s3 cp /opt/vdi/jars "$S3/artifacts/jars/" --recursive --quiet
aws s3 cp /opt/vdi/BUILD_INFO "$S3/artifacts/" --quiet

cd /   # the cleanup below deletes the directory the smoke test left us in
chown -R ubuntu:ubuntu /opt/spark/ "/opt/$(basename "$TGZ" .tgz)" /opt/vdi
# The smoke test ran as root with SPARK_LOCAL_DIRS etc. under /home/ubuntu; don't bake those
# root-owned dirs into the image (boot.sh creates them, owned by ubuntu).
rm -rf "$SRC" /root/.m2 /root/smoke /tmp/aws /tmp/awscli.zip \
    /home/ubuntu/spark-local /home/ubuntu/spark-logs /home/ubuntu/spark-work
apt-get clean
