import duckdb

dbs = ["tpcds_freq.db", "tpcds_vod.db"]

tables = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]

for db in dbs:
    print(f"Starting {db}")
    con = duckdb.connect(db)
    for tbl in tables: 
        qry = f"CREATE TABLE {tbl} AS SELECT * FROM '/home/cc/tpcds_30gb/{tbl}.parquet'"
        print(f"    Loading {tbl}")
        con.execute(qry)
        print(f"    Loaded {tbl}")






