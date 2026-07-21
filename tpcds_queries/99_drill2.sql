SELECT w_substr ,
       ship_mode.sm_type ,
       LOWER(call_center.cc_name) call_center.cc_name_lower ,
       sum(CASE
               WHEN (catalog_sales.cs_ship_date_sk - catalog_sales.cs_sold_date_sk <= 30) THEN 1
               ELSE 0
           END) AS "30 days",
       sum(CASE
               WHEN (catalog_sales.cs_ship_date_sk - catalog_sales.cs_sold_date_sk > 30)
                    AND (catalog_sales.cs_ship_date_sk - catalog_sales.cs_sold_date_sk <= 60) THEN 1
               ELSE 0
           END) AS "31-60 days",
       sum(CASE
               WHEN (catalog_sales.cs_ship_date_sk - catalog_sales.cs_sold_date_sk > 60)
                    AND (catalog_sales.cs_ship_date_sk - catalog_sales.cs_sold_date_sk <= 90) THEN 1
               ELSE 0
           END) AS "61-90 days",
       sum(CASE
               WHEN (catalog_sales.cs_ship_date_sk - catalog_sales.cs_sold_date_sk > 90)
                    AND (catalog_sales.cs_ship_date_sk - catalog_sales.cs_sold_date_sk <= 120) THEN 1
               ELSE 0
           END) AS "91-120 days",
       sum(CASE
               WHEN (catalog_sales.cs_ship_date_sk - catalog_sales.cs_sold_date_sk > 120) THEN 1
               ELSE 0
           END) AS ">120 days"
FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales ,
  (SELECT SUBSTRING(warehouse.w_warehouse_name,1,20) w_substr, *
   FROM dfs.`tmp/warehouse.parquet` AS warehouse) AS sq1 ,
     dfs.`tmp/ship_mode.parquet` AS ship_mode ,
     dfs.`tmp/call_center.parquet` AS call_center ,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11
  AND catalog_sales.cs_ship_date_sk = date_dim.d_date_sk
  AND catalog_sales.cs_warehouse_sk = warehouse.w_warehouse_sk
  AND catalog_sales.cs_ship_mode_sk = ship_mode.sm_ship_mode_sk
  AND catalog_sales.cs_call_center_sk = call_center.cc_call_center_sk
GROUP BY w_substr ,
         ship_mode.sm_type ,
         call_center.cc_name
ORDER BY w_substr  NULLS FIRST,
         ship_mode.sm_type  NULLS FIRST,
        call_center.cc_name_lower NULLS FIRST
LIMIT 100;

