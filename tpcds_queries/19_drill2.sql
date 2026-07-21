SELECT item.i_brand_id brand_id,
       item.i_brand brand,
       item.i_manufact_id,
       item.i_manufact,
       sum(store_sales.ss_ext_sales_price) ext_price
FROM dfs.`tmp/date_dim.parquet` AS date_dim,
     dfs.`tmp/store_sales.parquet` AS store_sales,
     dfs.`tmp/item.parquet` AS item,
     dfs.`tmp/customer.parquet` AS customer,
     dfs.`tmp/customer_address.parquet` AS customer_address,
     dfs.`tmp/store.parquet` AS store
WHERE date_dim.d_date_sk = store_sales.ss_sold_date_sk
  AND store_sales.ss_item_sk = item.i_item_sk
  AND item.i_manager_id=8
  AND date_dim.d_moy=11
  AND date_dim.d_year=1998
  AND store_sales.ss_customer_sk = customer.c_customer_sk
  AND customer.c_current_addr_sk = customer_address.ca_address_sk
  AND SUBSTRING(customer_address.ca_zip, 1, 5) <> SUBSTRING(store.s_zip, 1, 5)
  AND store_sales.ss_store_sk = store.s_store_sk
GROUP BY item.i_brand,
         item.i_brand_id,
         item.i_manufact_id,
         item.i_manufact
ORDER BY ext_price DESC,
         item.i_brand,
         item.i_brand_id,
         item.i_manufact_id,
         item.i_manufact
LIMIT 100 ;

