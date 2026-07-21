import pandas as pd

tb_col = "listener_time_sec"
rg_col = "listener_rg_time"
vanilla_col = "vanilla_time_sec"

df = pd.read_csv("../data/custom_spark/final_results_custom_spark_8_26.csv")
df = df[df["vanilla_time_sec"] != "fail"]

exclude_cols = ['run_number', 'query', 'dataset']
numeric_cols = [col for col in df.columns if col not in exclude_cols]
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
grouped = df.groupby(['query', 'dataset'])[numeric_cols].mean().reset_index()

grouped["rg_tb_overhead"] = 100 * (grouped[rg_col] - grouped[tb_col] ) / grouped[tb_col]
print(grouped["rg_tb_overhead"].describe())
print("")
print(grouped.loc[grouped["rg_tb_overhead"].idxmax()])
print("")


grouped["rg_overhead"] = 100 * (grouped[rg_col] - grouped[vanilla_col] ) / grouped[vanilla_col]
grouped["tb_overhead"] = 100 * (grouped[tb_col] - grouped[vanilla_col] ) / grouped[vanilla_col]
grouped = grouped[grouped["rg_overhead"] > 0]
grouped = grouped[grouped["tb_overhead"] > 0]

maxqs = ["4.sql", "5.sql", "6.sql", "3.sql", "1.sql", "15.sql", "17.sql", "12.sql", "10.sql"]

df = grouped[grouped["query"].isin(maxqs)]
print(df[["query", "listener_time_sec", "listener_rg_time", "vanilla_time_sec"]])
