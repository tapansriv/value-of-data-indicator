"""
The Spark placement path makes the same eviction decisions as the original DuckDB harness.

Replays whole runs (warm-up + the 99-query phase) in metadata only, no data read, with
  * reference: the ORIGINAL ColumnCache (column_cache.py, DuckDB) — test use only;
  * new:       PlacementCache + SparkVDI (Iceberg tables read through Spark SQL, history
               seeded as Data Value rows, columns from Spark's plan) — the experiment path.
Static phase: values 0 and no Data Value rows (listener writes nothing); dynamic: values
flow and rows are appended. Ties are broken by (table, column) in both (rounded VDI for
vod) because the original ORDER BY leaves tie order unspecified.

    . run/spark_env_local.sh
    python3 test/validate_spark_vdi.py --data-dir ~/tpcds_sf1_place [--sizes ..] [--iters ..]
"""

import json
import os
import shutil
import sys
import tempfile
import time
from argparse import ArgumentParser
from datetime import datetime

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "run"))
from column_cache import ColumnCache  # noqa: E402  (reference only)
from column_cache.placement_cache import PlacementCache  # noqa: E402
from column_cache.spark_session import build_spark  # noqa: E402
from column_cache.vdi_store import SparkVDI  # noqa: E402
from run_spark import QUERY_KEYS, history_executions  # noqa: E402

META = os.path.join(ROOT, "metadata")
DUCK_Q = os.path.join(ROOT, "test", "example_queries", "tpcds")
SPARK_Q = os.path.join(ROOT, "test", "example_queries", "tpcds_spark")
DIGITS = 9


def original_run(size, it, dynamic, policy, workdir):
    d = os.path.join(workdir, f"orig_{policy}_{size}_{it}_{int(dynamic)}")
    shutil.rmtree(d, ignore_errors=True)
    cache = ColumnCache(
        cache_dir=d, max_cache_size_gb=size, local_mode=True, data_dir=workdir,
        eviction_policy=policy, schema_file=os.path.join(META, "tpcds_schema_registry.json"),
        value_file=os.path.join(META, "data_val_cols_custom.json"),
        size_file=os.path.join(META, "sizes_30gb", "column_sizes.json"),
        value_iter=it, tie_round_digits=DIGITS)
    schema = json.load(open(os.path.join(META, "tpcds_schema_registry.json")))
    paths = {t: f"{t}.parquet" for t in schema}
    qv = pd.read_csv(os.path.join(META, "tpcds_query_values_custom.csv"))[it].to_list()
    qs = [open(os.path.join(DUCK_Q, k)).read() for k in QUERY_KEYS]
    for q, v in zip(qs, qv):
        cache.replay_query(q, paths, value=v)
    warm = len(cache.eviction_log)
    for q, v in zip(qs, qv):
        cache.replay_query(q, paths, value=v if dynamic else 0)
    cache.conn.close()
    return cache.eviction_log, warm


def spark_run(size, it, dynamic, policy, spark, plan_paths, workdir):
    qv = pd.read_csv(os.path.join(META, "tpcds_query_values_custom.csv")).set_index("query_id")[it]
    qs = {k: open(os.path.join(SPARK_Q, k)).read() for k in QUERY_KEYS}
    vdi = SparkVDI(spark, round_digits=DIGITS)
    vdi.create({k: (qs[k], float(qv[k])) for k in QUERY_KEYS})
    hist = history_executions(os.path.join(ROOT, "value_generation", "tpcds_columns_in_queries_spark.json"),
                              1500, 0)
    vdi.seed_history(hist, end=datetime.now())
    sizes = json.load(open(os.path.join(META, "sizes_30gb", "column_sizes.json")))
    d = os.path.join(workdir, f"spark_{policy}_{size}_{it}_{int(dynamic)}")
    shutil.rmtree(d, ignore_errors=True)
    cache = PlacementCache(spark, vdi, policy=policy, cache_dir=d, max_cache_size_gb=size,
                           column_sizes=sizes, plan_paths=plan_paths, tie_round_digits=DIGITS)
    for k in QUERY_KEYS:
        cache.replay(k, qs[k], float(qv[k]))
    for k in QUERY_KEYS:
        cache.replay(k, qs[k], float(qv[k]) if dynamic else 0.0, write_data_value=dynamic)
    return cache.eviction_log


def main():
    ap = ArgumentParser()
    ap.add_argument("--data-dir", required=True, help="any TPC-DS Parquet dir (schemas only)")
    ap.add_argument("--sizes", default="2.75,3.5,5.0,7.5,13.75")
    ap.add_argument("--iters", default="0,2,4")
    ap.add_argument("--policies", default="vod,lru")
    args = ap.parse_args()
    data_dir = os.path.expanduser(args.data_dir)
    schema = json.load(open(os.path.join(META, "tpcds_schema_registry.json")))
    plan_paths = {t: os.path.join(data_dir, f"{t}.parquet") for t in schema}

    workdir = tempfile.mkdtemp(prefix="vdi_validate_")
    spark = build_spark(os.path.join(workdir, "warehouse"), master="local[4]",
                        with_listener=True, driver_memory="4g")
    failures = 0
    for policy in args.policies.split(","):
        for size in [float(s) for s in args.sizes.split(",")]:
            for it in args.iters.split(","):
                for dynamic in ((False, True) if policy == "vod" else (False,)):
                    t0 = time.time()
                    orig, warm = original_run(size, it, dynamic, policy, workdir)
                    t1 = time.time()
                    new = spark_run(size, it, dynamic, policy, spark, plan_paths, workdir)
                    t2 = time.time()
                    ok = orig == new
                    failures += not ok
                    print(f"{policy} size={size:<5} iter={it} {'dynamic' if dynamic else 'static '} "
                          f"evictions={len(orig)} (warm {warm}) "
                          f"cols={sum(len(e) for e in orig)} match={ok} "
                          f"original={t1 - t0:.1f}s spark={t2 - t1:.1f}s", flush=True)
                    if not ok:
                        for i, (a, b) in enumerate(zip(orig, new)):
                            if a != b:
                                print(f"  first divergence at eviction {i}:\n    original={a}\n    spark   ={b}")
                                break
                        if len(orig) != len(new):
                            print(f"  eviction counts differ: {len(orig)} vs {len(new)}")
    spark.stop()
    shutil.rmtree(workdir, ignore_errors=True)
    print("ALL MATCH" if failures == 0 else f"{failures} MISMATCHED RUNS")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
