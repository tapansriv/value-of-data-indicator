#!/bin/bash
# Runs ONCE on the placement AMI builder as root, as EC2 user-data. 10_build_ami.sh prepends:
#   VDI_BUCKET VDI_BUILD_ID VDI_REGION VDI_BUILD_S3 VDI_MAX_MIN VDI_DATA_BUCKET
#   VDI_SPARK_MODE (source|reuse) VDI_SPARK_SRC VDI_SPARK_SHA VDI_PARQUET_SHA
# Sources arrive as tarballs in $VDI_BUILD_S3/src/ (no GitHub access needed). Ends by
# writing BUILD_OK or BUILD_FAILED there and powering off; the builder's shutdown
# behaviour is "stop", so 10_build_ami.sh can image the stopped disk.
# Keep this file well under 15 KB: it travels as user-data (16 KB limit).
set -euo pipefail

# Run as a systemd service, outside cloud-init's cgroup (spark-scale lesson).
if [ "${VDI_UNDER_SYSTEMD:-0}" != 1 ]; then
    cp "$0" /root/vdi_build.sh
    args=()
    for v in VDI_BUCKET VDI_BUILD_ID VDI_REGION VDI_BUILD_S3 VDI_MAX_MIN VDI_DATA_BUCKET \
             VDI_SPARK_MODE VDI_SPARK_SRC VDI_SPARK_SHA VDI_PARQUET_SHA; do
        args+=(--setenv="$v=${!v}")
    done
    systemd-run --unit=vdi-place-build --property=TimeoutStartSec=infinity \
        --setenv=VDI_UNDER_SYSTEMD=1 "${args[@]}" /bin/bash /root/vdi_build.sh
    exit 0
fi

exec >/var/log/vdi-build.log 2>&1
set -x

S3="$VDI_BUILD_S3"
SRC=/root/src
DIST_NAME=vod-rg
ICEBERG=iceberg-spark-runtime-3.5_2.13-1.8.1.jar
ICEBERG_URL="https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.13/1.8.1/$ICEBERG"
PLACE=/opt/vdi-place
export HOME=/root
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64
export DEBIAN_FRONTEND=noninteractive

finish() {
    local rc=$?
    set +e
    cd /   # the AWS CLI dies at startup if the cwd was deleted (spark-scale builds 1-4)
    if [ -x /usr/local/bin/aws ]; then
        aws s3 cp /var/log/vdi-build.log "$S3/build.log" --quiet
        if [ $rc = 0 ]; then marker=BUILD_OK; else marker=BUILD_FAILED; fi
        echo "exit=$rc $(date -u +%FT%TZ)" | aws s3 cp - "$S3/$marker" --quiet
    fi
    echo "finish: exit=$rc at $(date -u +%FT%TZ)"
    [ $rc = 0 ] && cloud-init clean --logs
    shutdown -h now
}
trap finish EXIT
on_signal() { set +x; echo "!!! received SIG$1 at $(date -u +%FT%TZ)"; ps -eo pid,ppid,etime,cmd --forest | tail -60; exit $((128 + $2)); }
trap 'on_signal TERM 15' TERM
trap 'on_signal HUP 1' HUP

# No package or snap changes behind our back, here or in the image.
systemctl disable --now unattended-upgrades.service apt-daily.timer apt-daily-upgrade.timer || true
systemctl stop apt-daily.service apt-daily-upgrade.service || true
snap refresh --hold=forever || true

# Dead-man's switch: power off (= stop) even if the build hangs.
systemd-run --unit="vdi-deadman-$(date +%s)" --on-active="${VDI_MAX_MIN}min" /bin/systemctl poweroff

# ── Packages ──
apt-get -o DPkg::Lock::Timeout=600 update -q
apt-get -o DPkg::Lock::Timeout=600 install -y -q openjdk-17-jdk-headless maven unzip curl \
    tmux jq software-properties-common
