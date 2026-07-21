WITH ssci AS
  (SELECT store_sales.ss_customer_sk customer_sk ,
          store_sales.ss_item_sk item_sk
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11
   GROUP BY store_sales.ss_customer_sk ,
            store_sales.ss_item_sk),
csci as
  ( SELECT catalog_sales.cs_bill_customer_sk customer_sk ,catalog_sales.cs_item_sk item_sk
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11
   GROUP BY catalog_sales.cs_bill_customer_sk ,catalog_sales.cs_item_sk)
SELECT sum(CASE
               WHEN ssci.customer_sk IS NOT NULL
                    AND csci.customer_sk IS NULL THEN 1
               ELSE 0
           END) store_only ,
       sum(CASE
               WHEN ssci.customer_sk IS NULL
                    AND csci.customer_sk IS NOT NULL THEN 1
               ELSE 0
           END) catalog_only ,
       sum(CASE
               WHEN ssci.customer_sk IS NOT NULL
                    AND csci.customer_sk IS NOT NULL THEN 1
               ELSE 0
           END) store_and_catalog
FROM ssci
FULL OUTER JOIN csci ON (ssci.customer_sk=csci.customer_sk
                         AND ssci.item_sk = csci.item_sk)
LIMIT 100;

