SELECT
  i_item_id,
  AVG(cs_quantity) AS agg1,
  AVG(cs_list_price) AS agg2,
  AVG(cs_coupon_amt) AS agg3,
  AVG(cs_sales_price) AS agg4
FROM READ_PARQUET('catalog_sales.parquet') AS catalog_sales, READ_PARQUET('customer_demographics.parquet') AS customer_demographics, READ_PARQUET('date_dim.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_partitioned_value/item/**/*.parquet', hive_partitioning = 1) AS item, READ_PARQUET('promotion.parquet') AS promotion
WHERE
  cs_sold_date_sk = d_date_sk
  AND cs_item_sk = i_item_sk
  AND cs_bill_cdemo_sk = cd_demo_sk
  AND cs_promo_sk = p_promo_sk
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