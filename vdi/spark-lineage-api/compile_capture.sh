#!/bin/bash
# Builds the R2D7 row-group capture JAR (listener_versions_new/RowGroupCapture.scala)
# in a throwaway copy of the project, so src/main/scala/LineageAPI.scala and the six
# benchmark JARs built by compile.sh are left alone.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT_JAR="${1:-$HOME/spark-rowgroup-capture.jar}"
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

mkdir -p "$BUILD_DIR/src/main/scala"
cp "$HERE/pom.xml" "$BUILD_DIR/"
cp "$HERE/listener_versions_new/RowGroupCapture.scala" "$BUILD_DIR/src/main/scala/"
# Compile against the Scala library Spark actually ships (the pom says 2.13.16; the
# rowgroup-dev fork is on 2.13.8). Overridden here so the tracked pom is left alone.
SCALA_VERSION="${SCALA_VERSION:-2.13.8}"
(cd "$BUILD_DIR" && mvn -q -Dscala.version="$SCALA_VERSION" clean package)
cp "$BUILD_DIR"/target/spark-rowgroup-listener-1.0.0.jar "$OUT_JAR"
echo "Built $OUT_JAR (class RowGroupCapture)"
