SELECT
  promotions,
  total,
  CAST(promotions AS DECIMAL(15, 4)) / CAST(total AS DECIMAL(15, 4)) * 100
FROM (
    SELECT
      SUM(ss_ext_sales_price) AS promotions
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/store/*.parquet') AS store, READ_PARQUET('/home/cc/tpcds_cluster_base/promotion/*.parquet') AS promotion, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/customer/*.parquet') AS customer, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_address/*.parquet') AS customer_address, READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item
    WHERE
      ss_sold_date_sk = d_date_sk
      AND ss_store_sk = s_store_sk
      AND ss_promo_sk = p_promo_sk
      AND ss_customer_sk = c_customer_sk
      AND ca_address_sk = c_current_addr_sk
      AND ss_item_sk = i_item_sk
      AND ca_gmt_offset = -5
      AND i_category = 'Jewelry'
      AND (
        p_channel_dmail = 'Y' OR p_channel_email = 'Y' OR p_channel_tv = 'Y'
      )
      AND s_gmt_offset = -5
      AND d_year = 1998
      AND d_moy = 11
) AS promotional_sales, (
    SELECT
      SUM(ss_ext_sales_price) AS total
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/store/*.parquet') AS store, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/customer/*.parquet') AS customer, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_address/*.parquet') AS customer_address, READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item
    WHERE
      ss_sold_date_sk = d_date_sk
      AND ss_store_sk = s_store_sk
      AND ss_customer_sk = c_customer_sk
      AND ca_address_sk = c_current_addr_sk
      AND ss_item_sk = i_item_sk
      AND ca_gmt_offset = -5
      AND i_category = 'Jewelry'
      AND s_gmt_offset = -5
      AND d_year = 1998
      AND d_moy = 11
) AS all_sales
ORDER BY
  promotions,
  total
LIMIT 100