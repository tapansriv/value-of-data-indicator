SELECT promotions,
       total,
       cast(promotions AS decimal(15,4))/cast(total AS decimal(15,4))*100
FROM
  (SELECT sum(store_sales.ss_ext_sales_price) promotions
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/promotion.parquet` AS promotion,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/customer_address.parquet` AS customer_address,
        dfs.`tmp/item.parquet` AS item
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND store_sales.ss_promo_sk = promotion.p_promo_sk
     AND store_sales.ss_customer_sk= customer.c_customer_sk
     AND customer_address.ca_address_sk = customer.c_current_addr_sk
     AND store_sales.ss_item_sk = item.i_item_sk
     AND customer_address.ca_gmt_offset = -5
     AND item.i_category = 'Jewelry'
     AND (promotion.p_channel_dmail = 'Y'
          OR promotion.p_channel_email = 'Y'
          OR promotion.p_channel_tv = 'Y')
     AND store.s_gmt_offset = -5
     AND date_dim.d_year = 1998
     AND date_dim.d_moy = 11) promotional_sales,
  (SELECT sum(store_sales.ss_ext_sales_price) total
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/customer_address.parquet` AS customer_address,
        dfs.`tmp/item.parquet` AS item
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND store_sales.ss_customer_sk= customer.c_customer_sk
     AND customer_address.ca_address_sk = customer.c_current_addr_sk
     AND store_sales.ss_item_sk = item.i_item_sk
     AND customer_address.ca_gmt_offset = -5
     AND item.i_category = 'Jewelry'
     AND store.s_gmt_offset = -5
     AND date_dim.d_year = 1998
     AND date_dim.d_moy = 11) all_sales
ORDER BY promotions,
         total
LIMIT 100;

