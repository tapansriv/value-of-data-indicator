SELECT
  CASE
    WHEN pmc = 0
    THEN NULL
    ELSE CAST(amc AS DECIMAL(15, 4)) / CAST(pmc AS DECIMAL(15, 4))
  END AS am_pm_ratio
FROM (
    SELECT
      COUNT(*) AS amc
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS web_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/household_demographics/*.parquet') AS household_demographics, READ_PARQUET('/home/cc/tpcds_cluster_base/time_dim/*.parquet') AS time_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/web_page/*.parquet') AS web_page
    WHERE
      ws_sold_time_sk = time_dim.t_time_sk
      AND ws_ship_hdemo_sk = household_demographics.hd_demo_sk
      AND ws_web_page_sk = web_page.wp_web_page_sk
      AND time_dim.t_hour BETWEEN 8 AND 8 + 1
      AND household_demographics.hd_dep_count = 6
      AND web_page.wp_char_count BETWEEN 5000 AND 5200
) AS at1, (
    SELECT
      COUNT(*) AS pmc
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS web_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/household_demographics/*.parquet') AS household_demographics, READ_PARQUET('/home/cc/tpcds_cluster_base/time_dim/*.parquet') AS time_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/web_page/*.parquet') AS web_page
    WHERE
      ws_sold_time_sk = time_dim.t_time_sk
      AND ws_ship_hdemo_sk = household_demographics.hd_demo_sk
      AND ws_web_page_sk = web_page.wp_web_page_sk
      AND time_dim.t_hour BETWEEN 19 AND 19 + 1
      AND household_demographics.hd_dep_count = 6
      AND web_page.wp_char_count BETWEEN 5000 AND 5200
) AS pt
ORDER BY
  am_pm_ratio
LIMIT 100