SELECT count(*)
FROM
  (SELECT DISTINCT customer.c_last_name,
                   customer.c_first_name,
                   date_dim.d_date
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer.parquet` AS customer
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_customer_sk = customer.c_customer_sk
     AND date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11 INTERSECT
     SELECT DISTINCT customer.c_last_name,
                     customer.c_first_name,
                     date_dim.d_date
     FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
          dfs.`tmp/date_dim.parquet` AS date_dim,
          dfs.`tmp/customer.parquet` AS customer WHERE catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
     AND catalog_sales.cs_bill_customer_sk = customer.c_customer_sk
     AND date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11 INTERSECT
     SELECT DISTINCT customer.c_last_name,
                     customer.c_first_name,
                     date_dim.d_date
     FROM dfs.`tmp/web_sales.parquet` AS web_sales,
          dfs.`tmp/date_dim.parquet` AS date_dim,
          dfs.`tmp/customer.parquet` AS customer WHERE web_sales.ws_sold_date_sk = date_dim.d_date_sk
     AND web_sales.ws_bill_customer_sk = customer.c_customer_sk
     AND date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11 ) hot_cust
LIMIT 100;

