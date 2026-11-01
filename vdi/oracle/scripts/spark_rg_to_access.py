'''
Convert RowGroupCapture output (spark-lineage-api/listener_versions_new/RowGroupCapture.scala)
into the per-query access.json layout that assign_val_to_de.py reads, i.e. the same shape the
Drill logs had:

    <out-dir>/tpcds_<N>/access.json   [{"query": ..., "data_elements":
                                          [{"file": <table>, "row_group": "<idx>",
                                            "num_records": "<rows>"}, ...]}]
    <out-dir>/tpcds_completed.json     sorted list of query numbers that captured cleanly

Spark logs each row group as (ordinal, row index offset, row count). The row-group index is
recovered from the row index offset against the Parquet footer, which is independent of
whether the writer stored ordinals; the ordinal, when present, is checked against it.

A query counts as completed only if every statement in it succeeded and its rg/<N>.done
marker exists. Everything else is listed in capture_summary.json with the reason.
'''

import csv
import json
import os
import sys
from argparse import ArgumentParser
from urllib.parse import urlparse

import pyarrow.parquet as pq

csv.field_size_limit(sys.maxsize)


def local_path(uri):
    parsed = urlparse(uri)
    return parsed.path if parsed.scheme in ("file", "") else uri


def footer_index(path):
    '''row index offset -> (row group index, num rows) for one Parquet file.'''
    md = pq.ParquetFile(path).metadata
    index = {}
    offset = 0
    for i in range(md.num_row_groups):
        rows = md.row_group(i).num_rows
        index[offset] = (i, rows)
        offset += rows
    return index


def load_statuses(capture_dir):
    '''query -> its statements' rows. queries.csv is append-only, so when a query is rerun
    (the capture driver retries anything without a .done marker) the latest row for each
    statement supersedes earlier attempts.'''
    latest = {}
    with open(os.path.join(capture_dir, "queries.csv")) as fp:
        for row in csv.DictReader(fp):
            latest[(int(row["query"]), int(row["stmt"]))] = row
    statuses = {}
    for (q, _), row in sorted(latest.items()):
        statuses.setdefault(q, []).append(row)
    return statuses


def convert_query(n, capture_dir, footers, query_dir):
    rg_path = os.path.join(capture_dir, "rg", f"{n}.csv")
    elements = set()
    with open(rg_path) as fp:
        for row in csv.DictReader(fp):
            path = local_path(row["file"])
            if path not in footers:
                footers[path] = footer_index(path)
            offset = int(row["row_index_offset"])
            if offset not in footers[path]:
                raise ValueError(f"query {n}: offset {offset} is not a row-group start in {path}")
            idx, rows = footers[path][offset]
            if int(row["row_count"]) != rows:
                raise ValueError(f"query {n}: row count {row['row_count']} != footer {rows} "
                                 f"for row group {idx} of {path}")
            ordinal = int(row["ordinal"])
            if ordinal >= 0 and ordinal != idx:
                raise ValueError(f"query {n}: ordinal {ordinal} != index {idx} in {path}")
            table = os.path.basename(path)[:-len(".parquet")]
            elements.add((table, idx, rows))

    text = ""
    if query_dir:
        with open(os.path.join(query_dir, f"query{n}.sql")) as fp:
            text = fp.read()
    # assign_val_to_de.py skips leading entries whose "query" contains "SET" (Drill logged
    # session SET statements), so the label goes in "query" and the SQL in "query_text".
    return [{
        "query": f"tpcds query {n} (spark row-group capture)",
        "query_text": text,
        "data_elements": [{"file": t, "row_group": str(i), "num_records": str(r)}
                          for t, i, r in sorted(elements)],
    }]


def check_tables(n, access, columns_in_queries):
    '''Tables the query references (per the column parser) that show no row groups read.'''
    expected = {("customer" if t == "tpcds.customer" else t)
                for t, cols in columns_in_queries[str(n)].items() if cols}
    seen = {e["file"] for e in access[0]["data_elements"]}
    return sorted(expected - seen)


if __name__ == "__main__":
    parser = ArgumentParser(description="Spark row-group capture -> access.json")
    parser.add_argument("--capture-dir", required=True,
                        help="RowGroupCapture output dir (has queries.csv and rg/)")
    parser.add_argument("--out-dir", required=True,
                        help="Where to write tpcds_<N>/access.json and tpcds_completed.json")
    parser.add_argument("--query-dir", default=None,
                        help="Spark query dir (queryN.sql); embeds the SQL in access.json")
    parser.add_argument("--columns-in-queries", default=None,
                        help="tpcds_columns_in_queries.json for the same query set; if given, "
                             "flag queries where a referenced table has no row groups")
    args = parser.parse_args()

    statuses = load_statuses(args.capture_dir)
    columns_in_queries = None
    if args.columns_in_queries:
        with open(args.columns_in_queries) as fp:
            columns_in_queries = json.load(fp)

    os.makedirs(args.out_dir, exist_ok=True)
    footers = {}
    completed, not_completed, table_gaps, per_query = [], {}, {}, {}

    for n in sorted(statuses):
        rows = statuses[n]
        bad = [r for r in rows if r["status"] != "ok"]
        done = os.path.exists(os.path.join(args.capture_dir, "rg", f"{n}.done"))
        if bad or not done:
            not_completed[n] = ([f"stmt {r['stmt']}: {r['status']}: {r['error'][:300]}" for r in bad]
                                or ["no .done marker"])
            continue

        access = convert_query(n, args.capture_dir, footers, args.query_dir)
        qdir = os.path.join(args.out_dir, f"tpcds_{n}")
        os.makedirs(qdir, exist_ok=True)
        with open(os.path.join(qdir, "access.json"), "w") as fp:
            json.dump(access, fp, indent=4)

        elements = access[0]["data_elements"]
        per_query[n] = {"row_groups": len(elements),
                        "tables": sorted({e["file"] for e in elements})}
        if columns_in_queries is not None:
            missing = check_tables(n, access, columns_in_queries)
            if missing:
                table_gaps[n] = missing
        completed.append(n)

    with open(os.path.join(args.out_dir, "tpcds_completed.json"), "w") as fp:
        json.dump(completed, fp)
    summary = {
        "capture_dir": os.path.abspath(args.capture_dir),
        "completed": len(completed),
        "not_completed": not_completed,
        "referenced_tables_with_no_row_groups": table_gaps,
        "per_query": per_query,
    }
    with open(os.path.join(args.out_dir, "capture_summary.json"), "w") as fp:
        json.dump(summary, fp, indent=4)

    print(f"completed {len(completed)}, not completed {len(not_completed)}: "
          f"{sorted(not_completed)}")
    if table_gaps:
        print(f"{len(table_gaps)} queries reference a table with no row groups read "
              f"(see capture_summary.json): {sorted(table_gaps)}")
