import re
import os
import json

f = open("./sqlline.log")
lines = f.readlines()

# files = [f"sqlline.log.{i}" for i in range(1, 11)]
# for file in files:
#     print(file)
#     f = open(file)
#     lines.extend(f.readlines())

num_lines = len(lines)
curr_line = 0

new_query_marker = "Query text for query with id"
row_group_match = r"Read (\d+) records out of row group\((\d+)\) in file '\/tmp\/(\w+).parquet'"

outputs = []
while curr_line < num_lines: 
    line = lines[curr_line]
    if new_query_marker not in line:
        curr_line += 1
        continue

    parts = line.split(new_query_marker) # remove the line start
    query_start = parts[1].split(":")[1] # parts[1] is the part with query start
    query = None
    num_skiped = 0
    if not lines[curr_line+1].startswith("2025-05"):
        # query is multiline
        query_parts = [query_start]
        i = 1
        while not lines[curr_line+i].startswith("2025-05"):
            query_parts.append(lines[curr_line+i])
            i += 1
        query = "".join(query_parts)
        num_skipped = i
    else: 
        query = query_start
        num_skipped = 1

    curr_line += num_skipped 

    row_groups = []
    while (curr_line < num_lines) and (new_query_marker not in lines[curr_line]):
        l = lines[curr_line]
        z = re.search(row_group_match, l)
        # if "Read 6005 records out of row group(0)" in l:
        #     print(l)
        #     print(z)
        if z is not None:
            num_records = z.group(1)
            rg = z.group(2)
            file = z.group(3)
            row_groups.append({
                "row_group": rg,
                "file": file,
                "num_records": num_records, 
            })
        curr_line += 1
    
    outputs.append({
        "query": query, 
        "data_elements": row_groups
    })

assert curr_line == num_lines
# print(outputs)
with open("access.json", 'w') as fp:
    json.dump(outputs, fp, indent=4)
