SELECT item.i_item_id,
       item.i_item_desc,
       store.s_state,
       count(store_sales.ss_quantity) AS store_sales_quantitycount,
       avg(store_sales.ss_quantity) AS store_sales_quantityave,
       stddev_samp(store_sales.ss_quantity) AS store_sales_quantitystdev,
       stddev_samp(store_sales.ss_quantity)/avg(store_sales.ss_quantity) AS store_sales_quantitycov,
       count(store_returns.sr_return_quantity) AS store_returns_quantitycount,
       avg(store_returns.sr_return_quantity) AS store_returns_quantityave,
       stddev_samp(store_returns.sr_return_quantity) AS store_returns_quantitystdev,
       stddev_samp(store_returns.sr_return_quantity)/avg(store_returns.sr_return_quantity) AS store_returns_quantitycov,
       count(catalog_sales.cs_quantity) AS catalog_sales_quantitycount,
       avg(catalog_sales.cs_quantity) AS catalog_sales_quantityave,
       stddev_samp(catalog_sales.cs_quantity) AS catalog_sales_quantitystdev,
       stddev_samp(catalog_sales.cs_quantity)/avg(catalog_sales.cs_quantity) AS catalog_sales_quantitycov
FROM dfs.`tmp/store_sales.parquet` AS store_sales,
     dfs.`tmp/store_returns.parquet` AS store_returns,
     dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
     dfs.`tmp/date_dim.parquet` d1,
     dfs.`tmp/date_dim.parquet` d2,
     dfs.`tmp/date_dim.parquet` d3,
     dfs.`tmp/store.parquet` AS store,
     dfs.`tmp/item.parquet` AS item
WHERE d1.d_quarter_name = '2001Q1'
  AND d1.d_date_sk = store_sales.ss_sold_date_sk
  AND item.i_item_sk = store_sales.ss_item_sk
  AND store.s_store_sk = store_sales.ss_store_sk
  AND store_sales.ss_customer_sk = store_returns.sr_customer_sk
  AND store_sales.ss_item_sk = store_returns.sr_item_sk
  AND store_sales.ss_ticket_number = store_returns.sr_ticket_number
  AND store_returns.sr_returned_date_sk = d2.d_date_sk
  AND d2.d_quarter_name IN ('2001Q1',
                            '2001Q2',
                            '2001Q3')
  AND store_returns.sr_customer_sk = catalog_sales.cs_bill_customer_sk
  AND store_returns.sr_item_sk = catalog_sales.cs_item_sk
  AND catalog_sales.cs_sold_date_sk = d3.d_date_sk
  AND d3.d_quarter_name IN ('2001Q1',
                            '2001Q2',
                            '2001Q3')
GROUP BY item.i_item_id,
         item.i_item_desc,
         store.s_state
ORDER BY item.i_item_id NULLS FIRST,
         item.i_item_desc NULLS FIRST,
         store.s_state NULLS FIRST
LIMIT 100;

