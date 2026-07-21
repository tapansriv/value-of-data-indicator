SELECT item.i_item_id,
       item.i_item_desc,
       store.s_store_id,
       store.s_store_name,
       sum(store_sales.ss_quantity) AS store_sales_quantity,
       sum(store_returns.sr_return_quantity) AS store_returns_quantity,
       sum(catalog_sales.cs_quantity) AS catalog_sales_quantity
FROM dfs.`tmp/store_sales.parquet` AS store_sales,
     dfs.`tmp/store_returns.parquet` AS store_returns,
     dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
     dfs.`tmp/date_dim.parquet` d1,
     dfs.`tmp/date_dim.parquet` d2,
     dfs.`tmp/date_dim.parquet` d3,
     dfs.`tmp/store.parquet` AS store,
     dfs.`tmp/item.parquet` AS item
WHERE d1.d_moy = 9
  AND d1.d_year = 1999
  AND d1.d_date_sk = store_sales.ss_sold_date_sk
  AND item.i_item_sk = store_sales.ss_item_sk
  AND store.s_store_sk = store_sales.ss_store_sk
  AND store_sales.ss_customer_sk = store_returns.sr_customer_sk
  AND store_sales.ss_item_sk = store_returns.sr_item_sk
  AND store_sales.ss_ticket_number = store_returns.sr_ticket_number
  AND store_returns.sr_returned_date_sk = d2.d_date_sk
  AND d2.d_moy BETWEEN 9 AND 9 + 3
  AND d2.d_year = 1999
  AND store_returns.sr_customer_sk = catalog_sales.cs_bill_customer_sk
  AND store_returns.sr_item_sk = catalog_sales.cs_item_sk
  AND catalog_sales.cs_sold_date_sk = d3.d_date_sk
  AND d3.d_year IN (1999,
                    1999+1,
                    1999+2)
GROUP BY item.i_item_id,
         item.i_item_desc,
         store.s_store_id,
         store.s_store_name
ORDER BY item.i_item_id,
         item.i_item_desc,
         store.s_store_id,
         store.s_store_name
LIMIT 100;

