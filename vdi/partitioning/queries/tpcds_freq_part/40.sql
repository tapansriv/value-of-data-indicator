SELECT
  w_state,
  i_item_id,
  SUM(
    CASE
      WHEN (
        CAST(d_date AS DATE) < CAST('2000-03-11' AS DATE)
      )
      THEN cs_sales_price - COALESCE(cr_refunded_cash, 0)
      ELSE 0
    END
  ) AS sales_before,
  SUM(
    CASE
      WHEN (
        CAST(d_date AS DATE) >= CAST('2000-03-11' AS DATE)
      )
      THEN cs_sales_price - COALESCE(cr_refunded_cash, 0)
      ELSE 0
    END
  ) AS sales_after
FROM READ_PARQUET('catalog_sales.parquet') AS catalog_sales
LEFT OUTER JOIN READ_PARQUET('catalog_returns.parquet') AS catalog_returns
  ON (
    cs_order_number = cr_order_number AND cs_item_sk = cr_item_sk
  ), READ_PARQUET('warehouse.parquet') AS warehouse, READ_PARQUET('item.parquet') AS item, READ_PARQUET('/home/cc/tpcds_partitioned_freq/date_dim/**/*.parquet', hive_partitioning = 1) AS date_dim
WHERE
  i_current_price BETWEEN 0.99 AND 1.49
  AND i_item_sk = cs_item_sk
  AND cs_warehouse_sk = w_warehouse_sk
  AND cs_sold_date_sk = d_date_sk
  AND d_date BETWEEN CAST('2000-02-10' AS DATE) AND CAST('2000-04-10' AS DATE)
GROUP BY
  w_state,
  i_item_id
ORDER BY
  w_state,
  i_item_id
LIMIT 100