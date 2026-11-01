"""
Placement experiment with Spark as the query engine and the VDI in Spark (R2D14, R3W1,
R3D1). No DuckDB.

One run = one cache size x one value assignment x one policy, as in run.py:
  1. Create the VDI tables (Iceberg, local catalog): Task Value = the 99 TPC-DS queries
     valued by the value assignment; Data Value seeded with the offline history (the same
     1500 sampled executions, seed 0, that produced the shipped starting values).
  2. Warm-up (--fill-cache, untimed): replay each query once in metadata only, with its
     value; the harness writes those Data Value rows (no execution, no listener). Then
     fetch the resulting cache contents from the source. Then compact Data Value
     (untimed; --no-compact skips it).
  3. Timed phase: run the 99 queries in order. Per query: columns from Spark's plan,
     fetch/evict (vod: eviction order from Spark SQL over the VDI tables; lru: least
     recent first), run in Spark. The listener appends Data Value rows after each query
     in dynamic mode, and none in static mode.

Output: <outfile> has run.py's shape ({"01.sql": seconds, ..., "total_time"}), so
metric/analyze.py reads it unchanged; <outfile minus .json>.breakdown.json has the per-
query breakdown (incl. S3 bytes fetched and Spark bytes read), the VoD cross-check
against the original metric, and the run's parameters.
"""

import json
import os
import platform
import subprocess
import sys
import time
from argparse import ArgumentParser
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from column_cache.placement_cache import PlacementCache  # noqa: E402
from column_cache.spark_session import build_spark  # noqa: E402
from column_cache.vdi_store import SparkVDI  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
TIE_DIGITS = 9
QUERY_KEYS = [f"{i:02d}.sql" for i in range(1, 100)]


def write_schema_files(table_paths, filesystem, out_dir):
    """Zero-row Parquet files with each source table's schema, named <table>.parquet.
    Spark plans queries against these to learn their columns: no S3 connector is needed
    in Spark, and nothing is read from the source outside the cache's own fetches."""
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    for table, path in table_paths.items():
        dst = os.path.join(out_dir, f"{table}.parquet")
        if not os.path.exists(dst):
            schema = pq.ParquetFile(path, filesystem=filesystem).schema_arrow
            pq.write_table(pa.Table.from_pylist([], schema=schema), dst)
        out[table] = dst
    return out


def history_executions(columns_file, n, seed):
    """The offline history: n executions sampled uniformly from the 99 queries with
    numpy default_rng(seed), exactly as value_generation/assign_val_to_de.py and
    spark_baselines.py sample them. Returns [(task_id, {table: [columns]})]."""
    cols = json.load(open(columns_file))
    sampled = np.random.default_rng(seed).integers(len(QUERY_KEYS), size=n)
    return [(QUERY_KEYS[i], cols[QUERY_KEYS[i]]) for i in sampled]


