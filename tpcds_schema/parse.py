tpcds_names = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]

prefixes = {}
for tbl in tpcds_names: 
    if tbl == "web_site": 
        prefixes[tbl] = "web"
    elif "_" in tbl and tbl != "date_dim" and tbl != "time_dim":
        parts = tbl.split("_")
        assert len(parts) == 2
        p = f"{parts[0][0]}{parts[1][0]}"
        prefixes[tbl] = p
    else: 
        prefixes[tbl] = tbl[0]

print(prefixes)
fout = open("tpcds_column_names.csv", 'w')

columns_in_tables = {tbl: [] for tbl in tpcds_names}

for tbl in tpcds_names:
    f = open(f"{tbl}.sql")
    lines = [x.strip() for x in f.readlines()[1:-1]]

    for line in lines:
        vals = line.split(" ") 
        col = vals[0]
        print(col)
        assert col.startswith(prefixes[tbl])
        fout.write(f"{col}\n")
        columns_in_tables[tbl].append(col)


with open("tpcds_columns_in_tables.json", 'w') as fp:
    import json
    json.dump(columns_in_tables, fp, indent=4)
