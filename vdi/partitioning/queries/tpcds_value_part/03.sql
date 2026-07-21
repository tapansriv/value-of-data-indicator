SELECT
  dt.d_year,
  item.i_brand_id AS brand_id,
  item.i_brand AS brand,
  SUM(ss_ext_sales_price) AS sum_agg
FROM READ_PARQUET('date_dim.parquet') AS dt, READ_PARQUET('store_sales.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_partitioned_value/item/**/*.parquet', hive_partitioning = 1) AS item
WHERE
  dt.d_date_sk = store_sales.ss_sold_date_sk
  AND store_sales.ss_item_sk = item.i_item_sk
  AND item.i_manufact_id = 128
  AND dt.d_moy = 11
GROUP BY
  dt.d_year,
  item.i_brand,
  item.i_brand_id
ORDER BY
  dt.d_year,
  sum_agg DESC,
  brand_id
LIMIT 100