'''
Parse what columns are in each query in the TPCH schema
'''
import json
import re
import os

# what the column prefixes are for each table
prefix = {
    "customer": "c_",
    "lineitem": "l_",
    "nation": "n_",
    "orders": "o_",
    "part": "p_",
    "partsupp": "ps_",
    "region": "r_",
    "supplier": "s_",
}

# hard coded the query numbers 
queries = [i for i in range(1, 39)]
outputs = {q: {t: [] for t in prefix} for q in queries}

# use regex to find all words matching table prefix and use that to map to
# tables and columns
for query in queries:
    fl = f"../../tpch_queries/{query}.sql"
    lines = [line for line in open(fl).readlines()]
    for line in lines:
        for tbl in prefix:
            p = prefix[tbl]
            regex = re.compile(f"{p}\\w+")
            lst = [l.lower() for l in regex.findall(line)]
            outputs[query][tbl].extend(lst)


for query in queries:
    for tbl in prefix:
        lst = outputs[query][tbl]
        outputs[query][tbl] = sorted(list(set(lst)))


# post analysis validation to ensure that every match is a real column and that
# matching works
path_prefix = "../data/tpch_csv/"
for tbl in prefix:
    tpath = f"{path_prefix}{tbl}.csv"
    f = open(tpath)
    schema = f.readline().lower()

    for query in queries: 
        to_remove = []
        for col in outputs[query][tbl]:
            if col not in schema:
                to_remove.append(col)
        for col in to_remove:
            outputs[query][tbl].remove(col)

# write this out to json and csv
with open("../data/tpch_columns_in_queries.json", 'w') as fp:
    json.dump(outputs, fp, indent=4)

ret = []
for query in queries:
    for tbl in prefix:
        for col in outputs[query][tbl]:
            line = f"{tbl}, {col}, query_{query}"
            ret.append(line)

with open('../data/tpch_columns_in_queries.csv', 'w') as fp:
    for l in ret:
        fp.write(f"{l}\n")
