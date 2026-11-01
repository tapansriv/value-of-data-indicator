"""
Per-query column sets from Spark, for value_generation/spark_baselines.py.

Each Spark-dialect query is executed once with the VDI listener writing Data Value rows,
and the columns it logged are written out in the format of tpcds_columns_in_queries.json:
{"01.sql": {"customer": ["c_customer_id", ...], ...}, ...}. The planned (pre-execution)
sets are recorded alongside and must match; a mismatch is reported and fails the run.

Only the schema matters for the column sets, so any scale factor works (SF1 locally).

Usage (after `. run/spark_env_local.sh`):
    python3 tools/extract_spark_columns.py --data-dir ~/tpcds_sf1_place
"""
import json
import os
import shutil
import sys
import tempfile
from argparse import ArgumentParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from column_cache.spark_session import build_spark, listener_object  # noqa: E402
from column_cache.vdi_store import DATA_VALUE_TABLE, TASK_VALUE_TABLE, SparkVDI  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
SPARK_DIR = os.path.join(ROOT, "test", "example_queries", "tpcds_spark")
META = os.path.join(ROOT, "metadata")


def main():
    ap = ArgumentParser()
    ap.add_argument("--data-dir", required=True,
                    help="directory (or s3a:// prefix) holding <table>.parquet")
    ap.add_argument("--out", default=os.path.join(ROOT, "value_generation",
                                                  "tpcds_columns_in_queries_spark.json"))
    args = ap.parse_args()
    data_dir = os.path.expanduser(args.data_dir)

    schema = json.load(open(os.path.join(META, "tpcds_schema_registry.json")))
    workdir = tempfile.mkdtemp(prefix="vdi_cols_")
    spark = build_spark(os.path.join(workdir, "warehouse"), master="local[4]", with_listener=True,
                        driver_memory="8g")
    SparkVDI(spark).create({f"{i:02d}.sql": (None, 1.0) for i in range(1, 100)})
    spark.conf.set("spark.vdi.placement.taskValueTable", TASK_VALUE_TABLE)
    spark.conf.set("spark.vdi.placement.dataValueTable", DATA_VALUE_TABLE)
    listener = listener_object(spark)
    for t in schema:
        spark.read.parquet(f"{data_dir.rstrip('/')}/{t}.parquet").createOrReplaceTempView(t)

    logged_all, mismatched = {}, []
    for i in range(1, 100):
        name = f"{i:02d}.sql"
        sql = open(os.path.join(SPARK_DIR, name)).read()
        planned = json.loads(listener.columnsForSql(spark._jsparkSession, sql))
        task_id = name
        spark.conf.set("spark.vdi.placement.taskId", task_id)
        spark.conf.set("spark.vdi.placement.execId", f"extract-{name}")
        spark.sql(sql).collect()
        status = listener.awaitExecution(f"extract-{name}", 600000)
        spark.conf.unset("spark.vdi.placement.execId")
        if not status.startswith("ok"):
            raise RuntimeError(f"{name}: listener {status}")
        logged = {}
        for row in spark.sql(f"SELECT table_name, column_name FROM {DATA_VALUE_TABLE} "
                             f"WHERE task_id = '{task_id}'").collect():
            logged.setdefault(row.table_name, []).append(row.column_name)
        logged = {t: sorted(c) for t, c in sorted(logged.items())}
        if logged != planned:
            mismatched.append(name)
        logged_all[name] = logged
        print(f"{name}: {sum(len(c) for c in logged.values())} columns", flush=True)

    with open(args.out, "w") as f:
        json.dump(logged_all, f, indent=4, sort_keys=True)
    spark.stop()
    shutil.rmtree(workdir, ignore_errors=True)
    print(f"wrote {args.out}")
    if mismatched:
        print(f"planned != logged for: {mismatched}")
        sys.exit(1)


if __name__ == "__main__":
    main()
