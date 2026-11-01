import json

duck_baseline = json.load(open("duckdb_baseline_times.json"))
opt_baseline = json.load(open("../ec2_30gb_5cache/baseline_times.json"))
cold_baseline = json.load(open("cold_runtimes.json"))

duck_opt = []
duck_cold = []
xs = []
cold_opt = []
for query in duck_baseline:
    duck_time = duck_baseline[query]
    opt_time = opt_baseline[query]
    cold_time = cold_baseline[query]["query_runtime"]

    if opt_time is None or cold_time is None:
        print(f"Missing data for query {query}, skipping comparison.")
        continue

    duck_vs_opt = 100 * (duck_time - opt_time)/ opt_time
    duck_vs_cold = 100 * (duck_time - cold_time) / cold_time
    cold_vs_opt = 100 * (cold_time - opt_time) / opt_time

    duck_opt.append(duck_vs_opt)
    duck_cold.append(duck_vs_cold)
    cold_opt.append(cold_vs_opt)

    cold_delete = cold_baseline[query]["delete_runtime"]

    x = cold_delete / cold_time
    xs.append(x)
    # print(f"Query: {query} Cold Delete vs Query Time: {x:.5f}x")



    # print(f"Query: {query} Cold {duck_vs_cold:.2f}% Opt {duck_vs_opt:.2f}% ColdVsOpt {cold_vs_opt:.2f}%")
    # print(f"Query: {query}")
    # print(f"  DuckDB Time: {duck_time:.2f}s")
    # print(f"  Optimized Time: {opt_time:.2f}s")
    # print(f"  Cold Baseline Time: {cold_time:.2f}s")
    # print(f"  DuckDB vs Optimized: {duck_vs_opt:.2f}x")
    # print(f"  DuckDB vs Cold Baseline: {duck_vs_cold:.2f}x")
    # print("")

avg_duck_opt = sum(duck_opt) / len(duck_opt)
avg_duck_cold = sum(duck_cold) / len(duck_cold)
avg_cold_opt = sum(cold_opt) / len(cold_opt)
print(f"Average DuckDB vs Optimized: {avg_duck_opt:.2f}%")
print(f"Average DuckDB vs Cold Baseline: {avg_duck_cold:.2f}%")
print(f"Average Cold Baseline vs Optimized: {avg_cold_opt:.2f}%")
import statistics
median = statistics.median(duck_cold)
print(f"Median DuckDB vs Cold Baseline: {median:.2f}%")
stdev = statistics.stdev(duck_cold)
print(f"Standard Deviation DuckDB vs Cold Baseline: {stdev:.2f}%")

# avg_x = sum(xs) / len(xs)
# print(f"Average Cold Delete vs Query Time: {avg_x:.5f}x")
# median_x = statistics.median(xs)
# print(f"Median Cold Delete vs Query Time: {median_x:.5f}x")
