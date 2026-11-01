#!/usr/bin/env bash
# Local-testing Spark home: your built Spark checkout (~/value_of_data/spark), with the
# spark-sql jar replaced by one built from rowgroup-dev at or after e9174562ee3 (thread-safe
# RowGroupMetricsRegistry.keys). Everything else is symlinked, nothing is copied but one jar.
#   tools/make_local_spark_home.sh [<built spark-sql jar>]
# then:  export VDI_LOCAL_SPARK_HOME=~/.cache/vdi-placement/sparkhome; . run/spark_env_local.sh
set -euo pipefail
SRC="${VDI_SPARK_CHECKOUT:-$HOME/value_of_data/spark}"
JAR="${1:-$SRC/sql/core/target/spark-sql_2.13-3.5.5.jar}"
DST="${VDI_LOCAL_SPARK_HOME:-$HOME/.cache/vdi-placement/sparkhome}"
[ -f "$JAR" ] || { echo "no spark-sql jar at $JAR; build it from rowgroup-dev: (cd $SRC && ./build/mvn -o -q -Pscala-2.13 -pl sql/core -DskipTests package)" >&2; exit 1; }
unzip -p "$JAR" org/apache/spark/sql/execution/datasources/parquet/RowGroupMetricsRegistry\$.class \
    | grep -q synchronizedList || { echo "$JAR lacks the thread-safe keys fix" >&2; exit 1; }
rm -rf "$DST"; mkdir -p "$DST/assembly/target/scala-2.13/jars"
for d in bin sbin conf python launcher common core sql; do ln -s "$SRC/$d" "$DST/$d"; done
for j in "$SRC"/assembly/target/scala-2.13/jars/*.jar; do
    b=$(basename "$j")
    if [ "$b" = spark-sql_2.13-3.5.5.jar ]; then cp "$JAR" "$DST/assembly/target/scala-2.13/jars/$b"
    else ln -s "$j" "$DST/assembly/target/scala-2.13/jars/$b"; fi
done
echo "local Spark home: $DST"
