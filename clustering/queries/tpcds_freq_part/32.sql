SELECT
  SUM(cs_ext_discount_amt) AS "excess discount amount"
FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS catalog_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item, READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim
WHERE
  i_manufact_id = 977
  AND i_item_sk = cs_item_sk
  AND d_date BETWEEN '2000-01-27' AND CAST('2000-04-26' AS DATE)
  AND d_date_sk = cs_sold_date_sk
  AND cs_ext_discount_amt > (
      SELECT
        1.3 * AVG(cs_ext_discount_amt)
      FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS catalog_sales, READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim
      WHERE
        cs_item_sk = i_item_sk
        AND d_date BETWEEN '2000-01-27' AND CAST('2000-04-26' AS DATE)
        AND d_date_sk = cs_sold_date_sk
  )
LIMIT 100