"""Build the Iceberg tables for the sorting experiment (run via run_phase.sh, not directly).

  base     all 24 TPC-DS tables, unsorted and unpartitioned, in namespace `base`, rows in
           source (dsdgen) order. Row groups hold exactly 128k rows, as in the DuckDB run
           (cluster.py), and files exactly 32 row groups; only a table's last row group is
           partial. Layouts reuse the per-table write properties, whose target file size
           is the measured size of 32 row groups.
  layouts  one table per (layout, mode) in namespace `<layout>_<mode>`, rows copied from
           `base`:
             s   WRITE ORDERED BY (sort cols)                    -- no partitioning
             ps  partitioned by a transform of c1 + WRITE ORDERED BY (sort cols)
             pz  partitioned by a transform of c1 + Z-order(sort cols), pilot only

Partition rule (identical for every strategy), P = min(--partitions, row groups of the
table in base):
  identity(c1)                   if approx NDV(c1) <= P
  truncate(ceil(range / P), c1)  integer and decimal types (keeps range locality)
  bucket(P, c1)                  string, date, timestamp
  none                           other types (recorded in the stats)

Every build is idempotent: a table carrying TBLPROPERTIES vdi.complete=true is skipped;
an incomplete one is dropped and rebuilt. Stats for each table are appended to --stats.
"""
import json
import math
import os
import sys
import time
from argparse import ArgumentParser

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark import StorageLevel

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from workload import P as WORKLOAD  # noqa: E402  (WORKLOAD=tpcds by default; see workload.py)
from pyspark.sql.types import (ByteType, DateType, DecimalType, IntegerType, LongType,
                               ShortType, StringType, TimestampType)

INTEGER_TYPES = (ByteType, ShortType, IntegerType, LongType)
BUCKET_TYPES = (StringType, DateType, TimestampType)  # decimals: truncate

# The source Parquet follows the official DSGen 4.0.0 DDL; the queries and the SQL-parsed
# column sets follow tpcds_schema/ (the DuckDB run). Two columns differ: source name ->
# (DuckDB-era name, cast type or None). c_last_review_date holds the date_sk as a string.
SCHEMA_FIXES = {
    "customer": {"c_last_review_date": ("c_last_review_date_sk", "int")},
    "store": {"s_tax_precentage": ("s_tax_percentage", None)},
}


