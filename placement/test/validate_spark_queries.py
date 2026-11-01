"""
Check the Spark translation of the 99 TPC-DS queries and the VDI listener, locally.

For each query, against the same Parquet files (e.g. SF1 from DuckDB's dsdgen):
  1. run the DuckDB original and the Spark translation, compare result rows;
  2. compare the columns Spark's plan says it needs (columnsForSql, used to fetch) with
     the columns the listener logged after execution (they must be identical);
  3. report how Spark's column sets differ from the sqlglot ones the DuckDB harness used.

Usage (after `. run/spark_env_local.sh`):
    python3 test/validate_spark_queries.py --data-dir ~/tpcds_sf1_place [--queries 1,2,3]
Writes test/spark_query_validation.json and prints a summary.
"""

import datetime
import decimal
import json
import math
import os
import shutil
import sys
import tempfile
import time
from argparse import ArgumentParser

import duckdb

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from column_cache import ColumnCache  # noqa: E402
from column_cache.spark_session import build_spark, listener_object  # noqa: E402
from column_cache.vdi_store import DATA_VALUE_TABLE, TASK_VALUE_TABLE, SparkVDI  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DUCK_DIR = os.path.join(ROOT, "test", "example_queries", "tpcds")
SPARK_DIR = os.path.join(ROOT, "test", "example_queries", "tpcds_spark")
META = os.path.join(ROOT, "metadata")


def norm(v):
    if v is None:
        return None
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    return v


def rows_equal(a, b, rel=1e-6, abs_=1e-6):
    if len(a) != len(b):
        return False
    key = lambda r: tuple((x is None, str(x) if not isinstance(x, float) else round(x, 4)) for x in r)
    for ra, rb in zip(sorted(a, key=key), sorted(b, key=key)):
        if len(ra) != len(rb):
            return False
        for x, y in zip(ra, rb):
            if isinstance(x, float) or isinstance(y, float):
                if x is None or y is None or not math.isclose(float(x), float(y), rel_tol=rel, abs_tol=abs_):
                    return False
            elif x != y:
                return False
    return True


def main():
    ap = ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--queries", default=",".join(str(i) for i in range(1, 100)))
    ap.add_argument("--out", default=os.path.join(ROOT, "test", "spark_query_validation.json"))
    ap.add_argument("--driver-memory", default="8g")
    args = ap.parse_args()
    data_dir = os.path.expanduser(args.data_dir)

    schema = json.load(open(os.path.join(META, "tpcds_schema_registry.json")))
    workdir = tempfile.mkdtemp(prefix="vdi_qval_")
    spark = build_spark(os.path.join(workdir, "warehouse"), master="local[4]", with_listener=True,
                        driver_memory=args.driver_memory)
    SparkVDI(spark).create({f"{i:02d}.sql": (None, 1.0) for i in range(1, 100)})
    spark.conf.set("spark.vdi.placement.taskValueTable", TASK_VALUE_TABLE)
    spark.conf.set("spark.vdi.placement.dataValueTable", DATA_VALUE_TABLE)
    listener = listener_object(spark)
    for t in schema:
        spark.read.parquet(os.path.join(data_dir, f"{t}.parquet")).createOrReplaceTempView(t)

    duck = duckdb.connect()
    for t in schema:
        duck.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{os.path.join(data_dir, t)}.parquet')")

    # sqlglot column extraction exactly as the DuckDB harness does it (no data touched).
    sqlglot_cache = ColumnCache(
        cache_dir=os.path.join(workdir, "sqlglot_cache"), local_mode=True, data_dir=data_dir,
        schema_file=os.path.join(META, "tpcds_schema_registry.json"),
        value_file=os.path.join(META, "data_val_cols_custom.json"),
        size_file=os.path.join(META, "sizes_30gb", "column_sizes.json"))

    results = {}
    for i in [int(x) for x in args.queries.split(",")]:
        name = f"{i:02d}.sql"
        dq = open(os.path.join(DUCK_DIR, name)).read()
        sq = open(os.path.join(SPARK_DIR, name)).read()
        r = {"query": name}
        try:
            t = time.perf_counter()
            d_rows = [tuple(norm(v) for v in row) for row in duck.execute(dq).fetchall()]
            r["duckdb_s"] = time.perf_counter() - t
        except Exception as e:
            r["duckdb_error"] = str(e)[:300]
            d_rows = None
        try:
            planned = json.loads(listener.columnsForSql(spark._jsparkSession, sq))
            task_id = name
            spark.conf.set("spark.vdi.placement.taskId", task_id)
            spark.conf.set("spark.vdi.placement.execId", f"qval-{name}")
            t = time.perf_counter()
            s_rows = [tuple(norm(v) for v in row) for row in spark.sql(sq).collect()]
            r["spark_s"] = time.perf_counter() - t
            r["listener"] = listener.awaitExecution(f"qval-{name}", 600000)
            spark.conf.unset("spark.vdi.placement.execId")
            logged = {}
            for row in spark.sql(f"SELECT table_name, column_name FROM {DATA_VALUE_TABLE} "
                                 f"WHERE task_id = '{task_id}'").collect():
                logged.setdefault(row.table_name, []).append(row.column_name)
            logged = {t_: sorted(c) for t_, c in logged.items()}
            r["planned_eq_logged"] = planned == logged
            sg = {t_: sorted(c) for t_, c in sqlglot_cache.get_columns_for_tables(dq).items()}
            sp_set = {(t_, c) for t_, cs in planned.items() for c in cs}
            sg_set = {(t_, c) for t_, cs in sg.items() for c in cs}
            r["spark_cols"] = len(sp_set)
            r["sqlglot_cols"] = len(sg_set)
            r["only_spark"] = sorted(f"{a}.{b}" for a, b in sp_set - sg_set)
            r["only_sqlglot"] = sorted(f"{a}.{b}" for a, b in sg_set - sp_set)
            r["planned"] = planned
        except Exception as e:
            r["spark_error"] = str(e)[:300]
            s_rows = None
        if d_rows is not None and s_rows is not None:
            r["rows"] = [len(d_rows), len(s_rows)]
            r["match"] = rows_equal(d_rows, s_rows)
        results[name] = r
        print(f"{name}: match={r.get('match')} rows={r.get('rows')} "
              f"planned==logged={r.get('planned_eq_logged')} "
              f"cols spark/sqlglot={r.get('spark_cols')}/{r.get('sqlglot_cols')} "
              f"{'DUCK_ERR ' + r['duckdb_error'][:80] if 'duckdb_error' in r else ''}"
              f"{'SPARK_ERR ' + r['spark_error'][:120] if 'spark_error' in r else ''}", flush=True)

    if os.path.exists(args.out):  # merge into earlier results (re-running a subset)
        results = {**json.load(open(args.out)), **results}
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2, sort_keys=True)
    vals = list(results.values())
    print(f"\nresult match: {sum(1 for r in vals if r.get('match'))}/{len(vals)}; "
          f"planned==logged: {sum(1 for r in vals if r.get('planned_eq_logged'))}/{len(vals)}; "
          f"spark errors: {sum(1 for r in vals if 'spark_error' in r)}; "
          f"column sets differ from sqlglot: "
          f"{sum(1 for r in vals if r.get('only_spark') or r.get('only_sqlglot'))}")
    spark.stop()
    shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
