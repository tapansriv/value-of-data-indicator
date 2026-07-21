SELECT item.i_brand_id brand_id,
       item.i_brand brand,
       time_dim.t_hour,
       time_dim.t_minute,
       sum(ext_price) ext_price
FROM dfs.`tmp/item.parquet` AS item,
  (SELECT web_sales.ws_ext_sales_price AS ext_price,
          web_sales.ws_sold_date_sk AS sold_date_sk,
          web_sales.ws_item_sk AS sold_item_sk,
          web_sales.ws_sold_time_sk AS time_sk
   FROM dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE date_dim.d_date_sk = web_sales.ws_sold_date_sk
     AND date_dim.d_moy=11
     AND date_dim.d_year=1999
   UNION ALL SELECT catalog_sales.cs_ext_sales_price AS ext_price,
                    catalog_sales.cs_sold_date_sk AS sold_date_sk,
                    catalog_sales.cs_item_sk AS sold_item_sk,
                    catalog_sales.cs_sold_time_sk AS time_sk
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE date_dim.d_date_sk = catalog_sales.cs_sold_date_sk
     AND date_dim.d_moy=11
     AND date_dim.d_year=1999
   UNION ALL SELECT store_sales.ss_ext_sales_price AS ext_price,
                    store_sales.ss_sold_date_sk AS sold_date_sk,
                    store_sales.ss_item_sk AS sold_item_sk,
                    store_sales.ss_sold_time_sk AS time_sk
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE date_dim.d_date_sk = store_sales.ss_sold_date_sk
     AND date_dim.d_moy=11
     AND date_dim.d_year=1999 ) tmp,
     dfs.`tmp/time_dim.parquet` AS time_dim
WHERE sold_item_sk = item.i_item_sk
  AND item.i_manager_id=1
  AND time_sk = time_dim.t_time_sk
  AND (time_dim.t_meal_time = 'breakfast'
       OR time_dim.t_meal_time = 'dinner')
GROUP BY item.i_brand,
         item.i_brand_id,
         time_dim.t_hour,
         time_dim.t_minute
ORDER BY ext_price DESC NULLS FIRST,
         item.i_brand_id NULLS FIRST;

