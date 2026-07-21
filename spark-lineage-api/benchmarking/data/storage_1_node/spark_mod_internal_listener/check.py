tpcds = [f"query{i}.sql" for i in range(1, 132)]
tpch = [f"{i}.sql" for i in range(1, 39)]

f = open("spark_internal_listener_cols_results.csv")
lines = "".join(f.readlines())

for x in tpcds:
    if x not in lines:
        print(x)

for x in tpch:
    if x not in lines:
        print(x)

