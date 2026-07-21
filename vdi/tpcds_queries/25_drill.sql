
SELECT i_item_id ,
       i_item_desc ,
       s_store_id ,
       s_store_name ,
       sum(ss_net_profit) AS store_sales_profit ,
       sum(sr_net_loss) AS store_returns_loss ,
       sum(cs_net_profit) AS catalog_sales_profit
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
  AND d1.d_date_sk = ss_sold_date_sk
  AND i_item_sk = ss_item_sk
  AND s_store_sk = ss_store_sk
  AND ss_customer_sk = sr_customer_sk
  AND ss_item_sk = sr_item_sk
  AND ss_ticket_number = sr_ticket_number
  AND sr_returned_date_sk = d2.d_date_sk
  AND d2.d_moy BETWEEN 4 AND 10
  AND d2.d_year = 2001
  AND sr_customer_sk = cs_bill_customer_sk
  AND sr_item_sk = cs_item_sk
  AND cs_sold_date_sk = d3.d_date_sk
  AND d3.d_moy BETWEEN 4 AND 10
  AND d3.d_year = 2001
GROUP BY i_item_id ,
         i_item_desc ,
         s_store_id ,
         s_store_name
ORDER BY i_item_id ,
         i_item_desc ,
         s_store_id ,
         s_store_name
LIMIT 100;