def log(msg):
    print(f"[build_iceberg {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def append_stats(path, rec):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def table_exists(spark, ident):
    return spark.catalog.tableExists(ident)


def is_complete(spark, ident):
    if not table_exists(spark, ident):
        return False
    props = {r[0]: r[1] for r in spark.sql(f"SHOW TBLPROPERTIES {ident}").collect()}
    return props.get("vdi.complete") == "true"


def file_stats(spark, ident):
    """Files, row groups (split_offsets), rows and bytes from Iceberg metadata."""
    r = spark.sql(f"""
        SELECT count(*) AS files,
               coalesce(sum(size(split_offsets)), 0) AS row_groups,
               coalesce(sum(record_count), 0) AS rows,
               coalesce(sum(file_size_in_bytes), 0) AS bytes
        FROM {ident}.files""").collect()[0]
    parts = spark.sql(f"SELECT count(*) FROM {ident}.partitions").collect()[0][0]
    return {"files": r.files, "row_groups": r.row_groups, "rows": r.rows,
            "bytes": r.bytes, "partitions": parts}


def write_props(rg_rows, file_bytes):
    """Row groups of exactly rg_rows rows: Iceberg's writer checks the row-group size only
    every N records (N clamped to [check-min, check-max]); with both pinned to rg_rows and a
    1-byte threshold, the first check after rg_rows records always flushes."""
    return {
        "write.format.default": "parquet",
        "write.parquet.compression-codec": "zstd",
        "write.parquet.row-group-size-bytes": "1",
        "write.parquet.row-group-check-min-record-count": str(rg_rows),
        "write.parquet.row-group-check-max-record-count": str(rg_rows),
        "write.target-file-size-bytes": str(file_bytes),
        "write.spark.advisory-partition-size-bytes": str(file_bytes),
    }


def props_sql(props):
    return ", ".join(f"'{k}'='{v}'" for k, v in sorted(props.items()))


def source_path(source, table):
    for cand in (f"{source}/{table}.parquet", f"{source}/{table}"):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(f"no source for {table} under {source}")


def chunk_keys(spark, n):
    """Long keys k_0..k_{n-1} with pmod(hash(k_c), n) == c. Spark's hash repartitioning
    uses the same Murmur3 hash (seed 42) as hash(), so repartitioning on k_c sends chunk c
    to partition c: exactly one chunk per write task. Range repartitioning is sample-based
    and can merge neighbouring chunks."""
    rows = (spark.range(0, 1000 * n + 1000)
            .select("id", F.expr(f"pmod(hash(id), {n})").alias("p"))
            .groupBy("p").agg(F.min("id").alias("k")).collect())
    keys = {r.p: r.k for r in rows}
    assert len(keys) == n, f"no hash key for some of {n} partitions"
    return [keys[c] for c in range(n)]


def build_base(spark, args, tables):
    os.makedirs(os.path.dirname(os.path.abspath(args.base_props)), exist_ok=True)
    base_props = json.load(open(args.base_props)) if os.path.exists(args.base_props) else {}
    rebuild = set(args.rebuild.split(",")) if args.rebuild else set()
    chunk_rows = args.rg_rows * args.rgs_per_file
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {args.catalog}.base")
    # Read each source file as a single input partition, so monotonically_increasing_id()
    # is the row's position in the source (dsdgen generation order).
    saved = {k: spark.conf.get(k, None) for k in
             ("spark.sql.files.maxPartitionBytes", "spark.sql.files.openCostInBytes")}
    for k in saved:
        spark.conf.set(k, str(1 << 40))
    for t in tables:
        ident = f"{args.catalog}.base.{t}"
        if t not in rebuild and is_complete(spark, ident):
            log(f"base.{t}: complete, skipping")
            continue
        df = spark.read.parquet(source_path(args.source, t))
        fixes = SCHEMA_FIXES.get(t, {})
        for src_col, (name, typ) in fixes.items():
            df = df.withColumn(src_col, F.col(src_col).cast(typ) if typ else F.col(src_col))
            df = df.withColumnRenamed(src_col, name)
        # One input partition <=> ids run 0..n-1 (each further partition starts at p << 33).
        # Checked with a query, not df.rdd: the fork's row-group hook asserts that every
        # Parquet scan runs inside an SQL execution.
        n_rows, max_id = (df.select(F.monotonically_increasing_id().alias("_id"))
                            .agg(F.count("*"), F.max("_id")).first())
        assert max_id == n_rows - 1, f"{t}: source read as several partitions"

        # Files of exactly rgs_per_file row groups of exactly rg_rows rows, in source order:
        # cut the rows into contiguous chunks of rg_rows * rgs_per_file, one write task (and
        # so one file, with size-based rolling off) per chunk. Only the table's last row
        # group is partial. Writing straight from the input splits instead gives one file per
        # source row group, each ending in a partial row group.
        n_files = max(1, math.ceil(n_rows / chunk_rows))
        keys = chunk_keys(spark, n_files)
        key_map = F.create_map(*[F.lit(x).cast("long") for c, k in enumerate(keys) for x in (c, k)])
        out = (df.withColumn("_vdi_idx", F.monotonically_increasing_id())
                 .withColumn("_vdi_key", F.element_at(
                     key_map, F.floor(F.col("_vdi_idx") / chunk_rows).cast("long")))
                 .repartition(n_files, "_vdi_key")
                 .sortWithinPartitions("_vdi_idx")
                 .drop("_vdi_idx", "_vdi_key"))

        props = write_props(args.rg_rows, 1 << 30)
        df.createOrReplaceTempView("_src")
        spark.sql(f"DROP TABLE IF EXISTS {ident}")
        spark.sql(f"CREATE TABLE {ident} USING iceberg TBLPROPERTIES ({props_sql(props)}) "
                  f"AS SELECT * FROM _src WHERE false")
        t0 = time.time()
        (out.writeTo(ident)
            .option("distribution-mode", "none")
            .option("target-file-size-bytes", str(1 << 40))
            .append())
        st = file_stats(spark, ident)
        log(f"base.{t}: {st['files']} files, {st['row_groups']} row groups, "
            f"{st['rows']:,} rows, {time.time() - t0:.0f}s")
        assert st["rows"] == n_rows, f"{t}: wrote {st['rows']} rows, source has {n_rows}"
        assert st["files"] == n_files, f"{t}: {st['files']} files, expected {n_files}"
        assert st["row_groups"] == math.ceil(n_rows / args.rg_rows), \
            f"{t}: {st['row_groups']} row groups, expected {math.ceil(n_rows / args.rg_rows)}"

        # Target file size for the layouts (which reuse these properties): the measured
        # bytes of rgs_per_file row groups, for tables spanning more than one file.
        if st["row_groups"] > args.rgs_per_file:
            props = write_props(args.rg_rows,
                                int(st["bytes"] / st["row_groups"] * args.rgs_per_file))
        spark.sql(f"ALTER TABLE {ident} SET TBLPROPERTIES ({props_sql(props)}, "
                  f"'vdi.complete'='true')")
        base_props[t] = props
        with open(args.base_props, "w") as f:
            json.dump(base_props, f, indent=2)
        append_stats(args.stats, {"ns": "base", "table": t, "props": props, **st,
                                  "rows_per_row_group": st["rows"] / max(st["row_groups"], 1),
                                  "build": "chunked", "build_s": round(time.time() - t0, 1),
                                  "schema_fixes": {k: list(v) for k, v in fixes.items()}})
    for k, v in saved.items():
        if v is None:
            spark.conf.unset(k)
        else:
            spark.conf.set(k, v)


def partition_expr(spark, args, table, c1):
    """Partition transform of c1 (rule in the module docstring). P is capped at the table's
    row-group count in base, so a partition is not finer than a base row group: a layout
    then gains no pruning granularity the base does not have (Tapan, 2026-10-08)."""
    base = f"{args.catalog}.base.{table}"
    dtype = spark.table(base).schema[c1].dataType
    ndv, lo, hi = spark.sql(
        f"SELECT approx_count_distinct({c1}), min({c1}), max({c1}) FROM {base}").collect()[0]
    base_rgs = file_stats(spark, base)["row_groups"]
    p = min(args.partitions, base_rgs)
    if ndv <= p:
        expr = c1
    elif isinstance(dtype, INTEGER_TYPES):
        expr = f"truncate({math.ceil((hi - lo + 1) / p)}, {c1})"
    elif isinstance(dtype, DecimalType):
        # Range-preserving, like integers. Iceberg truncates the unscaled value, so the width
        # is in units of 10^-scale (Tapan, 2026-10-08: truncate, not bucket, for decimals).
        unscaled = int((hi - lo) * (10 ** dtype.scale)) + 1
        expr = f"truncate({math.ceil(unscaled / p)}, {c1})"
    elif isinstance(dtype, BUCKET_TYPES):
        expr = f"bucket({p}, {c1})"
    else:
        expr = None
    return expr, {"c1_type": dtype.simpleString(), "c1_ndv": ndv, "c1_min": str(lo),
                  "c1_max": str(hi), "partitions_target": p, "base_row_groups": base_rgs}


def write_chunked_sorted(spark, args, ident, src, part_sql, cols):
    """Write src into ident sorted by (partition, *cols), each partition cut into contiguous
    files of exactly rgs_per_file row groups of rg_rows rows; only a partition's last file
    (and row group) is partial. Writing through Iceberg's range distribution instead sizes
    files by shuffle bytes (~1.9x the zstd Parquet bytes), giving ~14 row groups per file.
    Returns {partition value: rows} as computed here, for the caller's checks."""
    chunk_rows = args.rg_rows * args.rgs_per_file
    part = F.expr(part_sql) if part_sql else F.lit(0)
    # Global sort, then each row's position in it. Persisted so the counts and the positions
    # come from one evaluation (ties between equal keys may otherwise reorder).
    srt = (src.withColumn("_vdi_part", part)
              .orderBy(F.col("_vdi_part").asc_nulls_first(),
                       *[F.col(c).asc_nulls_first() for c in cols])
              .withColumn("_vdi_pid", F.spark_partition_id())
              .withColumn("_vdi_mid", F.monotonically_increasing_id())
              .persist(StorageLevel.DISK_ONLY))
    try:
        counts = {r["_vdi_pid"]: r["count"] for r in srt.groupBy("_vdi_pid").count().collect()}
        offset, acc = {}, 0
        for pid in sorted(counts):
            offset[pid], acc = acc, acc + counts[pid]
        idx = (F.element_at(F.create_map(*[F.lit(x).cast("long") for p, o in offset.items()
                                           for x in (p, o)]), F.col("_vdi_pid").cast("long"))
               + F.col("_vdi_mid") - F.shiftleft(F.col("_vdi_pid").cast("long"), 33))
        srt2 = srt.withColumn("_vdi_idx", idx)
        # Partitions are contiguous ranges of idx (the sort is partition-first).
        parts = sorted(srt2.groupBy("_vdi_part").agg(F.min("_vdi_idx").alias("lo"),
                                                     F.count("*").alias("n")).collect(),
                       key=lambda r: r["lo"])
        chunk_of, base_chunk, n_tasks = None, 0, 0
        for r in parts:
            hi = r["lo"] + r["n"]
            c = F.lit(base_chunk) + F.floor((F.col("_vdi_idx") - r["lo"]) / chunk_rows)
            chunk_of = (F.when(F.col("_vdi_idx") < hi, c) if chunk_of is None
                        else chunk_of.when(F.col("_vdi_idx") < hi, c))
            base_chunk += math.ceil(r["n"] / chunk_rows)
        n_tasks = base_chunk
        keys = chunk_keys(spark, n_tasks)
        key_map = F.create_map(*[F.lit(x).cast("long") for c, k in enumerate(keys) for x in (c, k)])
        out = (srt2.withColumn("_vdi_key", F.element_at(key_map, chunk_of.cast("long")))
                   .repartition(n_tasks, "_vdi_key")
                   .sortWithinPartitions("_vdi_idx")
                   .drop("_vdi_part", "_vdi_pid", "_vdi_mid", "_vdi_idx", "_vdi_key"))
        (out.writeTo(ident)
            .option("distribution-mode", "none")
            .option("target-file-size-bytes", str(1 << 40))
            .append())
    finally:
        srt.unpersist()
    return [r["n"] for r in parts], n_tasks


def build_layout(spark, args, lid, layout, mode, base_props):
    t, cols = layout["table"], layout["sort_cols"]
    ns = f"{lid}_{mode}"
    ident = f"{args.catalog}.{ns}.{t}"
    expr, c1_info = (None, {}) if mode == "s" else partition_expr(spark, args, t, cols[0])
    if ns not in args.rebuild.split(",") and is_complete(spark, ident):
        props_now = {r[0]: r[1] for r in spark.sql(f"SHOW TBLPROPERTIES {ident}").collect()}
        if props_now.get("vdi.partition", "") == (expr or ""):
            log(f"{ns}.{t}: complete, skipping")
            return
        log(f"{ns}.{t}: stale (partition {props_now.get('vdi.partition')!r}, rule now "
            f"{expr!r}), rebuilding")
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {args.catalog}.{ns}")
    spark.sql(f"DROP TABLE IF EXISTS {ident}")
    part = f"PARTITIONED BY ({expr})" if expr else ""
    chunked = mode in ("s", "ps")
    props = dict(base_props[t]) if chunked else dict(base_props[t], **{"write.distribution-mode": "range"})
    t0 = time.time()
    spark.sql(f"CREATE TABLE {ident} USING iceberg {part} TBLPROPERTIES ({props_sql(props)}) "
              f"AS SELECT * FROM {args.catalog}.base.{t} WHERE false")
    spark.sql(f"ALTER TABLE {ident} WRITE ORDERED BY {', '.join(cols)}")
    expect = {}
    if chunked:
        # Same partition function Iceberg applies (its Spark functions), for the chunking.
        part_sql = None
        if expr:
            part_sql = expr if expr == cols[0] else f"{args.catalog}.system.{expr}"
        part_rows, n_files = write_chunked_sorted(
            spark, args, ident, spark.table(f"{args.catalog}.base.{t}"), part_sql, cols)
        expect = {"files": n_files,
                  "row_groups": sum(math.ceil(n / args.rg_rows) for n in part_rows)}
    else:
        spark.sql(f"INSERT INTO {ident} SELECT * FROM {args.catalog}.base.{t}")
    if mode == "pz":
        spark.sql(f"""CALL {args.catalog}.system.rewrite_data_files(
            table => '{ns}.{t}', strategy => 'sort',
            sort_order => 'zorder({", ".join(cols)})',
            options => map('rewrite-all', 'true'))""")
    st = file_stats(spark, ident)
    n_base = file_stats(spark, f"{args.catalog}.base.{t}")["rows"]
    assert st["rows"] == n_base, f"{ns}.{t}: {st['rows']} rows, base has {n_base}"
    for k, v in expect.items():
        assert st[k] == v, f"{ns}.{t}: {st[k]} {k}, expected {v}"
    if expect:
        assert st["partitions"] == len(part_rows), \
            f"{ns}.{t}: {st['partitions']} Iceberg partitions, chunking assumed {len(part_rows)}"
    spark.sql(f"ALTER TABLE {ident} SET TBLPROPERTIES ('vdi.complete'='true', "
              f"'vdi.layout'='{lid}', 'vdi.mode'='{mode}', "
              f"'vdi.sort_cols'='{','.join(cols)}', 'vdi.partition'='{expr or ''}')")
    log(f"{ns}.{t}: {cols} partition={expr} -> {st['files']} files, "
        f"{st['row_groups']} row groups, {st['partitions']} partitions, {time.time() - t0:.0f}s")
    append_stats(args.stats, {"ns": ns, "table": t, "layout": lid, "mode": mode,
                              "sort_cols": cols, "partition": expr, **c1_info, **st,
                              "build": "chunked" if chunked else "range",
                              "build_s": round(time.time() - t0, 1)})


def main():
    ap = ArgumentParser()
    ap.add_argument("what", choices=["base", "layouts"])
    ap.add_argument("--catalog", default="vdi")
    ap.add_argument("--source", help="dir of <table>.parquet (base only)")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--modes", default="ps", help="comma-separated: s,ps,pz")
    ap.add_argument("--layouts", default="all", help="comma-separated layout ids, or all")
    ap.add_argument("--partitions", type=int, default=32)
    ap.add_argument("--rg-rows", type=int, default=128_000)
    ap.add_argument("--rgs-per-file", type=int, default=32)
    ap.add_argument("--rebuild", default="",
                    help="rebuild even if complete: base tables (base) or <layout>_<mode> "
                         "namespaces (layouts), comma-separated")
    ap.add_argument("--base-props", required=True, help="json: per-table write properties")
    ap.add_argument("--stats", required=True, help="jsonl: per-table build stats")
    args = ap.parse_args()

    spark = SparkSession.builder.appName(f"build_iceberg {args.what}").getOrCreate()
    manifest = json.load(open(args.manifest))
    tables = sorted(json.load(open(WORKLOAD["row_counts_json"])))

    if args.what == "base":
        assert args.source, "--source is required for base"
        build_base(spark, args, tables)
        latest = {r["table"]: r for r in map(json.loads, open(args.stats)) if r["ns"] == "base"}
        eligible = {t for t, r in latest.items() if r["row_groups"] > 1}
        expected = set(manifest["params"]["eligible_tables"])
        if eligible != expected:
            log(f"WARNING: multi-row-group tables differ from the manifest: "
                f"extra {sorted(eligible - expected)}, missing {sorted(expected - eligible)}")
        else:
            log(f"multi-row-group tables match the manifest ({len(eligible)})")
    else:
        base_props = json.load(open(args.base_props))
        ids = sorted(manifest["layouts"]) if args.layouts == "all" else args.layouts.split(",")
        for lid in ids:
            for mode in args.modes.split(","):
                build_layout(spark, args, lid, manifest["layouts"][lid], mode, base_props)
    spark.stop()


if __name__ == "__main__":
    main()
