SELECT sum(web_sales.ws_ext_discount_amt) AS "Excess Discount Amount"
FROM dfs.`tmp/web_sales.parquet` AS web_sales,
     dfs.`tmp/item.parquet` AS item,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE item.i_manufact_id = 350
  AND item.i_item_sk = web_sales.ws_item_sk
  AND date_dim.d_date BETWEEN '2000-01-27' AND cast('2000-04-26' AS date)
  AND date_dim.d_date_sk = web_sales.ws_sold_date_sk
  AND web_sales.ws_ext_discount_amt >
    (SELECT 1.3 * avg(web_sales.ws_ext_discount_amt)
     FROM dfs.`tmp/web_sales.parquet` AS web_sales,
          dfs.`tmp/date_dim.parquet` AS date_dim
     WHERE web_sales.ws_item_sk = item.i_item_sk
       AND date_dim.d_date BETWEEN '2000-01-27' AND cast('2000-04-26' AS date)
       AND date_dim.d_date_sk = web_sales.ws_sold_date_sk )
ORDER BY sum(web_sales.ws_ext_discount_amt)
LIMIT 100;

