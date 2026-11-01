"""
Cache manager for the Spark placement experiment. No DuckDB.

Decides which TPC-DS columns live on local disk under a size budget, with the same rules
as the original ColumnCache (column_cache.py), which it reproduces decision for decision:

  * a query's columns come from Spark's optimized plan (PlacementUsageListener.columnsForSql)
    against schema-only views, before the query runs;
  * columns not on disk are fetched from the source with pyarrow, whole columns, into
    32-row-group batch files under <cache>/tables/<table>/ (code copied from ColumnCache);
  * if the budget would be exceeded, cached columns are evicted in policy order until
    enough space is freed, never evicting a column the current query needs;
      - vod: order read from the VDI tables through Spark SQL (SparkVDI.eviction_order),
      - lru: least recent access first;
  * the query then runs in Spark against views over the cache directories, and the VDI
    listener appends its Data Value rows (dynamic mode) or nothing (static mode).

CacheState (what is on disk, sizes, last access) is a Python dict, exposed to Spark as a
view for the VDI lookup. A plain-Python copy of the original in-process VoD metric is kept
alongside, only to cross-check every VoD eviction against what the original would do.
"""

import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set, Tuple

import pyarrow as pa
import pyarrow.parquet as pq
from pyspark.sql import SparkSession

from .spark_session import bytes_listener_object, listener_object
from .vdi_store import DATA_VALUE_TABLE, TASK_VALUE_TABLE, SparkVDI

BATCH_SIZE = 32  # row groups per cache batch file, as in ColumnCache
GB_TO_BYTES = math.pow(2, 30)
LISTENER_TIMEOUT_MS = 10 * 60 * 1000

Key = Tuple[str, str]  # (table, column)