# Python 3.11 (jammy ships 3.10)
add-apt-repository -y ppa:deadsnakes/ppa
apt-get -o DPkg::Lock::Timeout=600 install -y -q python3.11 python3.11-venv python3.11-dev
curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip -o /tmp/awscli.zip
unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install
aws --version

( set +e +x
  while sleep 60; do
    aws s3 cp /var/log/vdi-build.log "$S3/build.log" --quiet
    { echo "== $(date -u +%FT%TZ) $(uptime)"; df -h /; free -m; journalctl -b --no-pager -n 200; } 2>&1 \
        | aws s3 cp - "$S3/diag.txt" --quiet
  done ) &

# ── Sources ──
mkdir -p "$SRC"/{listener,repo} "$PLACE" /opt/jars
aws s3 cp "$S3/src/listener.tar.gz" - --quiet | tar xz -C "$SRC/listener"
aws s3 cp "$S3/src/s3-column-cache.tar.gz" - --quiet | tar xz -C "$SRC/repo"

# ── 1. Spark ──
if [ "$VDI_SPARK_MODE" = source ]; then
    mkdir -p "$SRC"/{spark,parquet-java}
    for r in spark parquet-java; do
        aws s3 cp "$VDI_SPARK_SRC/$r.tar.gz" - --quiet | tar xz -C "$SRC/$r"
    done
    # Identical to spark-scale's node/build_ami.sh steps 2-3 (minus the sql/core install,
    # which the listener does not need: it compiles against spark-sql from Maven Central).
    cd "$SRC/parquet-java"
    MAVEN_OPTS="--add-opens java.base/java.lang=ALL-UNNAMED" \
        mvn -B -q clean install -pl parquet-hadoop -DskipTests
    cd "$SRC/spark"
    ./dev/change-scala-version.sh 2.13
    ./dev/make-distribution.sh --name "$DIST_NAME" --tgz -Pscala-2.13 -Phadoop-cloud
    TGZ="$(ls "$SRC"/spark/spark-*-bin-$DIST_NAME.tgz)"
    SPARK_INFO="built from source: spark=$VDI_SPARK_SHA parquet-java=$VDI_PARQUET_SHA"
else
    mkdir -p "$SRC/dist"
    name="$(aws s3 ls "$VDI_SPARK_SRC/artifacts/" | awk '{print $4}' | grep "^spark-.*-bin-$DIST_NAME\.tgz$" | head -1)"
    aws s3 cp "$VDI_SPARK_SRC/artifacts/$name" "$SRC/dist/$name" --quiet
    aws s3 cp "$VDI_SPARK_SRC/artifacts/BUILD_INFO" "$SRC/dist/SPARK_BUILD_INFO" --quiet
    TGZ="$SRC/dist/$name"
    SPARK_INFO="reused from $VDI_SPARK_SRC/artifacts/$name"
fi
tar xzf "$TGZ" -C /opt
ln -sfn "/opt/$(basename "$TGZ" .tgz)" /opt/spark
J=/opt/spark/jars
# Fail unless the instrumentation is really in the dist (REVISION_SCALEUP.md §3 trap).
for c in RowGroupAccumulator RowGroupMetricsRegistry; do
    unzip -l $J/spark-sql_2.13-*.jar "org/apache/spark/sql/execution/datasources/parquet/$c.class" >/dev/null
done
/opt/spark/bin/spark-submit --version 2>&1 | tee /tmp/spark-version.txt
grep -q 'Scala version 2.13.8' /tmp/spark-version.txt
grep -q 'version 3.5.5' /tmp/spark-version.txt

# ── 2. Iceberg runtime (checksum from Maven Central) ──
curl -fsSL "$ICEBERG_URL" -o "/opt/jars/$ICEBERG"
echo "$(curl -fsSL "$ICEBERG_URL.sha1")  /opt/jars/$ICEBERG" | sha1sum -c -
ln -sfn "/opt/jars/$ICEBERG" /opt/jars/iceberg-spark-runtime.jar

