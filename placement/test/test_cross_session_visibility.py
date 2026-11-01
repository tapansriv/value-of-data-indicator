"""
Data Value rows the listener appends (through the query session) must be visible to the
next VDI lookup (through SparkVDI's own session) immediately. Iceberg's SparkCatalog caches
tables per session (cache-enabled, 30 s by default) and does not refresh a cached table,
so without spark.sql.catalog.vdi.cache-enabled=false the lookup reads stale values.
Also checks static mode: with writeDataValue=false the listener appends nothing.

    . run/spark_env_local.sh && python3 test/test_cross_session_visibility.py --data-dir ~/tpcds_sf1_place
    (add --catalog-cache to see the failure with Iceberg's default)
"""
import os
import shutil
import sys
import tempfile
from argparse import ArgumentParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from column_cache.spark_session import build_spark, listener_object  # noqa: E402
from column_cache.vdi_store import DATA_VALUE_TABLE, TASK_VALUE_TABLE, SparkVDI  # noqa: E402

QUERY = ("SELECT i_brand, SUM(ss_ext_sales_price) FROM store_sales "
         "JOIN item ON ss_item_sk = i_item_sk GROUP BY i_brand")
N_COLS = 4  # i_brand, i_item_sk, ss_ext_sales_price, ss_item_sk


def main():
    ap = ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--catalog-cache", action="store_true",
                    help="force Iceberg's catalog cache on (default in Iceberg)")
    args = ap.parse_args()
    workdir = tempfile.mkdtemp(prefix="vdi_vis_")
    extra = {"spark.sql.catalog.vdi.cache-enabled": "true"} if args.catalog_cache else None
    spark = build_spark(os.path.join(workdir, "wh"), master="local[4]", with_listener=True,
                        driver_memory="4g", extra_conf=extra)
    vdi = SparkVDI(spark)
    vdi.create({"t1": (QUERY, 100.0)})
    exec_session = spark.newSession()
    exec_session.conf.set("spark.vdi.placement.taskValueTable", TASK_VALUE_TABLE)
    exec_session.conf.set("spark.vdi.placement.dataValueTable", DATA_VALUE_TABLE)
    exec_session.conf.set("spark.vdi.placement.taskId", "t1")
    listener = listener_object(spark)
    for t in ("store_sales", "item"):
        exec_session.read.parquet(os.path.join(os.path.expanduser(args.data_dir), f"{t}.parquet")) \
            .createOrReplaceTempView(t)

    key = ("item", "i_brand")
    vdi.eviction_order([(key[0], key[1], 1, 0, True)])  # load (and, with caching, cache) tables
    failures = 0
    expected = 0.0
    for i, write in enumerate([True, True, False, True]):
        exec_session.conf.set("spark.vdi.placement.execId", f"vis{i}")
        exec_session.conf.set("spark.vdi.placement.writeDataValue", str(write).lower())
        exec_session.sql(QUERY).collect()
        status = listener.awaitExecution(f"vis{i}", 600000)
        expected += 100.0 / N_COLS if write else 0.0
        got = vdi.data_values().get(key, 0.0)
        ok = abs(got - expected) < 1e-9
        failures += not ok
        print(f"query {i} ({'dynamic' if write else 'static '}): listener={status} "
              f"VDI(item.i_brand)={got:.2f}, expected {expected:.2f} -> {'OK' if ok else 'STALE/WRONG'}")
    spark.stop()
    shutil.rmtree(workdir, ignore_errors=True)
    print("PASS" if failures == 0 else "FAIL")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
