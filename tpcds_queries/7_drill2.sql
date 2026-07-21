SELECT item.i_item_id,
       avg(store_sales.ss_quantity) agg1,
       avg(store_sales.ss_list_price) agg2,
       avg(store_sales.ss_coupon_amt) agg3,
       avg(store_sales.ss_sales_price) agg4
FROM dfs.`tmp/store_sales.parquet` AS store_sales,
     dfs.`tmp/customer_demographics.parquet` AS customer_demographics,
     dfs.`tmp/date_dim.parquet` AS date_dim,
     dfs.`tmp/item.parquet` AS item,
     dfs.`tmp/promotion.parquet` AS promotion
WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
  AND store_sales.ss_item_sk = item.i_item_sk
  AND store_sales.ss_cdemo_sk = customer_demographics.cd_demo_sk
  AND store_sales.ss_promo_sk = promotion.p_promo_sk
  AND customer_demographics.cd_gender = 'M'
  AND customer_demographics.cd_marital_status = 'S'
  AND customer_demographics.cd_education_status = 'College'
  AND (promotion.p_channel_email = 'N'
       OR promotion.p_channel_event = 'N')
  AND date_dim.d_year = 2000
GROUP BY item.i_item_id
ORDER BY item.i_item_id
LIMIT 100;

