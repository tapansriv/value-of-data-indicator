"""Translate the DuckDB TPC-DS queries used by the sorting experiment into Spark SQL.

The Spark rerun must execute the *same query text* as the DuckDB run
(clustering/queries/tpcds/), so that the SQL-parsed column sets, and therefore the
VOD/Frequent/Random layout decisions, are identical across engines. Only the dialect
changes. Do not substitute spark-lineage-api/benchmarking/tpcds_queries_spark/: it is a
different qgen stream (19/99 queries reference different columns).

Output: queries_spark/NN.sql, one statement each. Validate on the node with
`run_phase.sh explain` before any measured run.
"""
import os
from argparse import ArgumentParser
from pathlib import Path

import sqlglot

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "queries" / "tpcds"
OUT = HERE / "queries_spark"


def main():
    parser = ArgumentParser()
    parser.add_argument("--src", default=str(SRC))
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--expect", type=int, default=99,
                        help="number of .sql files required; 0 to accept any count. "
                             "Default 99 keeps the TPC-DS invariant; the Redbench IMDb "
                             "workload (R3D4) has 415.")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    files = sorted(Path(args.src).glob("*.sql"))
    if args.expect:
        assert len(files) == args.expect, \
            f"expected {args.expect} queries, found {len(files)}"
    assert files, f"no .sql files in {args.src}"
    for f in files:
        stmts = sqlglot.transpile(f.read_text(), read="duckdb", write="spark", pretty=True)
        assert len(stmts) == 1, f"{f.name}: {len(stmts)} statements"
        (Path(args.out) / f.name).write_text(stmts[0] + "\n")
    print(f"translated {len(files)} queries -> {args.out} (sqlglot {sqlglot.__version__})")


if __name__ == "__main__":
    main()
