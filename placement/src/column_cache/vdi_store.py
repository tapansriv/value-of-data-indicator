"""
The VDI as the paper defines it (§3): a Task Value table and a Data Value table, here
Iceberg tables in a local catalog, written and read only through Spark.

    task_value(task_id, task_text, task_value)
        One row per task: the 99 TPC-DS query templates, valued by the run's value
        assignment. Written once before the run.
    data_value(task_id, table_name, column_name, row_group_id, ts, value)
        Append-only; one row per task execution x column it read, value = task_value /
        #columns read (Equal dividing, column granularity, row_group_id NULL).
        Seeded with the offline history; appended by the listener for executed queries
        (vdi.placement.PlacementUsageListener) and by the harness for replayed ones.

The VDI of a column is SUM(value) over its data_value rows. Eviction ranks the cached
columns by it, reading cache residency from a CacheState view the cache manager supplies.
"""

from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from pyspark.sql import SparkSession
from pyspark.sql.types import (DoubleType, IntegerType, StringType, StructField,
                               StructType, TimestampType)

from .spark_session import CATALOG

NAMESPACE = f"{CATALOG}.placement"
TASK_VALUE_TABLE = f"{NAMESPACE}.task_value"
DATA_VALUE_TABLE = f"{NAMESPACE}.data_value"

TASK_VALUE_SCHEMA = StructType([
    StructField("task_id", StringType(), False),
    StructField("task_text", StringType(), True),
    StructField("task_value", DoubleType(), False),
])
# Must match PlacementUsageListener.DataValueSchema in spark-lineage-api.
DATA_VALUE_SCHEMA = StructType([
    StructField("task_id", StringType(), False),
    StructField("table_name", StringType(), False),
    StructField("column_name", StringType(), True),
    StructField("row_group_id", IntegerType(), True),
    StructField("ts", TimestampType(), False),
    StructField("value", DoubleType(), False),
])


def _quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


