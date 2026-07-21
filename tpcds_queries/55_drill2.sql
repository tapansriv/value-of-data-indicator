SELECT item.i_brand_id brand_id,
       item.i_brand brand,
       sum(store_sales.ss_ext_sales_price) ext_price
FROM dfs.`tmp/date_dim.parquet` AS date_dim,
     dfs.`tmp/store_sales.parquet` AS store_sales,
     dfs.`tmp/item.parquet` AS item
WHERE date_dim.d_date_sk = store_sales.ss_sold_date_sk
  AND store_sales.ss_item_sk = item.i_item_sk
  AND item.i_manager_id=28
  AND date_dim.d_moy=11
  AND date_dim.d_year=1999
GROUP BY item.i_brand,
         item.i_brand_id
ORDER BY ext_price DESC,
         item.i_brand_id
LIMIT 100 ;

