import re

pattern = "'(\w+).parquet'"
repl = r"dfs.`tmp/\1.parquet`"

for i in range(67, 68):
    fname = f"{i}.sql"
    if i < 10:
        fname = f"0{fname}"

    with open(fname) as fin: 
        with open(f"{i}_drill.sql", 'w') as fout:
            lines = fin.readlines() 
            for line in lines: 
                outline = re.sub(pattern, repl, line)
                fout.write(outline)



tpcds_names = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]

prefixes = {}
for tbl in tpcds_names: 
    if tbl == "inventory": 
        prefixes["inv_"] = tbl
    if tbl == "web_site": 
        prefixes["web_"] = tbl
    elif "_" in tbl and tbl != "date_dim" and tbl != "time_dim":
        parts = tbl.split("_")
        assert len(parts) == 2
        p = f"{parts[0][0]}{parts[1][0]}_"
        prefixes[p] = tbl
    else: 
        prefixes[tbl[0] + "_"] = tbl







f = open("../tpcds_schema/tpcds_column_names.csv")
columns = [x.strip() for x in f.readlines()]

for i in range(67, 68):
    with open(f"{i}_drill.sql") as fin: 
        with open(f"{i}_drill2.sql", 'w') as fout:
            qry = fin.read()
            out = qry 
            for col in columns: 
                # pattern = f" {col}"
                pattern = fr"(\(|,|\s|^){col}"
                sw = [prefixes[p] for p in prefixes if col.startswith(p)]
                assert len(sw) == 1, f"{sw}, {col}"
                repl = fr"\1{sw[0]}.{col}"
                out = re.sub(pattern, repl, out)
            fout.write(out)