class PlacementCache:
    def __init__(self, spark: SparkSession, vdi: SparkVDI, *, policy: str, cache_dir: str,
                 max_cache_size_gb: float, column_sizes: Dict[str, Dict[str, int]],
                 plan_paths: Dict[str, str], filesystem=None,
                 reference_baseline: Optional[Dict[str, float]] = None,
                 tie_round_digits: Optional[int] = None):
        """
        vdi: the VDI tables (always present: the listener writes Data Value under every
            policy so instrumentation is identical; only vod reads it for eviction).
        plan_paths: table -> Parquet file with the table's schema (zero rows is fine);
            Spark plans queries against these to learn which columns they need.
        filesystem: pyarrow filesystem for source paths (S3FileSystem, or None for local).
        reference_baseline: column -> starting value of the original metric, for the
            cross-check (None disables it).
        """
        if policy not in ("lru", "vod"):
            raise ValueError("policy must be lru or vod")
        self.spark = spark
        self.vdi = vdi
        self.policy = policy
        self.cache_dir = cache_dir
        self.tables_dir = os.path.join(cache_dir, "tables")
        os.makedirs(self.tables_dir, exist_ok=True)
        self.max_bytes = max_cache_size_gb * GB_TO_BYTES
        self.sizes = column_sizes
        self.filesystem = filesystem
        self.rg_cache: Dict[str, Tuple[int, int]] = {}

        # CacheState: (table, column) -> size, cached, last access (logical clock).
        self.state: Dict[Key, Dict] = {}
        self.clock = 0
        # Plain-Python copy of ColumnCache's eviction_metric, for the cross-check only.
        self.reference_baseline = reference_baseline
        self.reference_metric: Dict[Key, float] = {}
        self.tie_round_digits = tie_round_digits
        self.eviction_log: List[List[Key]] = []
        self.crosscheck_events = 0
        self.crosscheck_mismatches: List[Dict] = []

        self.plan_session = spark.newSession()
        self.exec_session = spark.newSession()
        self.exec_session.conf.set("spark.vdi.placement.taskValueTable", TASK_VALUE_TABLE)
        self.exec_session.conf.set("spark.vdi.placement.dataValueTable", DATA_VALUE_TABLE)
        for table, path in plan_paths.items():
            self.plan_session.read.parquet(path).createOrReplaceTempView(table)
        self.listener = listener_object(spark)
        self.bytes_listener = bytes_listener_object(spark)
        self.timings: List[Dict] = []
        self._lookup_s = 0.0

    # ---- what a query needs --------------------------------------------------------------

    def columns_for(self, query: str) -> Dict[str, List[str]]:
        cols = json.loads(self.listener.columnsForSql(self.plan_session._jsparkSession, query))
        return {t: sorted(c) for t, c in cols.items()}

    # ---- CacheState ------------------------------------------------------------------------

    def _tick(self) -> int:
        self.clock += 1
        return self.clock

    def _cached(self, key: Key) -> bool:
        e = self.state.get(key)
        return bool(e and e["cached"])

    def cache_size(self) -> int:
        return sum(e["size"] for e in self.state.values() if e["cached"])

    def _touch(self, key: Key, vpc: float):
        """A cached column is read again (ColumnCache._update_column_values). All columns a
        query touches share one recency (self.clock, advanced once per phase)."""
        self.state[key]["last"] = self.clock
        if self.reference_baseline is not None:
            self.reference_metric[key] += vpc

    def _register(self, key: Key, vpc: float):
        """A column enters the cache (ColumnCache._cache_columns)."""
        self.state[key] = {"size": self.sizes[key[0]][key[1]], "cached": True,
                           "last": self.clock}
        if self.reference_baseline is not None:
            if key in self.reference_metric:
                self.reference_metric[key] += vpc
            else:
                self.reference_metric[key] = self.reference_baseline[key[1]] + vpc

    def cache_state_rows(self):
        return [(t, c, e["size"], e["last"], e["cached"]) for (t, c), e in self.state.items()]

    # ---- eviction --------------------------------------------------------------------------

    @staticmethod
    def _pick(order: List[Key], sizes: Dict[Key, int], required_space: float,
              required_columns: Set[str]) -> List[Key]:
        """The loop in ColumnCache._evict_columns, without side effects."""
        picked, freed = [], 0
        for key in order:
            if freed >= required_space:
                break
            if key[1] in required_columns:
                continue
            freed += sizes[key]
            picked.append(key)
        return picked

    def _eviction_order(self) -> List[Key]:
        cached = [k for k, e in self.state.items() if e["cached"]]
        if self.policy == "lru":
            return sorted(cached, key=lambda k: (self.state[k]["last"], k))
        t = time.perf_counter()
        try:
            return self.vdi.eviction_order(self.cache_state_rows())
        finally:
            self._lookup_s += time.perf_counter() - t

    def _reference_order(self) -> List[Key]:
        d = self.tie_round_digits
        cached = [k for k, e in self.state.items() if e["cached"]]
        return sorted(cached, key=lambda k: (round(self.reference_metric[k], d)
                                             if d is not None else self.reference_metric[k], k))

    def _evict(self, required_space: float, required_columns: Set[str], replay: bool):
        sizes = {k: e["size"] for k, e in self.state.items() if e["cached"]}
        per_table = {}
        for (t, _c) in sizes:
            per_table[t] = per_table.get(t, 0) + 1
        picked = self._pick(self._eviction_order(), sizes, required_space, required_columns)
        if self.policy == "vod" and self.reference_baseline is not None:
            self.crosscheck_events += 1
            ref = self._pick(self._reference_order(), sizes, required_space, required_columns)
            if ref != picked:
                self.crosscheck_mismatches.append(
                    {"event": len(self.eviction_log), "vdi": picked, "reference": ref})
        self.eviction_log.append(picked)
        by_table: Dict[str, List[str]] = {}
        for t, c in picked:
            self.state[(t, c)]["cached"] = False
            by_table.setdefault(t, []).append(c)
        if not replay and by_table:
            args = [(t, cs, len(cs) == per_table[t]) for t, cs in by_table.items()]
            with ThreadPoolExecutor(max_workers=len(args)) as pool:
                list(pool.map(lambda a: self._evict_columns_parallel(*a), args))

    def _plan_fetch(self, columns_for_table: Dict[str, List[str]], vpc: float,
                    replay: bool) -> Dict[str, List[str]]:
        """ColumnCache.evict_necessary_columns: touch cached columns, evict for the rest."""
        to_fetch: Dict[str, List[str]] = {}
        fetch_bytes = 0
        required: Set[str] = set()
        self._tick()  # recency of the columns this query touches
        for t, cols in columns_for_table.items():
            required.update(cols)
            for c in cols:
                if not self._cached((t, c)):
                    to_fetch.setdefault(t, []).append(c)
                    fetch_bytes += self.sizes[t][c]
                else:
                    self._touch((t, c), vpc)
        current = self.cache_size()
        if current + fetch_bytes > self.max_bytes:
            self._evict(current + fetch_bytes - self.max_bytes, required, replay)
        return to_fetch

    # ---- the three entry points --------------------------------------------------------------

    def replay(self, task_id: str, query: str, value: float, write_data_value: bool = True):
        """Warm-up: the query's effect on the cache in metadata only (ColumnCache.replay_query),
        plus its Data Value rows (no execution, so the harness writes them).
        write_data_value=False mirrors a static-mode query (tests only)."""
        cols = self.columns_for(query)
        n = sum(len(c) for c in cols.values())
        vpc = value / n if (value > 0 and n > 0) else 0
        to_fetch = self._plan_fetch(cols, vpc, replay=True)
        self._tick()  # recency of the columns this query brings in
        for t, cs in to_fetch.items():
            for c in cs:
                self._register((t, c), vpc)
        if write_data_value:
            self.vdi.record_replay(task_id, cols)

    def materialize(self, source_paths: Dict[str, str]):
        """Fetch, untimed, every column CacheState says is cached
        (ColumnCache.materialize_cache_from_metadata)."""
        by_table: Dict[str, List[str]] = {}
        for (t, c), e in self.state.items():
            if e["cached"]:
                by_table.setdefault(t, []).append(c)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda tc: self._fetch_columns_parallel(source_paths[tc[0]], tc[0], tc[1]),
                          by_table.items()))

    def execute(self, task_id: str, query: str, value: float, exec_id: str,
                source_paths: Dict[str, str], write_data_value: bool):
        """Timed: plan, fetch/evict, run in Spark; then wait for the listener (untimed)."""
        t0 = time.perf_counter()
        lookup0 = self._lookup_s
        cols = self.columns_for(query)
        n = sum(len(c) for c in cols.values())
        vpc = value / n if (value > 0 and n > 0) else 0
        t_plan = time.perf_counter()

        to_fetch = self._plan_fetch(cols, vpc, replay=False)
        fetched_bytes = sum(self.sizes[t][c] for t, cs in to_fetch.items() for c in cs)
        if to_fetch:
            with ThreadPoolExecutor(max_workers=len(to_fetch)) as pool:
                list(pool.map(lambda tc: self._fetch_columns_parallel(source_paths[tc[0]], tc[0], tc[1]),
                              to_fetch.items()))
            self._tick()  # recency of the columns this query brings in
            for t, cs in to_fetch.items():
                for c in cs:
                    self._register((t, c), vpc)
        t_fetch = time.perf_counter()

        for t in cols:
            self.exec_session.read.parquet(os.path.join(self.tables_dir, t)).createOrReplaceTempView(t)
        t_views = time.perf_counter()

        conf = self.exec_session.conf
        conf.set("spark.vdi.placement.taskId", task_id)
        conf.set("spark.vdi.placement.execId", exec_id)
        conf.set("spark.vdi.placement.writeDataValue", "true" if write_data_value else "false")
        sc = self.spark.sparkContext
        sc.setJobGroup(exec_id, exec_id)  # attributes Spark's input bytes to this query
        try:
            rows = self.exec_session.sql(query).collect()
        finally:
            t_exec = time.perf_counter()
            sc.setLocalProperty("spark.jobGroup.id", None)
            sc.setLocalProperty("spark.job.description", None)
            status = self.listener.awaitExecution(exec_id, LISTENER_TIMEOUT_MS)
            conf.unset("spark.vdi.placement.execId")
            t_listener = time.perf_counter()
        if not status.startswith("ok"):
            raise RuntimeError(f"VDI listener for {exec_id}: {status}")
        self.timings.append({
            "task_id": task_id, "exec_id": exec_id,
            "plan_s": t_plan - t0,                     # columns from Spark's plan
            "fetch_evict_s": t_fetch - t_plan,         # includes vdi_lookup_s
            "vdi_lookup_s": self._lookup_s - lookup0,  # Spark SQL over the VDI tables
            "view_refresh_s": t_views - t_fetch,
            "exec_s": t_exec - t_views,
            "query_s": t_exec - t0,                    # user-observed latency
            "listener_wait_s": t_listener - t_exec,    # Data Value append, after the result
            "data_value_rows": int(status.split(":", 1)[1]),
            "s3_bytes_fetched": fetched_bytes,         # compressed column chunks fetched
            "spark_bytes_read": int(self.bytes_listener.takeBytesRead(exec_id)),
            "columns": n,
        })
        return rows

    def stats(self) -> Dict:
        cached = [e for e in self.state.values() if e["cached"]]
        return {"total_columns": len(cached),
                "total_size_gb": sum(e["size"] for e in cached) / GB_TO_BYTES,
                "total_tables": len({t for (t, _), e in self.state.items() if e["cached"]}),
                "max_size_gb": self.max_bytes / GB_TO_BYTES}

    # ---- pyarrow fetch / evict (copied from ColumnCache, unchanged in behaviour) ------------

    def _get_parquet_metadata(self, table_name: str, source_path: str):
        if table_name in self.rg_cache:
            return self.rg_cache[table_name]
        pf = pq.ParquetFile(source_path, filesystem=self.filesystem)
        self.rg_cache[table_name] = (pf.num_row_groups, pf.metadata.row_group(0).num_rows)
        return self.rg_cache[table_name]

    def _fetch_columns_batch(self, source_path, table_name, batch_id, required_columns):
        num_rgs, _ = self._get_parquet_metadata(table_name, source_path)
        rg_start = batch_id * BATCH_SIZE
        rg_ids = list(range(rg_start, min(rg_start + BATCH_SIZE, num_rgs)))
        batch_path = os.path.join(self.tables_dir, table_name, f"batch_{batch_id:06d}.parquet")
        os.makedirs(os.path.dirname(batch_path), exist_ok=True)
        cached_tbl = None
        if os.path.exists(batch_path):
            cached_tbl = pq.ParquetFile(batch_path, filesystem=None).read()
        src_pf = pq.ParquetFile(source_path, filesystem=self.filesystem)
        fetched_tbl = src_pf.read_row_groups(rg_ids, columns=required_columns)
        if cached_tbl is not None:
            merged = pa.Table.from_arrays(
                list(cached_tbl.columns) + list(fetched_tbl.columns),
                names=list(cached_tbl.schema.names) + list(required_columns))
        else:
            merged = fetched_tbl
        pq.write_table(merged, batch_path)

    def _fetch_columns_parallel(self, source_path, table_name, column_names, max_workers=4):
        num_row_groups, _ = self._get_parquet_metadata(table_name, source_path)
        num_batches = (num_row_groups + BATCH_SIZE - 1) // BATCH_SIZE
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            list(ex.map(lambda b: self._fetch_columns_batch(source_path, table_name, b, column_names),
                        range(num_batches)))

    def _evict_columns_batch(self, batch_path, columns_to_evict, delete_file):
        if delete_file:
            os.remove(batch_path)
        else:
            tbl = pq.ParquetFile(batch_path, filesystem=None).read()
            pq.write_table(tbl.drop(columns_to_evict), batch_path)

    def _evict_columns_parallel(self, table_name, columns_to_evict, delete_file, max_workers=4):
        table_dir = os.path.join(self.tables_dir, table_name)
        batch_files = sorted(f for f in os.listdir(table_dir) if f.endswith(".parquet"))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            list(ex.map(lambda f: self._evict_columns_batch(os.path.join(table_dir, f),
                                                            columns_to_evict, delete_file),
                        batch_files))
