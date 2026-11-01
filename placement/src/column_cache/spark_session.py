"""
SparkSession for the placement experiment: the forked Spark (rowgroup-dev, Scala 2.13),
an Iceberg hadoop catalog `vdi` for the VDI tables, and optionally the column-usage
listener (vdi.placement.PlacementUsageListener from spark-lineage-api).

Jars come from the environment (see run/spark_env.sh):
    VDI_ICEBERG_JAR   iceberg-spark-runtime-3.5_2.13-1.8.1.jar
    VDI_LISTENER_JAR  spark-lineage-api jar containing vdi.placement.PlacementUsageListener
"""
import os
from typing import Optional

from pyspark.sql import SparkSession

CATALOG = "vdi"
LISTENER_CLASS = "vdi.placement.PlacementUsageListener"
BYTES_LISTENER_CLASS = "vdi.placement.PlacementBytesListener"


def build_spark(warehouse: str, master: str = "local[*]", with_listener: bool = False,
                driver_memory: Optional[str] = None,
                extra_conf: Optional[dict] = None) -> SparkSession:
    jars = [os.environ.get("VDI_ICEBERG_JAR")]
    if with_listener:
        jars.append(os.environ.get("VDI_LISTENER_JAR"))
        if not jars[-1]:
            raise RuntimeError("VDI_LISTENER_JAR is not set (source run/spark_env.sh)")
    if not jars[0]:
        raise RuntimeError("VDI_ICEBERG_JAR is not set (source run/spark_env.sh)")
    builder = (SparkSession.builder
               .master(master)
               .appName("vdi-placement")
               .config("spark.jars", ",".join(jars))
               .config(f"spark.sql.catalog.{CATALOG}", "org.apache.iceberg.spark.SparkCatalog")
               .config(f"spark.sql.catalog.{CATALOG}.type", "hadoop")
               .config(f"spark.sql.catalog.{CATALOG}.warehouse",
                       f"file://{os.path.abspath(warehouse)}")
               # The listener appends usage through the query session; the VDI store reads
               # through its own session. Iceberg's catalog cache is per session and never
               # refreshes a cached table, so with it on the store read stale usage (every
               # executed query invisible; test/test_cross_session_visibility.py).
               .config(f"spark.sql.catalog.{CATALOG}.cache-enabled", "false")
               .config("spark.ui.enabled", "false")
               .config("spark.ui.showConsoleProgress", "false")
               # The cache rewrites batch files in place under the same names. Spark's
               # shared file-status cache would keep the old lengths and read footers at
               # stale offsets (seen as ArrayIndexOutOfBounds in the Parquet reader), so
               # it is disabled: every view refresh lists the directory afresh.
               .config("spark.sql.hive.filesourcePartitionFileCacheSize", "0")
               # Full JVM stack traces in Python exceptions (diagnosing runs on nodes).
               .config("spark.sql.pyspark.jvmStacktrace.enabled", "true"))
    if driver_memory:
        # Local mode: the driver JVM is the only JVM, so this is all executor memory too.
        builder = builder.config("spark.driver.memory", driver_memory)
    if with_listener:
        builder = (builder.config("spark.sql.queryExecutionListeners", LISTENER_CLASS)
                   .config("spark.extraListeners", BYTES_LISTENER_CLASS))
    for k, v in (extra_conf or {}).items():
        builder = builder.config(k, v)
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def listener_object(spark: SparkSession):
    """The Scala companion object (static helpers) of the VDI listener."""
    return spark.sparkContext._jvm.vdi.placement.PlacementUsageListener


def bytes_listener_object(spark: SparkSession):
    """The Scala companion object of the bytes-read listener."""
    return spark.sparkContext._jvm.vdi.placement.PlacementBytesListener
