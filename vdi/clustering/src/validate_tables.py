import duckdb

no_cluster_tables = ["call_center", "catalog_page", "catalog_returns",
                     "catalog_sales", "customer", "customer_address",
                     "customer_demographics", "income_band", "inventory",
                     "promotion", "reason", "ship_mode", "store", "time_dim",
                     "warehouse", "web_page", "web_returns", "web_site"]

# Directory paths (update as per your setup)
INPUT_DIR = "/home/cc/tpcds_30gb"
VOD_OUTPUT_DIR = "/home/cc/tpcds_cluster_vod"
FREQ_OUTPUT_DIR = "/home/cc/tpcds_cluster_freq"
RAND_OUTPUT_DIR = "/home/cc/tpcds_cluster_random"
BASE_OUTPUT_DIR = "/home/cc/tpcds_cluster_base"

vod_inputs = [("web_sales", ['ws_sold_time_sk', 'ws_web_page_sk']), ("item", ['i_category', 'i_manufact_id'])]
freq_inputs = [("store_sales", ['ss_sold_date_sk', 'ss_item_sk']), ("date_dim", ['d_date_sk', 'd_year'])]
rand_inputs = [("household_demographics", ['hd_dep_count', 'hd_buy_potential']), ("store_returns", ['sr_store_credit', 'sr_cdemo_sk'])]

con = duckdb.connect()
tables = ["call_center", "catalog_page", "catalog_returns",
        "catalog_sales", "customer", "customer_address",
        "customer_demographics", "date_dim", "household_demographics",
        "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
        "store", "store_returns", "store_sales", "time_dim", "warehouse",
        "web_page", "web_returns", "web_sales", "web_site"]


for tbl in tables: 
    print(f"Count for base table {tbl}")
    path = f"{BASE_OUTPUT_DIR}/{tbl}/*.parquet"
    qry = f"SELECT COUNT(*) FROM '{path}'"
    ret = con.execute(qry)
    print(ret.fetchdf())


for arg in vod_inputs: 
    tbl = arg[0]
    cols = arg[1]
    path = f"{VOD_OUTPUT_DIR}/{tbl}/*.parquet"
    qry = f"SELECT COUNT(*) FROM '{path}'"
    ret = con.execute(qry)
    print(ret.fetchdf())


print("\n===== REWRITING FREQ TABLES =====")
for arg in freq_inputs: 
    tbl = arg[0]
    cols = arg[1]
    path = f"{FREQ_OUTPUT_DIR}/{tbl}/*.parquet"
    qry = f"SELECT COUNT(*) FROM '{path}'"
    ret = con.execute(qry)
    print(ret.fetchdf())

print("\n===== REWRITING RAND TABLES =====")
for arg in rand_inputs: 
    tbl = arg[0]
    cols = arg[1]
    path = f"{RAND_OUTPUT_DIR}/{tbl}/*.parquet"
    qry = f"SELECT COUNT(*) FROM '{path}'"
    ret = con.execute(qry)
    print(ret.fetchdf())
