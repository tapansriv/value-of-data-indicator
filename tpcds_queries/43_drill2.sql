
SELECT store.s_store_name,
       store.s_store_id,
       sum(CASE
               WHEN (date_dim.d_day_name='Sunday') THEN store_sales.ss_sales_price
               ELSE NULL
           END) sun_sales,
       sum(CASE
               WHEN (date_dim.d_day_name='Monday') THEN store_sales.ss_sales_price
               ELSE NULL
           END) mon_sales,
       sum(CASE
               WHEN (date_dim.d_day_name='Tuesday') THEN store_sales.ss_sales_price
               ELSE NULL
           END) tue_sales,
       sum(CASE
               WHEN (date_dim.d_day_name='Wednesday') THEN store_sales.ss_sales_price
               ELSE NULL
           END) wed_sales,
       sum(CASE
               WHEN (date_dim.d_day_name='Thursday') THEN store_sales.ss_sales_price
               ELSE NULL
           END) thu_sales,
       sum(CASE
               WHEN (date_dim.d_day_name='Friday') THEN store_sales.ss_sales_price
               ELSE NULL
           END) fri_sales,
       sum(CASE
               WHEN (date_dim.d_day_name='Saturday') THEN store_sales.ss_sales_price
               ELSE NULL
           END) sat_sales
FROM dfs.`tmp/date_dim.parquet` AS date_dim,
     dfs.`tmp/store_sales.parquet` AS store_sales,
     dfs.`tmp/store.parquet` AS store
WHERE date_dim.d_date_sk = store_sales.ss_sold_date_sk
  AND store.s_store_sk = store_sales.ss_store_sk
  AND store.s_gmt_offset = -5
  AND date_dim.d_year = 2000
GROUP BY store.s_store_name,
         store.s_store_id
ORDER BY store.s_store_name,
         store.s_store_id,
         sun_sales,
         mon_sales,
         tue_sales,
         wed_sales,
         thu_sales,
         fri_sales,
         sat_sales
LIMIT 100;

