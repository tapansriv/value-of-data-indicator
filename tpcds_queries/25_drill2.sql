
SELECT item.i_item_id ,
       item.i_item_desc ,
       store.s_store_id ,
       store.s_store_name ,
       sum(store_sales.ss_net_profit) AS store_sales_profit ,
       sum(store_returns.sr_net_loss) AS store_returns_loss ,
       sum(catalog_sales.cs_net_profit) AS catalog_sales_profit
FROM dfs.`tmp/store_sales.parquet` AS store_sales ,
     dfs.`tmp/store_returns.parquet` AS store_returns ,
     dfs.`tmp/catalog_sales.parquet` AS catalog_sales ,
     dfs.`tmp/date_dim.parquet` d1 ,
     dfs.`tmp/date_dim.parquet` d2 ,
     dfs.`tmp/date_dim.parquet` d3 ,
     dfs.`tmp/store.parquet` AS store ,
     dfs.`tmp/item.parquet` AS item
WHERE d1.d_moy = 4
  AND d1.d_year = 2001
  AND d1.d_date_sk = store_sales.ss_sold_date_sk
  AND item.i_item_sk = store_sales.ss_item_sk
  AND store.s_store_sk = store_sales.ss_store_sk
  AND store_sales.ss_customer_sk = store_returns.sr_customer_sk
  AND store_sales.ss_item_sk = store_returns.sr_item_sk
  AND store_sales.ss_ticket_number = store_returns.sr_ticket_number
  AND store_returns.sr_returned_date_sk = d2.d_date_sk
  AND d2.d_moy BETWEEN 4 AND 10
  AND d2.d_year = 2001
  AND store_returns.sr_customer_sk = catalog_sales.cs_bill_customer_sk
  AND store_returns.sr_item_sk = catalog_sales.cs_item_sk
  AND catalog_sales.cs_sold_date_sk = d3.d_date_sk
  AND d3.d_moy BETWEEN 4 AND 10
  AND d3.d_year = 2001
GROUP BY item.i_item_id ,
         item.i_item_desc ,
         store.s_store_id ,
         store.s_store_name
ORDER BY item.i_item_id ,
         item.i_item_desc ,
         store.s_store_id ,
         store.s_store_name
LIMIT 100;