def git_rev():
    try:
        return subprocess.check_output(["git", "-C", HERE, "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def main():
    p = ArgumentParser(description="Placement experiment runner (Spark engine, Spark VDI)")
    p.add_argument("--cache-dir", default="../metadata/cache_spark")
    p.add_argument("--max-cache-size", type=float, default=10.0, help="GB")
    p.add_argument("--s3-region", default=None)
    p.add_argument("--s3-bucket", default="vod-tpcds-10gb")
    p.add_argument("--local-mode", action="store_true")
    p.add_argument("--data-dir", default=None, help="local mode: dir with <table>.parquet")
    p.add_argument("--policy", default="lru", choices=["lru", "vod"])
    p.add_argument("--schema-file", default="../metadata/tpcds_schema_registry.json")
    p.add_argument("--size-file", default="../metadata/sizes_30gb/column_sizes.json")
    p.add_argument("--query-value-file", default="../metadata/tpcds_query_values_custom.csv")
    p.add_argument("--query-dir", default="../test/example_queries/tpcds_spark/")
    p.add_argument("--history-columns", default="../value_generation/tpcds_columns_in_queries_spark.json",
                   help="per-query column sets logged by the listener (tools/extract_spark_columns.py)")
    p.add_argument("--history-n", type=int, default=1500)
    p.add_argument("--history-seed", type=int, default=0)
    p.add_argument("--value-iter", default="0")
    p.add_argument("--fill-cache", action="store_true")
    p.add_argument("--dynamic", action="store_true")
    p.add_argument("--no-crosscheck", action="store_true",
                   help="skip the plain-Python reference metric used to cross-check VoD")
    p.add_argument("--no-compact", action="store_true",
                   help="skip compacting Data Value after the warm-up")
    p.add_argument("--master", default="local[*]")
    p.add_argument("--driver-memory", default="20g",
                   help="local mode: all of Spark runs in the driver JVM (m7g.2xlarge has 32 GiB)")
    p.add_argument("--outfile", default="experiment_results.json")
    p.add_argument("--queries", default=None, help="comma-separated subset, e.g. 1,2,3 (testing)")
    args = p.parse_args()
    assert args.local_mode or args.s3_region, "need --s3-region or --local-mode"
    print(args, flush=True)
    started = datetime.now(timezone.utc).isoformat()

    os.makedirs(args.cache_dir, exist_ok=True)
    schema_registry = json.load(open(args.schema_file))
    if args.local_mode:
        source_paths = {t: os.path.join(args.data_dir, f"{t}.parquet") for t in schema_registry}
        filesystem = None
    else:
        source_paths = {t: f"{args.s3_bucket}/{t}.parquet" for t in schema_registry}
        filesystem = pa.fs.S3FileSystem(region=args.s3_region)
    plan_paths = write_schema_files(source_paths, filesystem, os.path.join(args.cache_dir, "schemas"))

    query_ids = [int(x) for x in args.queries.split(",")] if args.queries else range(1, 100)
    keys = [f"{i:02d}.sql" for i in query_ids]
    queries = {k: open(os.path.join(args.query_dir, k)).read() for k in QUERY_KEYS}
    qv = pd.read_csv(args.query_value_file).set_index("query_id")[args.value_iter]

    spark = build_spark(os.path.join(args.cache_dir, "warehouse"), master=args.master,
                        with_listener=True, driver_memory=args.driver_memory)
    vdi = SparkVDI(spark, round_digits=TIE_DIGITS)
    # Task Value: every TPC-DS query is a task, valued by this run's value assignment.
    vdi.create({k: (queries[k], float(qv[k])) for k in QUERY_KEYS})
    history = history_executions(args.history_columns, args.history_n, args.history_seed)
    history_rows = vdi.seed_history(history, end=datetime.now())

    reference = None
    if not args.no_crosscheck:
        # The original metric's starting values, recomputed from the same history.
        reference = {}
        for task_id, cols in history:
            n = sum(len(c) for c in cols.values())
            for t, cs in cols.items():
                for c in cs:
                    reference[c] = reference.get(c, 0.0) + float(qv[task_id]) / n
        for t, cs in schema_registry.items():
            for c in cs:
                reference.setdefault(c, 0.0)
    sizes = json.load(open(args.size_file))
    cache = PlacementCache(spark, vdi, policy=args.policy, cache_dir=args.cache_dir,
                           max_cache_size_gb=args.max_cache_size, column_sizes=sizes,
                           plan_paths=plan_paths, filesystem=filesystem,
                           reference_baseline=reference, tie_round_digits=TIE_DIGITS)

    # One untimed query so JVM start-up and first-use costs fall outside the timed window.
    spark.sql("SELECT 1").collect()

    materialize_s = None
    if args.fill_cache:
        for k in keys:
            cache.replay(k, queries[k], float(qv[k]))
        t = time.time()
        cache.materialize(source_paths)
        materialize_s = time.time() - t
    warm_evictions = len(cache.eviction_log)

    # Untimed: compact Data Value so the timed lookups plan over one file instead of one
    # per append so far. Appends during the timed phase (dynamic) add files again.
    compaction = None
    if not args.no_compact:
        t = time.time()
        compaction = vdi.compact()
        compaction["seconds"] = time.time() - t
        print(f"Data Value compaction: {compaction}", flush=True)

    ret = {}
    total_start = time.time()
    for k in keys:
        print("===============================\n" + k, flush=True)
        # Values reach the cache only in dynamic mode, as in run.py (static passes 0).
        cache.execute(k, queries[k], float(qv[k]) if args.dynamic else 0.0,
                      exec_id=f"exp:{k}", source_paths=source_paths,
                      write_data_value=args.dynamic)
        ret[k] = cache.timings[-1]["query_s"]
    ret["total_time"] = time.time() - total_start
    print(f"Total time for experiment: {ret['total_time']} seconds", flush=True)
    print(f"Cache stats: {cache.stats()}", flush=True)

    with open(args.outfile, "w") as f:
        json.dump(ret, f, indent=4)
    if cache.crosscheck_mismatches:
        print(f"WARNING: {len(cache.crosscheck_mismatches)}/{cache.crosscheck_events} VoD "
              f"evictions differ from the original metric (see breakdown)", flush=True)
    breakdown = {
        "args": vars(args), "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "git_rev": git_rev(), "host": platform.node(), "spark_version": spark.version,
        "history_rows": history_rows, "materialize_s": materialize_s,
        "evictions": len(cache.eviction_log), "warmup_evictions": warm_evictions,
        "compaction": compaction,
        "data_value_files_end": vdi.data_file_count(),
        "crosscheck_events": cache.crosscheck_events,
        "crosscheck_mismatches": cache.crosscheck_mismatches,
        "cache_stats": cache.stats(),
        "duckdb_loaded": "duckdb" in sys.modules,   # must be False: no DuckDB in this path
        "queries": {t["task_id"]: t for t in cache.timings},
    }
    base = args.outfile[:-5] if args.outfile.endswith(".json") else args.outfile
    with open(base + ".breakdown.json", "w") as f:
        json.dump(breakdown, f, indent=2)
    spark.stop()


if __name__ == "__main__":
    main()
