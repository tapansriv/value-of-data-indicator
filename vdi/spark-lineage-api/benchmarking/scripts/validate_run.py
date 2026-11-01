"""R2D16: validate one EC2 run's outputs, not just its timings.

    python3 validate_run.py <run-dir> <query-dir>

<run-dir>: benchmarking/data/ec2/<run-id>/ with rep*/<variant>/{results CSV, driver.log} and
usage_logs/rep*/<variant>/ (parquet; `aws s3 sync s3://<results>/runs/<run-id>/usage_logs`).
<query-dir>: the queries the run used (benchmarking/tpch22).

Checks, per (rep, variant):
  1. completion: every query has runtime >= 0 and listener_timeout = false.
  2. answers: the result table each query prints (show(): first 20 rows) is identical in every
     (rep, variant) — the listeners must not change results.
  3. cols usage log: one logged query per query; its tables = the tables in the SQL; every
     logged column belongs to its table and appears in the SQL text.
  4. rowgroup usage log: one logged query per query; its tables = the tables in the SQL; the
     row groups per table equal that table's total row groups (no filter in TPC-H can skip a
     row group here: the data is not clustered on any filter column), with no duplicates.
Exit status 0 if everything passes.
"""
import csv
import glob
import os
import re
import sys
from collections import defaultdict

import duckdb

# Row groups per table, read from the parquet footers in s3://vod-tpch-1tb (REVISION_SCALEUP.md §6).
TOTAL_RG = {"lineitem": 48372, "orders": 12188, "partsupp": 6499, "part": 1624,
            "customer": 1217, "supplier": 81, "nation": 1, "region": 1}
PREFIX = {"lineitem": "l_", "orders": "o_", "partsupp": "ps_", "part": "p_",
          "customer": "c_", "supplier": "s_", "nation": "n_", "region": "r_"}

failures = []


def fail(msg):
    failures.append(msg)
    print("   FAIL", msg)


def sql_tables(sql):
    # ignore string literals: Q16's "like '%Customer%Complaints%'" is not a table reference
    code = re.sub(r"'[^']*'", "''", sql)
    return {t for t in TOTAL_RG if re.search(rf"\b{t}\b", code, re.IGNORECASE)}


def result_tables(driver_log):
    """The show() output blocks, in order: runs of lines starting with '+' or '|'."""
    blocks, cur = [], []
    for line in open(driver_log, errors="replace"):
        if line.startswith(("+", "|")):
            cur.append(line.rstrip("\n"))
        elif cur:
            blocks.append("\n".join(cur)); cur = []
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def per_query_groups(con, path):
    """Usage-log rows grouped by query execution, ordered by first timestamp."""
    con.execute(f"create or replace view u as select * from read_parquet('{path}/*.parquet')")
    ids = [r[0] for r in con.execute(
        "select dataTaskId from u group by dataTaskId order by min(timestamp)").fetchall()]
    return ids


def main(run_dir, qdir):
    queries = sorted(f for f in os.listdir(qdir) if f.endswith(".sql"))
    sql = {q: open(os.path.join(qdir, q)).read() for q in queries}
    con = duckdb.connect()
    answers = defaultdict(dict)   # query -> (rep, variant) -> printed table

    for res in sorted(glob.glob(os.path.join(run_dir, "rep*", "*", "spark_internal_listener_*_results.csv"))):
        rep = res.split(os.sep)[-3]; variant = res.split(os.sep)[-2]
        print(f"== {rep}/{variant}")
        rows = list(csv.DictReader(open(res)))
        names = [r["query"] for r in rows]
        if names != queries:
            fail(f"{rep}/{variant}: queries {names} != {queries}")
        for r in rows:
            if int(r["runtime"]) < 0 or r["listener_timeout"] == "true":
                fail(f"{rep}/{variant}/{r['query']}: runtime {r['runtime']}, timeout {r['listener_timeout']}")

        log = os.path.join(os.path.dirname(res), "driver.log")
        if os.path.exists(log):
            blocks = result_tables(log)
            if len(blocks) != len(queries):
                fail(f"{rep}/{variant}: {len(blocks)} printed result tables for {len(queries)} queries")
            for q, b in zip(queries, blocks):
                answers[q][(rep, variant)] = b
        else:
            print(f"   (no driver.log; answers not checked)")

        ul = os.path.join(run_dir, "usage_logs", rep, variant)
        if variant not in ("cols", "rowgroup"):
            continue
        if not glob.glob(os.path.join(ul, "*.parquet")):
            fail(f"{rep}/{variant}: no usage-log parquet at {ul}")
            continue
        ids = per_query_groups(con, ul)
        if len(ids) != len(queries):
            fail(f"{rep}/{variant}: {len(ids)} logged queries for {len(queries)} queries")
        n_ok = 0
        for q, tid in zip(queries, ids):
            want = sql_tables(sql[q])
            if variant == "cols":
                got = con.execute("select tableName, columnName from u where dataTaskId = ?", [tid]).fetchall()
                tables = {t for t, _ in got}
                bad_cols = [(t, c) for t, c in got
                            if t not in PREFIX or not c.lower().startswith(PREFIX[t])  # physical names may be upper-case
                            or not re.search(rf"\b{re.escape(c)}\b", sql[q], re.IGNORECASE)]
                if tables != want:
                    fail(f"{rep}/cols/{q}: tables {sorted(tables)} != SQL {sorted(want)}")
                elif bad_cols:
                    fail(f"{rep}/cols/{q}: columns not in table/SQL: {bad_cols[:4]}")
                else:
                    n_ok += 1
            else:
                got = con.execute("""select tableName, count(*) n, count(distinct (rowGroupOffset, rowGroupSize)) d
                                     from u where dataTaskId = ? group by tableName""", [tid]).fetchall()
                tables = {t for t, _, _ in got}
                problems = []
                if tables != want:
                    problems.append(f"tables {sorted(tables)} != SQL {sorted(want)}")
                for t, n, d in got:
                    if n != d:
                        problems.append(f"{t}: {n - d} duplicate row groups")
                    if t in TOTAL_RG and d != TOTAL_RG[t]:
                        problems.append(f"{t}: {d} row groups, table has {TOTAL_RG[t]}")
                if problems:
                    fail(f"{rep}/rowgroup/{q}: " + "; ".join(problems))
                else:
                    n_ok += 1
        print(f"   {variant} usage log: {n_ok}/{len(queries)} queries correct")

    print("== answers across (rep, variant)")
    n_same = 0
    for q in queries:
        distinct = set(answers[q].values())
        if len(distinct) > 1:
            fail(f"{q}: {len(distinct)} different printed results across {sorted(answers[q])}")
        elif answers[q]:
            n_same += 1
    print(f"   {n_same}/{len(queries)} queries print identical results in all {len(next(iter(answers.values()), {}))} passes")

    print("PASS" if not failures else f"FAILED: {len(failures)} problems")
    return 0 if not failures else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
