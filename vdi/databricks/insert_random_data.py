import json
import numpy as np
from datetime import datetime, timezone

rng = np.random.default_rng(42)
column_data = json.load(open("tpcds_columns_in_queries.json"))

timestamp = "2026-03-05T12:00:00"

rows = []
for qry in column_data: 
    qry_data = column_data[qry]
    num_rel_columns = sum([len(qry_data[tbl]) for tbl in qry_data])
    qry_val = rng.uniform(low=0, high=1000, size=1).tolist()[0]
    col_val = qry_val / num_rel_columns

    for tbl in qry_data:
        for col in qry_data[tbl]:
            row = (tbl, col, None, -1, timestamp, col_val)
            newstr = f"{tbl},{col},NULL,-1,{timestamp},{col_val}"
            print(newstr)
            # rows.append(newstr)


