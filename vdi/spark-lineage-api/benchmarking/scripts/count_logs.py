import duckdb
import pandas as pd
import os

tpcds_dirs = os.listdir("../tpcds_rgs")
tpch_dirs = os.listdir("../tpch_rgs")

counts = []
for dir_ in tpcds_dirs:
    tbls = f"../tpcds_rgs/{dir_}/usage_logs/*.parquet"
    qry = f"SELECT COUNT(*) from '{tbls}'"
    ret = duckdb.sql(qry)
    count = ret.fetchall()[0][0]
    counts.append(count)
    if count == 1455:
        print(dir_)
    if dir_ == "query4.sql":
        print(f"{dir_} counts: {count}")

for dir_ in tpch_dirs:
    tbls = f"../tpch_rgs/{dir_}/usage_logs/*.parquet"
    qry = f"SELECT COUNT(*) from '{tbls}'"
    ret = duckdb.sql(qry)
    count = ret.fetchall()[0][0]
    counts.append(count)
    if count == 1455:
        print(dir_)


s = pd.Series(counts)
print(s.describe())
