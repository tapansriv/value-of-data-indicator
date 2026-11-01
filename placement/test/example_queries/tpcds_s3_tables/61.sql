SELECT promotions,
       total,
       cast(promotions AS decimal(15,4))/cast(total AS decimal(15,4))*100
FROM
  (SELECT sum(ss_ext_sales_price) promotions
   FROM 's3://vod-tpcds-10gb/store_sales.parquet' AS store_sales,
        's3://vod-tpcds-10gb/store.parquet' AS store,
        's3://vod-tpcds-10gb/promotion.parquet' AS promotion,
        's3://vod-tpcds-10gb/date_dim.parquet' AS date_dim,
        's3://vod-tpcds-10gb/customer.parquet' AS customer,
        's3://vod-tpcds-10gb/customer_address.parquet' AS customer_address,
        's3://vod-tpcds-10gb/item.parquet' AS item
   WHERE ss_sold_date_sk = d_date_sk
     AND ss_store_sk = s_store_sk
     AND ss_promo_sk = p_promo_sk
     AND ss_customer_sk= c_customer_sk
     AND ca_address_sk = c_current_addr_sk
     AND ss_item_sk = i_item_sk
     AND ca_gmt_offset = -5
     AND i_category = 'Jewelry'
     AND (p_channel_dmail = 'Y'
          OR p_channel_email = 'Y'
          OR p_channel_tv = 'Y')
     AND s_gmt_offset = -5
     AND d_year = 1998
     AND d_moy = 11) promotional_sales,
  (SELECT sum(ss_ext_sales_price) total
   FROM 's3://vod-tpcds-10gb/store_sales.parquet' AS store_sales,
        's3://vod-tpcds-10gb/store.parquet' AS store,
        's3://vod-tpcds-10gb/date_dim.parquet' AS date_dim,
        's3://vod-tpcds-10gb/customer.parquet' AS customer,
        's3://vod-tpcds-10gb/customer_address.parquet' AS customer_address,
        's3://vod-tpcds-10gb/item.parquet' AS item
   WHERE ss_sold_date_sk = d_date_sk
     AND ss_store_sk = s_store_sk
     AND ss_customer_sk= c_customer_sk
     AND ca_address_sk = c_current_addr_sk
     AND ss_item_sk = i_item_sk
     AND ca_gmt_offset = -5
     AND i_category = 'Jewelry'
     AND s_gmt_offset = -5
     AND d_year = 1998
     AND d_moy = 11) all_sales
ORDER BY promotions,
         total
LIMIT 100;

