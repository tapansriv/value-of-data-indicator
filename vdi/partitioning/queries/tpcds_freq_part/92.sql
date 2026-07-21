SELECT
  SUM(ws_ext_discount_amt) AS "Excess Discount Amount"
FROM READ_PARQUET('web_sales.parquet') AS web_sales, READ_PARQUET('item.parquet') AS item, READ_PARQUET('/home/cc/tpcds_partitioned_freq/date_dim/**/*.parquet', hive_partitioning = 1) AS date_dim
WHERE
  i_manufact_id = 350
  AND i_item_sk = ws_item_sk
  AND d_date BETWEEN '2000-01-27' AND CAST('2000-04-26' AS DATE)
  AND d_date_sk = ws_sold_date_sk
  AND ws_ext_discount_amt > (
      SELECT
        1.3 * AVG(ws_ext_discount_amt)
      FROM READ_PARQUET('web_sales.parquet') AS web_sales, READ_PARQUET('/home/cc/tpcds_partitioned_freq/date_dim/**/*.parquet', hive_partitioning = 1) AS date_dim
      WHERE
        ws_item_sk = i_item_sk
        AND d_date BETWEEN '2000-01-27' AND CAST('2000-04-26' AS DATE)
        AND d_date_sk = ws_sold_date_sk
  )
ORDER BY
  SUM(ws_ext_discount_amt)
LIMIT 100