# ── 3. Listener ──
# Pin Scala to the version Spark was built with (2.13.8); the pom says 2.13.16 and 2.13 is
# not forward binary compatible (spark-scale build lesson).
# Only PlacementUsageListener: LineageAPI.scala (spark-scale's listener) imports the fork's
# RowGroupMetricsRegistry, which is not in Maven Central's spark-sql, and placement does
# not use it. PlacementUsageListener compiles against stock spark-sql 3.5.5.
cd "$SRC/listener"
rm -f src/main/scala/LineageAPI.scala
mvn -B -q -DskipTests -Dscala.version=2.13.8 package
LJAR="$(ls target/*.jar | grep -v -e '^target/original-' -e 'sources' -e 'javadoc' | head -1)"
[ -f target/spark-rowgroup-listener-1.0.0.jar ] && LJAR=target/spark-rowgroup-listener-1.0.0.jar
unzip -l "$LJAR" 'vdi/placement/PlacementUsageListener.class' >/dev/null
cp "$LJAR" /opt/jars/vdi-listener.jar

# ── 4. Python ──
python3.11 -m venv "$PLACE/venv"
"$PLACE/venv/bin/pip" install -q -U pip wheel
# Only what the Spark placement path imports. No DuckDB (the experiment must not use it)
# and no sqlglot (columns come from Spark's plan); requirements.txt lists both for the
# original harness, so it is deliberately not installed here.
"$PLACE/venv/bin/pip" install -q pyarrow pandas numpy matplotlib boto3
"$PLACE/venv/bin/python" -c 'import sys, pyarrow, pandas, numpy, matplotlib; assert sys.version_info >= (3, 11)'
"$PLACE/venv/bin/python" -c 'import importlib.util as u; assert u.find_spec("duckdb") is None, "duckdb must not be installed"'
"$PLACE/venv/bin/pip" freeze > "$PLACE/pip-freeze.txt"

# ── 5. Harness repo ──
mkdir -p "$PLACE/s3-column-cache"
cp -a "$SRC/repo/." "$PLACE/s3-column-cache/"
aws s3 cp "$S3/src/s3-column-cache.tar.gz.info" "$PLACE/s3-column-cache/REPO_INFO" --quiet

# ── 6. Environment and Spark config ──
PY4J="$(ls /opt/spark/python/lib/py4j-*-src.zip)"
cat > /etc/profile.d/vdi-place.sh <<EOF
# VDI placement node environment (written by node/build_ami.sh, build $VDI_BUILD_ID)
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64
export SPARK_HOME=/opt/spark
export VDI_ICEBERG_JAR=/opt/jars/iceberg-spark-runtime.jar
export VDI_LISTENER_JAR=/opt/jars/vdi-listener.jar
export VDI_PLACE_DATA_BUCKET=$VDI_DATA_BUCKET
export PYSPARK_PYTHON=$PLACE/venv/bin/python
export PYSPARK_DRIVER_PYTHON=$PLACE/venv/bin/python
export PYTHONPATH=/opt/spark/python:$PY4J\${PYTHONPATH:+:\$PYTHONPATH}
export PATH=$PLACE/venv/bin:/opt/spark/bin:\$PATH
export AWS_REGION=$VDI_REGION AWS_DEFAULT_REGION=$VDI_REGION
EOF
cat > /opt/spark/conf/spark-defaults.conf <<EOF
spark.hadoop.fs.s3a.aws.credentials.provider  org.apache.hadoop.fs.s3a.auth.IAMInstanceCredentialsProvider
spark.hadoop.fs.s3a.endpoint                  s3.$VDI_REGION.amazonaws.com
spark.speculation                             false
EOF
echo "export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64" > /opt/spark/conf/spark-env.sh

