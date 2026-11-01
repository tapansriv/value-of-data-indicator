SELECT sum(ws_ext_discount_amt) AS "Excess Discount Amount"
FROM 's3://vod-tpcds-10gb/web_sales.parquet' AS web_sales,
     's3://vod-tpcds-10gb/item.parquet' AS item,
     's3://vod-tpcds-10gb/date_dim.parquet' AS date_dim
WHERE i_manufact_id = 350
  AND i_item_sk = ws_item_sk
  AND d_date BETWEEN '2000-01-27' AND cast('2000-04-26' AS date)
  AND d_date_sk = ws_sold_date_sk
  AND ws_ext_discount_amt >
    (SELECT 1.3 * avg(ws_ext_discount_amt)
     FROM 's3://vod-tpcds-10gb/web_sales.parquet' AS web_sales,
          's3://vod-tpcds-10gb/date_dim.parquet' AS date_dim
     WHERE ws_item_sk = i_item_sk
       AND d_date BETWEEN '2000-01-27' AND cast('2000-04-26' AS date)
       AND d_date_sk = ws_sold_date_sk )
ORDER BY sum(ws_ext_discount_amt)
LIMIT 100;

