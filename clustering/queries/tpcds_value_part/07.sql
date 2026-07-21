SELECT
  i_item_id,
  AVG(ss_quantity) AS agg1,
  AVG(ss_list_price) AS agg2,
  AVG(ss_coupon_amt) AS agg3,
  AVG(ss_sales_price) AS agg4
FROM READ_PARQUET('/home/cc/tpcds_cluster_base/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_demographics/*.parquet') AS customer_demographics, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item, READ_PARQUET('/home/cc/tpcds_cluster_base/promotion/*.parquet') AS promotion
WHERE
  ss_sold_date_sk = d_date_sk
  AND ss_item_sk = i_item_sk
  AND ss_cdemo_sk = cd_demo_sk
  AND ss_promo_sk = p_promo_sk
  AND cd_gender = 'M'
  AND cd_marital_status = 'S'
  AND cd_education_status = 'College'
  AND (
    p_channel_email = 'N' OR p_channel_event = 'N'
  )
  AND d_year = 2000
GROUP BY
  i_item_id
ORDER BY
  i_item_id
LIMIT 100