cat > "$PLACE/BUILD_INFO" <<EOF
build_id=$VDI_BUILD_ID
built_at=$(date -u +%FT%TZ)
spark=$SPARK_INFO
spark_dist=$(basename "$TGZ")
iceberg=$ICEBERG
listener_jar=$(basename "$LJAR")
python=$("$PLACE/venv/bin/python" --version 2>&1)
java=$(java -version 2>&1 | head -1)
arch=$(uname -m)
--- listener source
$(aws s3 cp "$S3/src/listener.tar.gz.info" - --quiet)
--- harness source
$(cat "$PLACE/s3-column-cache/REPO_INFO")
EOF
[ -f "$SRC/dist/SPARK_BUILD_INFO" ] && { echo "--- spark-scale BUILD_INFO"; cat "$SRC/dist/SPARK_BUILD_INFO"; } >> "$PLACE/BUILD_INFO"
cat "$PLACE/BUILD_INFO"

# ── 7. Smoke test: PySpark local mode + Iceberg hadoop catalog + listener on the classpath,
#       and the instance role can list the data bucket ──
aws s3 ls "s3://$VDI_DATA_BUCKET/" > /tmp/data-ls.txt; head -3 /tmp/data-ls.txt
mkdir -p /root/smoke && cd /root/smoke
cat > smoke.py <<'EOF'
import os
from pyspark.sql import SparkSession
jars = os.environ["VDI_ICEBERG_JAR"] + "," + os.environ["VDI_LISTENER_JAR"]
spark = (SparkSession.builder.master("local[2]").config("spark.jars", jars)
         .config("spark.ui.showConsoleProgress", "false")
         .config("spark.local.dir", "/root/smoke/tmp")
         .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
         .config("spark.sql.catalog.smoke", "org.apache.iceberg.spark.SparkCatalog")
         .config("spark.sql.catalog.smoke.type", "hadoop")
         .config("spark.sql.catalog.smoke.warehouse", "file:///root/smoke/wh").getOrCreate())
spark.sql("CREATE TABLE smoke.db.t (k int, v double) USING iceberg")
spark.sql("INSERT INTO smoke.db.t VALUES (1, 0.5), (2, 1.5)")
assert spark.sql("SELECT sum(v) s FROM smoke.db.t").collect()[0].s == 2.0
# Data Value compaction path (SparkVDI.compact): Iceberg's Java actions API
J = spark._jvm.org.apache.iceberg.spark
t = J.Spark3Util.loadIcebergTable(spark._jsparkSession, "smoke.db.t")
J.actions.SparkActions.get(spark._jsparkSession).rewriteDataFiles(t).option("rewrite-all", "true").execute()
assert spark.sql("SELECT count(*) n FROM smoke.db.t.files").collect()[0].n == 1
# the context class loader (which holds spark.jars), not py4j's own
spark._jvm.org.apache.spark.util.Utils.classForName("vdi.placement.PlacementUsageListener", True, False)
print("SMOKE OK", spark.version)
spark.stop()
EOF
( . /etc/profile.d/vdi-place.sh && python smoke.py ) 2>&1 | tee smoke.log
grep -q 'SMOKE OK 3.5.5' smoke.log

# ── Backup of the artifacts, then shrink the image ──
aws s3 cp /opt/jars "$S3/artifacts/jars/" --recursive --quiet
aws s3 cp "$PLACE/BUILD_INFO" "$S3/artifacts/" --quiet
aws s3 cp "$PLACE/pip-freeze.txt" "$S3/artifacts/" --quiet
[ "$VDI_SPARK_MODE" = source ] && aws s3 cp "$TGZ" "$S3/artifacts/" --quiet

cd /
chown -R ubuntu:ubuntu /opt/spark/ "/opt/$(basename "$TGZ" .tgz)" /opt/jars "$PLACE"
rm -rf "$SRC" /root/.m2 /root/smoke /root/.ivy2 /tmp/aws /tmp/awscli.zip
apt-get clean
