#!/usr/bin/env python
"""Convert dsdgen raw text to one Parquet file per table with Spark 3.5.5 (pyspark).

Usage: convert.py <SF> [--tables t1,t2] [--workers K]

Reads /mnt/tpcds/tpcds_raw/sf<SF>/<table>_<i>_<N>.dat (child order 1..N),
writes $PARQUET_ROOT/sf<SF>/<table>.parquet (single plain file).

Environment (both optional; unset reproduces the first R2D7 run exactly):
  PARQUET_ROOT  output root, default /mnt/tpcds/parquet
  RG_ROWS       if set, every row group except a file's last has exactly RG_ROWS rows
                (parquet-mr 1.13.1 has no row-count limit, so the byte limit is set to 1 and
                the size check is pinned to every RG_ROWS records; see WRITER_CONF).
                Unset: 128 MiB row groups (parquet.block.size = 134217728).

Row order = dsdgen generation order: each chunk file is read as its own DataFrame
forced to exactly one input partition (no splitting), the DataFrames are unioned in
child order and coalesce(1)'d; no shuffle/sort/repartition. Asserted at runtime.
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tpcds_schema as S  # noqa: E402

os.environ.setdefault("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64")

RAW = "/mnt/tpcds/tpcds_raw/sf{sf}"
PARQUET_ROOT = os.environ.get("PARQUET_ROOT", "/mnt/tpcds/parquet")
OUT = PARQUET_ROOT + "/sf{sf}"
BLOCK = 134217728  # 128 MiB row groups
RG_ROWS = int(os.environ["RG_ROWS"]) if os.environ.get("RG_ROWS") else None

# Parquet writer settings, applied both as spark.hadoop.* and as write options.
# RG_ROWS: InternalParquetRecordWriter.checkBlockSizeReached only measures the buffered size
# every parquet.page.size.row.check.{min,max} records; with a 1-byte block size the first
# check always flushes, so pinning min = max = RG_ROWS cuts a row group every RG_ROWS records.
# max-padding = 0 disables block alignment padding (meaningless with a 1-byte block size).
# Side effect: the same min/max also gate the page-size check, so pages are cut by
# parquet.page.row.count.limit (20,000 rows) rather than at ~1 MiB.
if RG_ROWS is None:
    WRITER_CONF = {"parquet.block.size": str(BLOCK)}
else:
    WRITER_CONF = {
        "parquet.block.size": "1",
        "parquet.page.size.row.check.min": str(RG_ROWS),
        "parquet.page.size.row.check.max": str(RG_ROWS),
        "parquet.writer.max-padding": "0",
    }
HUGE = str(1 << 40)  # 1 TiB: forces one partition per input file

SPARK_CONF = {
    "spark.master": "local[16]",
    "spark.driver.memory": "20g",
    "spark.local.dir": "/mnt/tpcds/spark-tmp",
    "spark.speculation": "false",
    "spark.ui.enabled": "false",
    "spark.sql.adaptive.enabled": "false",
    "spark.sql.files.maxPartitionBytes": HUGE,
    "spark.sql.files.openCostInBytes": HUGE,
    "spark.sql.csv.parser.columnPruning.enabled": "false",
    "spark.sql.parquet.compression.codec": "snappy",
    **{"spark.hadoop." + k: v for k, v in WRITER_CONF.items()},
    "spark.hadoop.parquet.enable.summary-metadata": "false",
}

CSV_OPTS = {
    "sep": "|",
    "header": "false",
    "quote": "",          # dsdgen never quotes; disable quote handling entirely
    "escape": "\\",
    "encoding": "UTF-8",  # all raw files are validated as UTF-8 before conversion (verify_raw_utf8)
    "mode": "FAILFAST",   # any unparseable value / wrong field count aborts the job
    "nullValue": "",
    "dateFormat": "yyyy-MM-dd",
    "multiLine": "false",
    "inferSchema": "false",
}


def chunk_files(sf, table):
    files = glob.glob(os.path.join(RAW.format(sf=sf), f"{table}_*_*.dat"))
    parsed = []
    for f in files:
        m = re.fullmatch(rf"{table}_(\d+)_(\d+)\.dat", os.path.basename(f))
        if m:
            parsed.append((int(m.group(1)), int(m.group(2)), f))
    if not parsed:
        raise RuntimeError(f"no chunks for {table}")
    ns = {n for _, n, _ in parsed}
    if len(ns) != 1:
        raise RuntimeError(f"{table}: mixed parallel counts {ns}")
    n = ns.pop()
    parsed.sort()
    kids = [c for c, _, _ in parsed]
    if kids != [1] and kids != list(range(1, n + 1)):
        raise RuntimeError(f"{table}: incomplete children {kids} of {n}")
    return [f for _, _, f in parsed], n


def build_spark():
    from pyspark.sql import SparkSession
    b = SparkSession.builder.appName("tpcds_to_parquet")
    for k, v in SPARK_CONF.items():
        b = b.config(k, v)
    return b.getOrCreate()


def convert_table(spark, sf, table, ddl):
    files, n = chunk_files(sf, table)
    files = [f for f in files if os.path.getsize(f) > 0]
    schema = S.read_schema(table, ddl)
    dfs = []
    for f in files:
        df = spark.read.options(**CSV_OPTS).schema(schema).csv("file://" + f)
        np_ = df.rdd.getNumPartitions()
        if np_ != 1:
            raise RuntimeError(f"{table}: {f} read as {np_} partitions (must be 1)")
        dfs.append(df)
    df = dfs[0]
    for d in dfs[1:]:
        df = df.union(d)
    df = df.drop(S.TRAILING).coalesce(1)
    tmp = os.path.join(OUT.format(sf=sf), f"_tmp_{table}")
    shutil.rmtree(tmp, ignore_errors=True)
    t0 = time.time()
    (df.write.mode("error")
       .option("compression", "snappy")
       .options(**WRITER_CONF)
       .parquet("file://" + tmp))
    secs = time.time() - t0
    parts = sorted(glob.glob(os.path.join(tmp, "part-*.parquet")))
    others = [p for p in os.listdir(tmp)
              if not p.startswith("part-") and not p.startswith(".") and p != "_SUCCESS"]
    if len(parts) != 1:
        raise RuntimeError(f"{table}: expected 1 part file, got {parts}")
    if others:
        raise RuntimeError(f"{table}: unexpected files in output dir: {others}")
    dest = os.path.join(OUT.format(sf=sf), f"{table}.parquet")
    if os.path.exists(dest):
        os.remove(dest)
    shutil.move(parts[0], dest)
    shutil.rmtree(tmp)
    return {"table": table, "chunks_read": len(files), "parallel_n": n,
            "write_seconds": round(secs, 1), "bytes": os.path.getsize(dest)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sf")
    ap.add_argument("--tables", default=None)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    sf = a.sf
    os.makedirs(OUT.format(sf=sf), exist_ok=True)
    tables = a.tables.split(",") if a.tables else S.TABLES
    ddl = S.parse_ddl()
    # biggest raw input first so the long tables start early
    size = {t: sum(os.path.getsize(f) for f in chunk_files(sf, t)[0]) for t in tables}
    tables = sorted(tables, key=lambda t: -size[t])

    spark = build_spark()
    jsc = spark.sparkContext._jsc
    hconf = jsc.hadoopConfiguration()
    effective = {
        "spark.version": spark.version,
        "java.version": spark.sparkContext._jvm.System.getProperty("java.version"),
        "parquet-mr": spark.sparkContext._jvm.org.apache.parquet.Version.FULL_VERSION,
        "spark_conf": {k: spark.conf.get(k, None) for k in SPARK_CONF
                       if not k.startswith("spark.hadoop.") and k not in ("spark.master", "spark.driver.memory", "spark.local.dir", "spark.speculation", "spark.ui.enabled")},
        "spark_core_conf": {k: spark.sparkContext.getConf().get(k, None) for k in ("spark.master", "spark.driver.memory", "spark.local.dir", "spark.speculation")},
        "hadoop_conf": {k: hconf.get(k) for k in (
            "parquet.block.size", "parquet.page.size", "parquet.dictionary.page.size",
            "parquet.enable.dictionary", "parquet.writer.version", "parquet.page.row.count.limit",
            "parquet.enable.summary-metadata")
            + tuple(k for k in WRITER_CONF if k != "parquet.block.size")},
        "spark_parquet_conf": {k: spark.conf.get(k, None) for k in (
            "spark.sql.parquet.writeLegacyFormat", "spark.sql.parquet.outputTimestampType",
            "spark.sql.parquet.fieldId.write.enabled")},
        "write_options": {"compression": "snappy", **WRITER_CONF},
        "csv_options": CSV_OPTS,
    }
    if RG_ROWS is not None:
        effective["parquet_root"] = PARQUET_ROOT
        effective["rg_rows"] = RG_ROWS
    print(json.dumps(effective, indent=1), flush=True)

    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(convert_table, spark, sf, t, ddl): t for t in tables}
        for fu in as_completed(futs):
            r = fu.result()  # re-raises -> fail loudly
            print(json.dumps(r), flush=True)
            results.append(r)
    total = time.time() - t0
    meta_path = os.path.join(OUT.format(sf=sf), "_convert_meta.json")
    prev = {}
    if a.tables and os.path.exists(meta_path):
        prev = {r["table"]: r for r in json.load(open(meta_path)).get("tables", [])}
    for r in results:
        prev[r["table"]] = r
    json.dump({"effective_settings": effective, "convert_wallclock_s": round(total, 1),
               "tables": sorted(prev.values(), key=lambda r: r["table"])},
              open(meta_path, "w"), indent=1)
    print(f"convert wallclock {total:.1f}s", flush=True)
    spark.stop()


if __name__ == "__main__":
    main()
