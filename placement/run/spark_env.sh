# Source this before any Spark run of the placement harness:  . ./spark_env.sh
# Defaults are the AMI layout (aws/README.md); override any variable before sourcing.
export SPARK_HOME="${SPARK_HOME:-/opt/spark}"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-arm64}"
export VDI_ICEBERG_JAR="${VDI_ICEBERG_JAR:-/opt/jars/iceberg-spark-runtime.jar}"
export VDI_LISTENER_JAR="${VDI_LISTENER_JAR:-/opt/jars/vdi-listener.jar}"
_py4j="$(ls "$SPARK_HOME"/python/lib/py4j-*-src.zip 2>/dev/null | head -1)"
export PYTHONPATH="$SPARK_HOME/python:${_py4j}${PYTHONPATH:+:$PYTHONPATH}"
unset _py4j
