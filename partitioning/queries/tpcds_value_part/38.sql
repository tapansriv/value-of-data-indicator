SELECT
  COUNT(*)
FROM (
    SELECT DISTINCT
      c_last_name,
      c_first_name,
      d_date
    FROM READ_PARQUET('store_sales.parquet') AS store_sales, READ_PARQUET('date_dim.parquet') AS date_dim, READ_PARQUET('customer.parquet') AS customer
    WHERE
      store_sales.ss_sold_date_sk = date_dim.d_date_sk
      AND store_sales.ss_customer_sk = customer.c_customer_sk
      AND d_month_seq BETWEEN 1200 AND 1200 + 11
    INTERSECT
    SELECT DISTINCT
      c_last_name,
      c_first_name,
      d_date
    FROM READ_PARQUET('catalog_sales.parquet') AS catalog_sales, READ_PARQUET('date_dim.parquet') AS date_dim, READ_PARQUET('customer.parquet') AS customer
    WHERE
      catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
      AND catalog_sales.cs_bill_customer_sk = customer.c_customer_sk
      AND d_month_seq BETWEEN 1200 AND 1200 + 11
    INTERSECT
    SELECT DISTINCT
      c_last_name,
      c_first_name,
      d_date
    FROM READ_PARQUET('/home/cc/tpcds_partitioned_value/web_sales/**/*.parquet', hive_partitioning = 1) AS web_sales, READ_PARQUET('date_dim.parquet') AS date_dim, READ_PARQUET('customer.parquet') AS customer
    WHERE
      web_sales.ws_sold_date_sk = date_dim.d_date_sk
      AND web_sales.ws_bill_customer_sk = customer.c_customer_sk
      AND d_month_seq BETWEEN 1200 AND 1200 + 11
) AS hot_cust
LIMIT 100