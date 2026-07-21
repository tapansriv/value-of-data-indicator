import pandas as pd

query_keys = [f"query_{i:02d}" for i in range(1,100)]
query_values = [1 for _ in range(1,100)]

high_val = 1000
mid_val = 100

high = [90]
mid = [41, 84]

for h in high:
    query_values[h-1] = high_val

for m in mid:
    query_values[m-1] = mid_val

df = pd.DataFrame({
    'query_id': query_keys,
    '0': query_values,
    })

df.to_csv("tpcds_query_values_custom_v2.csv")

