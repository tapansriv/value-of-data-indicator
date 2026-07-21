SELECT w_substr,
       ship_mode.sm_type,
       web_site.web_name,
       sum(CASE
               WHEN (web_sales.ws_ship_date_sk - web_sales.ws_sold_date_sk <= 30) THEN 1
               ELSE 0
           END) AS "30 days",
       sum(CASE
               WHEN (web_sales.ws_ship_date_sk - web_sales.ws_sold_date_sk > 30)
                    AND (web_sales.ws_ship_date_sk - web_sales.ws_sold_date_sk <= 60) THEN 1
               ELSE 0
           END) AS "31-60 days",
       sum(CASE
               WHEN (web_sales.ws_ship_date_sk - web_sales.ws_sold_date_sk > 60)
                    AND (web_sales.ws_ship_date_sk - web_sales.ws_sold_date_sk <= 90) THEN 1
               ELSE 0
           END) AS "61-90 days",
       sum(CASE
               WHEN (web_sales.ws_ship_date_sk - web_sales.ws_sold_date_sk > 90)
                    AND (web_sales.ws_ship_date_sk - web_sales.ws_sold_date_sk <= 120) THEN 1
               ELSE 0
           END) AS "91-120 days",
       sum(CASE
               WHEN (web_sales.ws_ship_date_sk - web_sales.ws_sold_date_sk > 120) THEN 1
               ELSE 0
           END) AS ">120 days"
FROM dfs.`tmp/web_sales.parquet` AS web_sales,
  (SELECT SUBSTRING(warehouse.w_warehouse_name,1,20) w_substr,
          *
   FROM dfs.`tmp/warehouse.parquet` AS warehouse) sq1,
     dfs.`tmp/ship_mode.parquet` AS ship_mode,
     dfs.`tmp/web_site.parquet` AS web_site,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11
  AND web_sales.ws_ship_date_sk = date_dim.d_date_sk
  AND web_sales.ws_warehouse_sk = warehouse.w_warehouse_sk
  AND web_sales.ws_ship_mode_sk = ship_mode.sm_ship_mode_sk
  AND web_sales.ws_web_site_sk = web_site.web_site_sk
GROUP BY w_substr,
         ship_mode.sm_type,
         web_site.web_name
ORDER BY 1 NULLS FIRST,
         2 NULLS FIRST,
         3 NULLS FIRST
LIMIT 100;

