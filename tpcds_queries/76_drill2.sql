SELECT channel,
       col_name,
       date_dim.d_year,
       date_dim.d_qoy,
       item.i_category,
       COUNT(*) sales_cnt,
       SUM(ext_sales_price) sales_amt
FROM
  ( SELECT 'store' AS channel,
           'ss_store_sk' col_name,
                         date_dim.d_year,
                         date_dim.d_qoy,
                         item.i_category,
                         store_sales.ss_ext_sales_price ext_sales_price
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE store_sales.ss_store_sk IS NULL
     AND store_sales.ss_sold_date_sk=d_date_sk
     AND store_sales.ss_item_sk=i_item_sk
   UNION ALL SELECT 'web' AS channel,
                    'ws_ship_customer_sk' col_name,
                                          date_dim.d_year,
                                          date_dim.d_qoy,
                                          item.i_category,
                                          web_sales.ws_ext_sales_price ext_sales_price
   FROM dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE web_sales.ws_ship_customer_sk IS NULL
     AND web_sales.ws_sold_date_sk=d_date_sk
     AND web_sales.ws_item_sk=i_item_sk
   UNION ALL SELECT 'catalog' AS channel,
                    'cs_ship_addr_sk' col_name,
                                      date_dim.d_year,
                                      date_dim.d_qoy,
                                      item.i_category,
                                      catalog_sales.cs_ext_sales_price ext_sales_price
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE catalog_sales.cs_ship_addr_sk IS NULL
     AND catalog_sales.cs_sold_date_sk=d_date_sk
     AND catalog_sales.cs_item_sk=i_item_sk) foo
GROUP BY channel,
         col_name,
         date_dim.d_year,
         date_dim.d_qoy,
         item.i_category
ORDER BY channel NULLS FIRST,
         col_name NULLS FIRST,
         date_dim.d_year NULLS FIRST,
         date_dim.d_qoy NULLS FIRST,
         item.i_category NULLS FIRST
LIMIT 100;