class SparkVDI:
    def __init__(self, spark: SparkSession, shuffle_partitions: int = 8,
                 round_digits: Optional[int] = None):
        # Own session, so this setting never reaches the TPC-DS queries (which run in a
        # separate session with Spark's defaults). The VDI tables are small; 200 shuffle
        # partitions (the default) roughly doubles a lookup.
        self.spark = spark.newSession()
        self.spark.conf.set("spark.sql.shuffle.partitions", str(shuffle_partitions))
        # When set, ties in VDI are broken by (table, column) after rounding to this many
        # digits, so decisions can be compared exactly with a reference implementation.
        self.round_digits = round_digits
        self.task_values: Dict[str, float] = {}

    # ---- setup -------------------------------------------------------------------------

    def create(self, task_values: Dict[str, Tuple[str, float]]):
        """Create both tables (replacing any from an earlier run) and write Task Value.
        task_values: task_id -> (task_text, task_value)."""
        s = self.spark
        s.sql(f"CREATE NAMESPACE IF NOT EXISTS {NAMESPACE}")
        for table, schema in ((TASK_VALUE_TABLE, TASK_VALUE_SCHEMA),
                              (DATA_VALUE_TABLE, DATA_VALUE_SCHEMA)):
            s.sql(f"DROP TABLE IF EXISTS {table}")
            s.createDataFrame([], schema).writeTo(table).using("iceberg").create()
        rows = [(tid, text, float(v)) for tid, (text, v) in sorted(task_values.items())]
        s.createDataFrame(rows, TASK_VALUE_SCHEMA).writeTo(TASK_VALUE_TABLE).append()
        self.task_values = {tid: float(v) for tid, (_, v) in task_values.items()}

    def seed_history(self, executions: Iterable[Tuple[str, Dict[str, List[str]]]],
                     end: datetime):
        """Append Data Value rows for past executions [(task_id, {table: [columns]})],
        one second apart and ending before `end`, valued as the listener would."""
        executions = list(executions)
        start = end - timedelta(seconds=len(executions) + 1)
        rows = []
        for i, (task_id, cols) in enumerate(executions):
            rows.extend(self._rows(task_id, cols, start + timedelta(seconds=i)))
        if rows:
            self.spark.createDataFrame(rows, DATA_VALUE_SCHEMA).writeTo(DATA_VALUE_TABLE).append()
        return len(rows)

    # ---- writes for replayed (not executed) tasks ------------------------------------

    def record_replay(self, task_id: str, columns_for_table: Dict[str, List[str]]):
        """Data Value rows for a task replayed in metadata only (warm-up): no execution,
        so the listener cannot log it. Same rule as the listener."""
        rows = self._rows(task_id, columns_for_table, datetime.now())
        if rows:
            self.spark.createDataFrame(rows, DATA_VALUE_SCHEMA).writeTo(DATA_VALUE_TABLE).append()

    def _rows(self, task_id, columns_for_table, ts):
        n = sum(len(c) for c in columns_for_table.values())
        if n == 0:
            return []
        share = self.task_values.get(task_id, 0.0) / n
        return [(task_id, t, c, None, ts, share)
                for t in sorted(columns_for_table) for c in sorted(columns_for_table[t])]

    # ---- maintenance -----------------------------------------------------------------

    def data_file_count(self) -> int:
        """Data files in Data Value's current snapshot (one per append until compacted)."""
        return self.spark.sql(f"SELECT COUNT(*) AS n FROM {DATA_VALUE_TABLE}.files").first().n

    def compact(self) -> Dict[str, int]:
        """Compact Data Value into as few files and manifests as possible (Iceberg's
        rewriteDataFiles + rewriteManifests actions). Every append (history seed, each
        warm-up replay, each listener write) adds a small data file and a manifest, and
        a lookup plans over all of them; the run compacts once after the untimed
        warm-up. Called through the Java actions API, so the query session does not need
        Iceberg's SQL extensions. Rows and values are unchanged."""
        jvm = self.spark.sparkContext._jvm
        jspark = self.spark._jsparkSession
        load = lambda: jvm.org.apache.iceberg.spark.Spark3Util.loadIcebergTable(jspark, DATA_VALUE_TABLE)
        actions = jvm.org.apache.iceberg.spark.actions.SparkActions.get(jspark)
        before = self.data_file_count()
        r = actions.rewriteDataFiles(load()).option("rewrite-all", "true").execute()
        m = actions.rewriteManifests(load()).execute()
        return {"files_before": before, "files_after": self.data_file_count(),
                "files_rewritten": r.rewrittenDataFilesCount(),
                "manifests_rewritten": sum(1 for _ in m.rewrittenManifests())}

    # ---- reads -----------------------------------------------------------------------

    def eviction_order(self, cache_state: List[Tuple[str, str, int, int, bool]]) -> List[Tuple[str, str]]:
        """Cached columns, lowest VDI first. cache_state rows:
        (table_name, column_name, size_bytes, last_access, cached)."""
        cached = [r for r in cache_state if r[4]]
        if not cached:
            return []
        self.register_cache_state(cached)
        vdi = "SUM(dv.value)"
        if self.round_digits is not None:
            vdi = f"ROUND({vdi}, {self.round_digits})"
        rows = self.spark.sql(f"""
            SELECT c.table_name, c.column_name, {vdi} AS vdi
            FROM {DATA_VALUE_TABLE} dv
            JOIN cache_state c
              ON dv.table_name = c.table_name AND dv.column_name = c.column_name
            WHERE c.cached
            GROUP BY c.table_name, c.column_name
            ORDER BY vdi ASC, c.table_name ASC, c.column_name ASC
        """).collect()
        ranked = [(r.vdi, r.table_name, r.column_name) for r in rows]
        # A cached column with no Data Value rows has VDI 0 (e.g. fetched during a static
        # timed phase and absent from the history), the same as the original metric's
        # zero baseline. Merge it into the same (vdi, table, column) order.
        seen = {(t, c) for _, t, c in ranked}
        ranked += [(0.0, r[0], r[1]) for r in cached if (r[0], r[1]) not in seen]
        ranked.sort()
        return [(t, c) for _, t, c in ranked]

    def register_cache_state(self, rows: List[Tuple[str, str, int, int, bool]]):
        """CacheState as an inline VALUES view: a local relation, ~6 ms to rebuild
        (a createDataFrame view costs ~100 ms more per join)."""
        values = ",".join(
            f"({_quote(t)}, {_quote(c)}, {int(size)}L, {int(last)}L, {'true' if cached else 'false'})"
            for t, c, size, last, cached in rows)
        self.spark.sql(
            "CREATE OR REPLACE TEMP VIEW cache_state AS SELECT * FROM VALUES "
            f"{values} AS t(table_name, column_name, size_bytes, last_access, cached)")

    def data_values(self) -> Dict[Tuple[str, str], float]:
        """VDI of every column that has Data Value rows (for inspection and tests)."""
        rows = self.spark.sql(f"""
            SELECT table_name, column_name, SUM(value) AS vdi FROM {DATA_VALUE_TABLE}
            GROUP BY table_name, column_name""").collect()
        return {(r.table_name, r.column_name): r.vdi for r in rows}
