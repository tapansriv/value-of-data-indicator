SELECT
  dt.d_year,
  item.i_category_id,
  item.i_category,
  SUM(ss_ext_sales_price)
FROM READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS dt, READ_PARQUET('/home/cc/tpcds_cluster_base/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item
WHERE
  dt.d_date_sk = store_sales.ss_sold_date_sk
  AND store_sales.ss_item_sk = item.i_item_sk
  AND item.i_manager_id = 1
  AND dt.d_moy = 11
  AND dt.d_year = 2000
GROUP BY
  dt.d_year,
  item.i_category_id,
  item.i_category
ORDER BY
  SUM(ss_ext_sales_price) DESC,
  dt.d_year,
  item.i_category_id,
  item.i_category
LIMIT 100