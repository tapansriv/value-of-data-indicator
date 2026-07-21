SELECT case when pmc=0 then null else cast(amc AS decimal(15,4))/cast(pmc AS decimal(15,4)) end am_pm_ratio
FROM
  (SELECT count(*) amc
   FROM dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/household_demographics.parquet` AS household_demographics,
        dfs.`tmp/time_dim.parquet` AS time_dim,
        dfs.`tmp/web_page.parquet` AS web_page
   WHERE web_sales.ws_sold_time_sk = time_dim.t_time_sk
     AND web_sales.ws_ship_hdemo_sk = household_demographics.hd_demo_sk
     AND web_sales.ws_web_page_sk = web_page.wp_web_page_sk
     AND time_dim.t_hour BETWEEN 8 AND 8+1
     AND household_demographics.hd_dep_count = 6
     AND web_page.wp_char_count BETWEEN 5000 AND 5200) AT,
  (SELECT count(*) pmc
   FROM dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/household_demographics.parquet` AS household_demographics,
        dfs.`tmp/time_dim.parquet` AS time_dim,
        dfs.`tmp/web_page.parquet` AS web_page
   WHERE web_sales.ws_sold_time_sk = time_dim.t_time_sk
     AND web_sales.ws_ship_hdemo_sk = household_demographics.hd_demo_sk
     AND web_sales.ws_web_page_sk = web_page.wp_web_page_sk
     AND time_dim.t_hour BETWEEN 19 AND 19+1
     AND household_demographics.hd_dep_count = 6
     AND web_page.wp_char_count BETWEEN 5000 AND 5200) pt
ORDER BY am_pm_ratio
LIMIT 100;

