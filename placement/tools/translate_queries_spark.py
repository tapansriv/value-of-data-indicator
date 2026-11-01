"""
Translate the DuckDB TPC-DS queries used by the placement experiment into Spark SQL.

Input:  test/example_queries/tpcds/NN.sql      (DuckDB dialect, bare table names)
Output: test/example_queries/tpcds_spark/NN.sql (Spark dialect, same table names)

Translation is sqlglot's duckdb -> spark transpile. The output is checked separately by
test/validate_spark_queries.py, which runs every query in both engines and compares rows.
"""
import os
import sys

import sqlglot

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "test", "example_queries", "tpcds")
DST = os.path.join(ROOT, "test", "example_queries", "tpcds_spark")


def translate(sql: str) -> str:
    out = sqlglot.transpile(sql, read="duckdb", write="spark", pretty=True)
    assert len(out) == 1, "expected one statement per file"
    return out[0] + "\n"


def main():
    os.makedirs(DST, exist_ok=True)
    failed = []
    for i in range(1, 100):
        name = f"{i:02d}.sql"
        try:
            with open(os.path.join(SRC, name)) as f:
                spark_sql = translate(f.read())
            with open(os.path.join(DST, name), "w") as f:
                f.write(spark_sql)
        except Exception as e:  # report and keep going
            failed.append((name, e))
    for name, e in failed:
        print(f"FAILED {name}: {e}")
    print(f"translated {99 - len(failed)}/99 -> {DST}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
