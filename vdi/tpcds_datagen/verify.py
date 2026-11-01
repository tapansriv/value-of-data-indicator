#!/usr/bin/env python
"""Verification for one scale factor.

  verify.py raw <SF>              UTF-8 validation + line counts of every raw chunk  -> raw/_raw_check.json
  verify.py parquet <SF> [--full] footer checks + row-text comparison vs raw          -> parquet/_verify.json

Parquet checks (fail loudly -> nonzero exit):
  * exactly one <table>.parquet per table, no other *.parquet entries
  * footer num_rows == raw line count (sum over chunks)
  * schema == DDL (names, order, types)
  * no column is 100% null (from row-group statistics null_count)
  * if RG_ROWS is set (env, as for convert.py): every row group except the file's last has
    exactly RG_ROWS rows, and the last has 1..RG_ROWS
  * row order/content: rows re-rendered from Parquet in dsdgen text format are
    byte-identical to the raw lines. Default: first/last 100 lines of every chunk.
    --full: every row of every table.
"""
import argparse
import codecs
import datetime
import decimal
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tpcds_schema as S  # noqa: E402
from convert import chunk_files, RAW, OUT, RG_ROWS  # noqa: E402

EDGE = 100
# Columns that dsdgen leaves empty in every row (confirmed against raw text at SF1 by the
# full row comparison): reported as a note, not an error. Any other all-null column fails.
KNOWN_ALL_NULL = {"c_login", "cc_closed_date_sk"}


def scan_file(path):
    dec = codecs.getincrementaldecoder("utf-8")("strict")
    lines = 0
    nonascii = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 26)
            if not b:
                break
            lines += b.count(b"\n")
            try:
                s = dec.decode(b)
            except UnicodeDecodeError as e:
                return {"path": path, "lines": None, "utf8_ok": False, "error": str(e)}
            if not s.isascii():
                nonascii += sum(1 for ch in s if ord(ch) > 127)
        dec.decode(b"", final=True)
        f.seek(0, 2)
        size = f.tell()
        if size:
            f.seek(size - 1)
            if f.read(1) != b"\n":
                lines += 1
    return {"path": path, "lines": lines, "utf8_ok": True, "nonascii_chars": nonascii, "bytes": size}


def cmd_raw(sf):
    jobs = []
    for t in S.TABLES:
        files, n = chunk_files(sf, t)
        jobs += [(t, f) for f in files]
    with ProcessPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(scan_file, [f for _, f in jobs]))
    out = {}
    bad = []
    for (t, f), r in zip(jobs, res):
        e = out.setdefault(t, {"raw_rows": 0, "raw_bytes": 0, "chunks": 0, "nonascii_chars": 0})
        if not r["utf8_ok"]:
            bad.append(r)
            continue
        e["raw_rows"] += r["lines"]
        e["raw_bytes"] += r["bytes"]
        e["chunks"] += 1
        e["nonascii_chars"] += r["nonascii_chars"]
        e.setdefault("file_lines", {})[os.path.basename(f)] = r["lines"]
    p = os.path.join(RAW.format(sf=sf), "_raw_check.json")
    json.dump({"tables": out, "invalid_utf8": bad}, open(p, "w"), indent=1)
    for t in S.TABLES:
        print(t, {k: v for k, v in out[t].items() if k != "file_lines"})
    if bad:
        print("INVALID UTF-8:", json.dumps(bad, indent=1))
        sys.exit(2)
    print("all raw files valid UTF-8 ->", p)


def render(v):
    if v is None:
        return ""
    if isinstance(v, decimal.Decimal):
        return str(v)
    if isinstance(v, datetime.date):
        return v.isoformat()
    return str(v)


def render_rows(tbl):
    cols = [c.to_pylist() for c in tbl.columns]
    return ["|".join(render(c[i]) for c in cols) + "|" for i in range(tbl.num_rows)]


