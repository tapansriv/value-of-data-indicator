SELECT
  i_brand_id AS brand_id,
  i_brand AS brand,
  SUM(ss_ext_sales_price) AS ext_price
FROM READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item
WHERE
  d_date_sk = ss_sold_date_sk
  AND ss_item_sk = i_item_sk
  AND i_manager_id = 28
  AND d_moy = 11
  AND d_year = 1999
GROUP BY
  i_brand,
  i_brand_id
ORDER BY
  ext_price DESC,
  i_brand_id
LIMIT 100