# Laptop paths for local development; sources spark_env.sh with these overrides.
export SPARK_HOME="${VDI_LOCAL_SPARK_HOME:-$HOME/value_of_data/spark}"
export JAVA_HOME="$(/usr/libexec/java_home -v 17 2>/dev/null || echo /opt/homebrew/opt/openjdk@17)"
export VDI_ICEBERG_JAR="$HOME/Library/Caches/Coursier/v1/https/repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.13/1.8.1/iceberg-spark-runtime-3.5_2.13-1.8.1.jar"
export VDI_LISTENER_JAR="${VDI_LOCAL_LISTENER_JAR:-$HOME/.cache/vdi-placement/vdi-listener.jar}"  # build: mvn -o -DskipTests package in value-of-data-metric/spark-lineage-api
. "$(dirname "${BASH_SOURCE[0]:-$0}")/spark_env.sh"
