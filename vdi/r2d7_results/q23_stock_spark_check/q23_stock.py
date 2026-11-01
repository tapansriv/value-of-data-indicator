import sys, os, pyspark
from pyspark.sql import SparkSession
sf = sys.argv[1]
spark = (SparkSession.builder.master("local[*]").config("spark.driver.memory", "40g")
         .config("spark.local.dir", f"/mnt/tpcds/spark-tmp/sf{sf}")
         .config("spark.sql.execution.reuseExchange", "false")
         .config("spark.sql.execution.reuseSubquery", "false").getOrCreate())
d = f"/mnt/tpcds/parquet/sf{sf}"
for f in sorted(os.listdir(d)):
    if f.endswith(".parquet"):
        spark.read.parquet(f"{d}/{f}").createOrReplaceTempView(f[:-8])
# Was /home/cc/value_of_data/spark-scale/...; that worktree was removed (2026-10-08), same file on main.
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
text = open(os.path.join(REPO, "spark-lineage-api/benchmarking/tpcds_queries_spark/query23.sql")).read()
stmts = [s for s in text.split(";") if any(l.strip() and not l.strip().startswith("--") for l in s.splitlines())]
print(f"pyspark {pyspark.__version__} AQE={spark.conf.get('spark.sql.adaptive.enabled')} SF{sf}")
for i, s in enumerate(stmts):
    try:
        print(f"SF{sf} stmt {i}: ok rows={len(spark.sql(s).collect())}")
    except Exception as e:
        msg = str(e); npe = "NullPointerException" in msg and "toBigDecimal" in msg
        print(f"SF{sf} stmt {i}: FAILED decimal-NPE={npe}: {msg.splitlines()[0][:200]}")
spark.stop()