def raw_normalizer(table):
    """raw line -> canonical text: decimal fields re-rendered at the column scale."""
    scales = {}
    for j, (c, t) in enumerate(S.parse_ddl()[table]):
        if t.startswith("decimal("):
            scales[j] = decimal.Decimal(1).scaleb(-int(t[:-1].split(",")[1]))
    if not scales:
        return lambda line: line

    def norm(line):
        toks = line.split("|")
        for j, q in scales.items():
            if toks[j] != "":
                toks[j] = str(decimal.Decimal(toks[j]).quantize(q))
        return "|".join(toks)
    return norm


def edge_lines(path, k):
    """first k and last k lines (as str, no newline) plus total line count."""
    import subprocess
    head = subprocess.run(["head", "-n", str(k), path], capture_output=True, check=True).stdout
    tail = subprocess.run(["tail", "-n", str(k), path], capture_output=True, check=True).stdout
    return head.decode("utf-8").splitlines(), tail.decode("utf-8").splitlines()


def check_table(args):
    sf, table, full, raw_rows_expected, file_lines = args
    import pyarrow as pa
    import pyarrow.parquet as pq
    ddl = S.parse_ddl()
    path = os.path.join(OUT.format(sf=sf), f"{table}.parquet")
    pf = pq.ParquetFile(path)
    md = pf.metadata
    errs = []
    r = {"table": table, "parquet_rows": md.num_rows, "row_groups": md.num_row_groups,
         "bytes": os.path.getsize(path), "raw_rows": raw_rows_expected,
         "created_by": md.created_by}
    if md.num_rows != raw_rows_expected:
        errs.append(f"row count mismatch parquet={md.num_rows} raw={raw_rows_expected}")
    # schema
    want = []
    for c, t in ddl[table]:
        st = S.spark_type(t).simpleString()
        if st == "int":
            at = pa.int32()
        elif st == "bigint":
            at = pa.int64()
        elif st == "date":
            at = pa.date32()
        elif st == "string":
            at = pa.string()
        else:
            p, s = st[len("decimal("):-1].split(",")
            at = pa.decimal128(int(p), int(s))
        want.append((c, at))
    got = [(f.name, f.type) for f in pf.schema_arrow]
    if got != want:
        errs.append(f"schema mismatch got={got} want={want}")
    # nulls from stats
    nulls = {}
    for j in range(md.num_columns):
        name = md.schema.column(j).name
        n = 0
        for i in range(md.num_row_groups):
            st = md.row_group(i).column(j).statistics
            if st is None or not st.has_null_count:
                n = None
                break
            n += st.null_count
        nulls[name] = n
    allnull = [c for c, n in nulls.items() if n is not None and md.num_rows > 0 and n == md.num_rows]
    r["all_null_columns"] = allnull
    unexpected = [c for c in allnull if c not in KNOWN_ALL_NULL]
    if unexpected:
        errs.append(f"unexpected all-null columns: {unexpected}")
    r["null_counts"] = nulls
    rg_rows = [md.row_group(i).num_rows for i in range(md.num_row_groups)]
    r["row_group_rows_min_max"] = [min(rg_rows), max(rg_rows)] if rg_rows else None
    if RG_ROWS is not None:
        r["rg_rows_expected"] = RG_ROWS
        wrong = [(i, n) for i, n in enumerate(rg_rows[:-1]) if n != RG_ROWS]
        if wrong:
            errs.append(f"{len(wrong)} non-final row groups != {RG_ROWS} rows, first: {wrong[:5]}")
        if rg_rows and not 1 <= rg_rows[-1] <= RG_ROWS:
            errs.append(f"last row group has {rg_rows[-1]} rows (want 1..{RG_ROWS})")
    rg0 = md.row_group(0)
    r["rg0_codecs"] = sorted({rg0.column(j).compression for j in range(md.num_columns)})
    r["rg0_encodings"] = sorted({e for j in range(md.num_columns) for e in rg0.column(j).encodings})

    files, _ = chunk_files(sf, table)
    files = [f for f in files if os.path.getsize(f) > 0]
    compared = 0
    norm = raw_normalizer(table)
    if full:
        it = pf.iter_batches(batch_size=65536)
        buf, bi = [], 0
        for f in files:
            with open(f, encoding="utf-8", newline="\n") as fh:
                for ln, line in enumerate(fh):
                    if bi >= len(buf):
                        buf, bi = render_rows(pa.Table.from_batches([next(it)])), 0
                    if buf[bi] != norm(line.rstrip("\n")):
                        errs.append(f"row mismatch {os.path.basename(f)}:{ln}: raw={line.rstrip()!r} pq={buf[bi]!r}")
                        break
                    bi += 1
                    compared += 1
            if errs:
                break
    else:
        # global row offsets of each chunk
        counts = [file_lines[os.path.basename(f)] for f in files]
        starts = [sum(counts[:i]) for i in range(len(counts))]
        cache = {}
        rg_start = [sum(rg_rows[:i]) for i in range(len(rg_rows))]

        def pq_rows(lo, hi):
            out = []
            for i in range(len(rg_rows)):
                a, b = rg_start[i], rg_start[i] + rg_rows[i]
                if b <= lo or a >= hi:
                    continue
                if i not in cache:
                    if len(cache) > 2:
                        cache.clear()
                    cache[i] = pf.read_row_group(i)
                t = cache[i].slice(max(lo, a) - a, min(hi, b) - max(lo, a))
                out += render_rows(t)
            return out

        for f, st, cnt in zip(files, starts, counts):
            head, tail = edge_lines(f, EDGE)
            for off, lines in ((st, head), (st + cnt - len(tail), tail)):
                got_rows = pq_rows(off, off + len(lines))
                for k, (a_, b_) in enumerate(zip(lines, got_rows)):
                    if norm(a_) != b_:
                        errs.append(f"row mismatch {os.path.basename(f)} global_row={off+k}: raw={a_!r} pq={b_!r}")
                        break
                compared += len(lines)
    r["rows_compared"] = compared
    r["compare_mode"] = "full" if full else f"first/last {EDGE} lines of each of {len(files)} chunks"
    r["errors"] = errs
    return r


