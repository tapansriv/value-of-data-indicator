#!/usr/bin/env python
"""Write $PARQUET_ROOT/sf<SF>/DATAGEN_NOTES.md from the logs/json the pipeline produced.
PARQUET_ROOT defaults to /mnt/tpcds/parquet (env, as for convert.py).
Usage: make_notes.py <SF> [--extra "free text"]"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tpcds_schema as S  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sf")
    ap.add_argument("--extra", default="")
    a = ap.parse_args()
    sf = a.sf
    raw_dir = f"/mnt/tpcds/tpcds_raw/sf{sf}"
    pq_dir = os.path.join(os.environ.get("PARQUET_ROOT", "/mnt/tpcds/parquet"), f"sf{sf}")
    gen_meta = open(os.path.join(raw_dir, "_gen_logs", "gen_meta.txt")).read()
    raw = json.load(open(os.path.join(raw_dir, "_raw_check.json")))
    conv = json.load(open(os.path.join(pq_dir, "_convert_meta.json")))
    ver = json.load(open(os.path.join(pq_dir, "_verify.json")))
    eff = conv["effective_settings"]
    vt = {r["table"]: r for r in ver["tables"]}
    ct = {r["table"]: r for r in conv["tables"]}
    import pyarrow
    java = subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.strip().splitlines()[0]

    L = []
    L.append(f"# TPC-DS SF{sf}: raw text + Parquet (one file per table)\n")
    L.append("Generated for the R2D7 row-group access capture. Produced by the scripts in "
             f"`{HERE}/` (gen.sh, convert.py, verify.py, tpcds_schema.py, make_notes.py).\n")
    L.append("## Data generation (dsdgen)\n")
    L.append("- dsdgen: TPC-DS tools version 4.0.0, `/home/cc/DSGen-software-code-4.0.0/tools/dsdgen` "
             f"(sha256 {sha('/home/cc/DSGen-software-code-4.0.0/tools/dsdgen')[:16]}…, "
             f"tpcds.idx sha256 {sha('/home/cc/DSGen-software-code-4.0.0/tools/tpcds.idx')[:16]}…)")
    L.append("- RNG seed: 19620718 (passed explicitly; this is also dsdgen's default)")
    L.append(f"- Raw output: `{raw_dir}/<table>_<child>_<N>.dat` (kept). dsdgen run with cwd = tools dir.")
    L.append("- Tables whose dsdgen row count is < 1,000,000 (for sales tables: orders/tickets) are emitted "
             "only by child 1; larger tables are split into N contiguous row ranges. Concatenating children "
             "1..N reproduces the serial output byte-for-byte (checked for all 24 tables at SF1, serial vs -parallel 4 and 8).")
    L.append("- gen log:\n```\n" + gen_meta.strip() + "\n```\n")
    L.append("## Encoding\n")
    bad = raw["invalid_utf8"]
    na = {t: v["nonascii_chars"] for t, v in raw["tables"].items() if v["nonascii_chars"]}
    L.append(f"- Every raw chunk was decoded with a strict UTF-8 decoder before conversion: "
             f"{'ALL VALID' if not bad else 'INVALID FILES: ' + str(bad)}.")
    L.append(f"- Non-ASCII (valid UTF-8) characters found: {na or 'none'} "
             "(customer.c_birth_country values such as `CÔTE D'IVOIRE`, `RÉUNION`). "
             "Spark reads with encoding=UTF-8, so these round-trip unchanged; no bytes were replaced or dropped.\n")
    L.append("## Parquet conversion\n")
    L.append(f"- Writer: Apache Spark {eff['spark.version']} (pip pyspark==3.5.5), bundled {eff['parquet-mr']}; "
             f"JVM java.version={eff['java.version']} ({java})")
    L.append("- Footer created_by: `" + next(iter(vt.values()))["created_by"] + "`")
    L.append("- Spark: " + ", ".join(f"{k}={v}" for k, v in eff["spark_core_conf"].items()) + ", "
             + ", ".join(f"{k}={v}" for k, v in eff["spark_conf"].items()))
    if "rg_rows" in eff:
        wo = {k: v for k, v in eff["write_options"].items() if k != "compression"}
        L.append(f"- Row groups: exactly {eff['rg_rows']:,} rows each except each file's last "
                 "(asserted by verify.py). parquet-mr 1.13.1 has no row-count limit, so the writer is set to "
                 + ", ".join(f"{k}={v}" for k, v in wo.items()) + " (set both as spark.hadoop.* and as "
                 "write options): with a 1-byte block size the size check, which runs every "
                 "page.size.row.check.{min,max} records, always flushes. Side effect: the same min/max gate "
                 "the page-size check, so pages are cut at page.row.count.limit (20,000 rows) rather than ~1 MiB.")
        blk = "Other writer settings: "
    else:
        blk = ("parquet.block.size=134217728 (128 MiB row groups; set both as "
               "spark.hadoop.parquet.block.size and as the write option), ")
    L.append("- Parquet writer: " + blk + "compression=snappy, "
             "parquet.enable.summary-metadata=false. Everything else at Spark 3.5.5 / parquet-mr 1.13.1 "
             "defaults (driver Hadoop conf, null = unset so the default applies: " + json.dumps(eff["hadoop_conf"]) + "; Spark: "
             + json.dumps(eff["spark_parquet_conf"]) + "). Those defaults are: parquet.page.size=1 MiB, "
             "parquet.dictionary.page.size=1 MiB, dictionary enabled, writer version PARQUET_1_0, "
             "page.row.count.limit=20000, spark.sql.parquet.writeLegacyFormat=false (decimals with "
             "precision<=9 as INT32, <=18 as INT64).")
    enc = sorted({e for r in vt.values() for e in r["rg0_encodings"]})
    L.append(f"- Observed in footers: codecs {sorted({c for r in vt.values() for c in r['rg0_codecs']})}, encodings {enc}")
    L.append("- CSV read options: `" + json.dumps(eff["csv_options"]) + "`; spark.sql.csv.parser.columnPruning.enabled=false "
             "so every field of every line is parsed; FAILFAST aborts on any unparseable value or wrong field count.")
    L.append("- Schema: explicit, from tools/tpcds.sql (integer->int32, decimal(p,s)->decimal(p,s), date->date32, "
             "char/varchar->string); column names exactly as in the DDL. The trailing `|` yields an extra empty "
             "field that is read into a placeholder column and dropped. Empty fields are NULL.")
    L.append("- Row order = dsdgen generation order: each chunk file is read as its own DataFrame, forced to exactly one "
             "input partition (spark.sql.files.maxPartitionBytes = openCostInBytes = 1 TiB; asserted at runtime), "
             "unioned in child order 1..N, coalesce(1), written. No repartition/shuffle/sort. The single "
             "part-*.parquet was moved to `<table>.parquet` and the Spark output directory removed.")
    L.append(f"- Convert wall-clock (all tables, up to 8 tables concurrently in one Spark app): {conv['convert_wallclock_s']} s\n")
    L.append("## Verification\n")
    modes = sorted({r["compare_mode"] for r in vt.values()})
    L.append("- raw line count (sum over chunks) == Parquet footer num_rows for every table; schema == DDL; "
             "no column 100% NULL except the known always-empty dsdgen columns c_login and cc_closed_date_sk "
             "(from row-group null_count statistics).")
    L.append(f"- Row content/order: rows re-rendered from Parquet compared byte-for-byte to raw lines "
             f"(decimals compared at column scale, since dsdgen prints e.g. gmt_offset `-5` for decimal(5,2)). "
             f"Mode: {modes}.")
    L.append(f"- Verification result: {'PASSED' if not ver['errors'] else 'FAILED: ' + str(ver['errors'])}; "
             f"checked with pyarrow {pyarrow.__version__}.")
    spot = []
    for t, c in (("store_sales", "ss_sold_date_sk"), ("store_sales", "ss_net_paid"), ("date_dim", "d_date"),
                 ("catalog_sales", "cs_sold_date_sk"), ("inventory", "inv_quantity_on_hand")):
        r = vt[t]
        spot.append(f"{t}.{c}: {r['null_counts'][c]:,} NULL of {r['parquet_rows']:,}")
    L.append("- Spot-check NULL counts: " + "; ".join(spot) + "\n")
    L.append("## Per-table results\n")
    L.append("| table | raw rows | parquet rows | row groups | rows/RG min–max | parquet bytes | raw bytes | chunks | convert s |")
    L.append("|---|---:|---:|---:|---|---:|---:|---:|---:|")
    tot_pq = tot_raw = 0
    for t in S.TABLES:
        r, rr, c = vt[t], raw["tables"][t], ct[t]
        mm = r["row_group_rows_min_max"]
        L.append(f"| {t} | {rr['raw_rows']:,} | {r['parquet_rows']:,} | {r['row_groups']} | "
                 f"{mm[0]:,}–{mm[1]:,} | {r['bytes']:,} | {rr['raw_bytes']:,} | {c['chunks_read']} | {c['write_seconds']} |")
        tot_pq += r["bytes"]
        tot_raw += rr["raw_bytes"]
    L.append(f"| **total** | | | | | {tot_pq:,} | {tot_raw:,} | | |\n")
    L.append("## Sanity vs TPC-DS expectations\n")
    ss = vt["store_sales"]["parquet_rows"]
    L.append(f"- store_sales = {ss:,} rows = {ss / float(sf) / 1e6:.4f} M x SF (expect ≈ 2.88 M x SF)")
    L.append(f"- date_dim = {vt['date_dim']['parquet_rows']:,} (expect 73,049 at every SF); "
             f"time_dim = {vt['time_dim']['parquet_rows']:,} (expect 86,400); "
             f"customer_demographics = {vt['customer_demographics']['parquet_rows']:,} (expect 1,920,800); "
             f"item = {vt['item']['parquet_rows']:,}\n")
    if a.extra:
        L.append("## Notes\n")
        L.append(a.extra + "\n")
    open(os.path.join(pq_dir, "DATAGEN_NOTES.md"), "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
