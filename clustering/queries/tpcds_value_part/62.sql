SELECT
  w_substr,
  sm_type,
  web_name,
  SUM(CASE WHEN (
    ws_ship_date_sk - ws_sold_date_sk <= 30
  ) THEN 1 ELSE 0 END) AS days_30,
  SUM(
    CASE
      WHEN (
        ws_ship_date_sk - ws_sold_date_sk > 30
      )
      AND (
        ws_ship_date_sk - ws_sold_date_sk <= 60
      )
      THEN 1
      ELSE 0
    END
  ) AS days_31_60,
  SUM(
    CASE
      WHEN (
        ws_ship_date_sk - ws_sold_date_sk > 60
      )
      AND (
        ws_ship_date_sk - ws_sold_date_sk <= 90
      )
      THEN 1
      ELSE 0
    END
  ) AS days_61_90,
  SUM(
    CASE
      WHEN (
        ws_ship_date_sk - ws_sold_date_sk > 90
      )
      AND (
        ws_ship_date_sk - ws_sold_date_sk <= 120
      )
      THEN 1
      ELSE 0
    END
  ) AS days_90_120,
  SUM(CASE WHEN (
    ws_ship_date_sk - ws_sold_date_sk > 120
  ) THEN 1 ELSE 0 END) AS days_over_120
FROM READ_PARQUET('/home/cc/tpcds_cluster_value/web_sales/*.parquet') AS web_sales, (
    SELECT
      SUBSTRING(w_warehouse_name, 1, 20) AS w_substr,
      *
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/warehouse/*.parquet') AS warehouse
) AS sq1, READ_PARQUET('/home/cc/tpcds_cluster_base/ship_mode/*.parquet') AS ship_mode, READ_PARQUET('/home/cc/tpcds_cluster_base/web_site/*.parquet') AS web_site, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim
WHERE
  d_month_seq BETWEEN 1200 AND 1200 + 11
  AND ws_ship_date_sk = d_date_sk
  AND ws_warehouse_sk = w_warehouse_sk
  AND ws_ship_mode_sk = sm_ship_mode_sk
  AND ws_web_site_sk = web_site_sk
GROUP BY
  w_substr,
  sm_type,
  web_name
ORDER BY
  1 NULLS FIRST,
  2 NULLS FIRST,
  3 NULLS FIRST
LIMIT 100