def cmd_parquet(sf, full, workers):
    raw = json.load(open(os.path.join(RAW.format(sf=sf), "_raw_check.json")))["tables"]
    outdir = OUT.format(sf=sf)
    pqs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(outdir, "*.parquet")))
    errs = []
    if pqs != sorted(f"{t}.parquet" for t in S.TABLES):
        errs.append(f"unexpected parquet entries: {pqs}")
    for p in pqs:
        if not os.path.isfile(os.path.join(outdir, p)):
            errs.append(f"{p} is not a plain file")
    leftovers = glob.glob(os.path.join(outdir, "_tmp_*"))
    if leftovers:
        errs.append(f"leftover tmp dirs {leftovers}")
    jobs = [(sf, t, full, raw[t]["raw_rows"], raw[t]["file_lines"]) for t in S.TABLES]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(check_table, jobs))
    for r in res:
        print(f"{r['table']:24s} raw={r['raw_rows']:>12,d} pq={r['parquet_rows']:>12,d} "
              f"rg={r['row_groups']:>4d} bytes={r['bytes']:>14,d} cmp={r['rows_compared']:,d} "
              f"{'OK' if not r['errors'] else 'ERR ' + '; '.join(r['errors'])[:2000]}")
        errs += [f"{r['table']}: {e}" for e in r["errors"]]
    json.dump({"sf": sf, "tables": res, "errors": errs}, open(os.path.join(outdir, "_verify.json"), "w"), indent=1)
    if errs:
        print("VERIFY FAILED")
        for e in errs:
            print("  ", e[:2000])
        sys.exit(3)
    print("VERIFY OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["raw", "parquet"])
    ap.add_argument("sf")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.mode == "raw":
        cmd_raw(a.sf)
    else:
        cmd_parquet(a.sf, a.full, a.workers)
