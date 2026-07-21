SELECT
  COUNT(*)
FROM READ_PARQUET('store_sales.parquet') AS store_sales, READ_PARQUET('household_demographics.parquet') AS household_demographics, READ_PARQUET('time_dim.parquet') AS time_dim, READ_PARQUET('store.parquet') AS store
WHERE
  ss_sold_time_sk = time_dim.t_time_sk
  AND ss_hdemo_sk = household_demographics.hd_demo_sk
  AND ss_store_sk = s_store_sk
  AND time_dim.t_hour = 20
  AND time_dim.t_minute >= 30
  AND household_demographics.hd_dep_count = 7
  AND store.s_store_name = 'ese'
ORDER BY
  COUNT(*)
LIMIT 100