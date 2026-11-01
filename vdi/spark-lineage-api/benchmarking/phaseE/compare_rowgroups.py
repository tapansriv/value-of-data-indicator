"""Phase E step 1: is row-group capture identical in local mode and on the cluster?

Runs ON THE DRIVER with the instrumented Spark, after the same query set was run with the
rowgroup variant twice (run_matrix.sh --local, then on the cluster):

    /opt/spark/bin/spark-submit --master 'local[4]' compare_rowgroups.py \
        <bucket> <run-id-local> <run-id-cluster> [rep] [variant]

Each run's usage log holds one row per (row group read, query): tableName, rowGroupOffset,
rowGroupSize, dataTaskId (one per query execution), timestamp. Queries run one at a time in
sorted order, so ordering a run's dataTaskIds by first timestamp recovers the query order;
names come from that run's results CSV. For every query the two runs must read exactly the
same set of (table, offset, size), with no row group recorded twice (a duplicate would mean
double counting, e.g. a retried or speculative task).

Exit status 0 = identical, 1 = any difference. Read-only.
"""
import csv
import os
import sys

from pyspark.sql import SparkSession, functions as F


def query_names(run_id, rep, variant):
    path = os.path.expanduser(
        f"~/vdi/runs/{run_id}/rep{rep}/{variant}/spark_internal_listener_{variant}_results.csv")
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return [r["query"] for r in rows if int(r["runtime"]) >= 0], len(rows)


def per_query(spark, bucket, run_id, rep, variant):
    df = spark.read.parquet(f"s3a://{bucket}/runs/{run_id}/usage_logs/rep{rep}/{variant}")
    order = (df.groupBy("dataTaskId").agg(F.min("timestamp").alias("t"))
             .orderBy("t").collect())
    out = []
    for row in order:
        rgs = (df.where(F.col("dataTaskId") == row["dataTaskId"])
               .groupBy("tableName", "rowGroupOffset", "rowGroupSize").count().collect())
        multiset = {(r["tableName"], r["rowGroupOffset"], r["rowGroupSize"]): r["count"] for r in rgs}
        out.append(multiset)
    return out


def main():
    bucket, run_a, run_b = sys.argv[1:4]
    rep = sys.argv[4] if len(sys.argv) > 4 else "1"
    variant = sys.argv[5] if len(sys.argv) > 5 else "rowgroup"
    spark = SparkSession.builder.appName("compare_rowgroups").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    ok = True
    names_a, n_a = query_names(run_a, rep, variant)
    names_b, n_b = query_names(run_b, rep, variant)
    if names_a != names_b or len(names_a) != n_a or len(names_b) != n_b:
        print(f"MISMATCH in completed queries: {run_a}={names_a} (of {n_a}), {run_b}={names_b} (of {n_b})")
        ok = False
    qa = per_query(spark, bucket, run_a, rep, variant)
    qb = per_query(spark, bucket, run_b, rep, variant)
    if len(qa) != len(names_a) or len(qb) != len(names_b):
        print(f"MISMATCH in logged queries: {run_a} has {len(qa)} for {len(names_a)} queries, "
              f"{run_b} has {len(qb)} for {len(names_b)}")
        ok = False

    print(f"{'query':<22} {'rg ' + run_a:>18} {'rg ' + run_b:>18} {'only A':>8} {'only B':>8} {'dup A':>6} {'dup B':>6}")
    for i, name in enumerate(names_a):
        a = qa[i] if i < len(qa) else {}
        b = qb[i] if i < len(qb) else {}
        only_a, only_b = set(a) - set(b), set(b) - set(a)
        dup_a = sum(1 for c in a.values() if c > 1)
        dup_b = sum(1 for c in b.values() if c > 1)
        tables = sorted({k[0] for k in a} | {k[0] for k in b})
        print(f"{name:<22} {len(a):>18} {len(b):>18} {len(only_a):>8} {len(only_b):>8} {dup_a:>6} {dup_b:>6}  {','.join(tables)}")
        if only_a or only_b or dup_a or dup_b or not a:
            ok = False
            for k in sorted(only_a)[:5]:
                print(f"    only in {run_a}: {k}")
            for k in sorted(only_b)[:5]:
                print(f"    only in {run_b}: {k}")
            if not a:
                print("    no row groups recorded at all")

    print("IDENTICAL" if ok else "DIFFERENT: row-group capture is not consistent; stop before any 1TB run")
    spark.stop()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
