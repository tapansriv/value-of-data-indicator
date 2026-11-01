# Value Gen 1
# high = ["90.sql"]
# medium = ["41.sql", "84.sql"]

# Value Gen 2
high = ["16.sql"]
medium = ["47.sql", "89.sql"]

import pandas as pd

query_ids = [f"{i:02d}.sql" for i in range(1, 100)]
iter_0 = [1 for _ in range(1, 100)]
iter_1 = [1 for _ in range(1, 100)] 
iter_2 = [1 for _ in range(1, 100)] 
iter_3 = [1 for _ in range(1, 100)] 
iter_4 = [1 for _ in range(1, 100)] 
# iter_5 = [1 for _ in range(1, 100)] 
# iter_6 = [1 for _ in range(1, 100)] 


for h in high: 
    index = query_ids.index(h)
    iter_1[index] = 50
    
    # iter_5[index] = 60
    # iter_6[index] = 80

    iter_2[index] = 100
    iter_3[index] = 500
    iter_4[index] = 1000


for m in medium:
    index = query_ids.index(m)
    iter_1[index] = 5

    # iter_5[index] = 6
    # iter_6[index] = 8

    iter_2[index] = 10
    iter_3[index] = 50
    iter_4[index] = 100


data = {
    "query_id": query_ids,
    "0": iter_0,
    "1": iter_1,
    "2": iter_2,
    "3": iter_3,
    "4": iter_4,
    # "5": iter_5,
    # "6": iter_6,
}

df = pd.DataFrame(data)
df.to_csv("tpcds_query_values_custom.csv")
