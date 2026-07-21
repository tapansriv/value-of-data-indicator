SELECT
  COUNT(DISTINCT ws_order_number) AS "order count",
  SUM(ws_ext_ship_cost) AS "total shipping cost",
  SUM(ws_net_profit) AS "total net profit"
FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS ws1, READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_address/*.parquet') AS customer_address, READ_PARQUET('/home/cc/tpcds_cluster_base/web_site/*.parquet') AS web_site
WHERE
  d_date BETWEEN '1999-02-01' AND CAST('1999-04-02' AS DATE)
  AND ws1.ws_ship_date_sk = d_date_sk
  AND ws1.ws_ship_addr_sk = ca_address_sk
  AND ca_state = 'IL'
  AND ws1.ws_web_site_sk = web_site_sk
  AND web_company_name = 'pri'
  AND EXISTS(
      SELECT
        *
      FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS ws2
      WHERE
        ws1.ws_order_number = ws2.ws_order_number
        AND ws1.ws_warehouse_sk <> ws2.ws_warehouse_sk
  )
  AND NOT EXISTS(
      SELECT
        *
      FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_returns/*.parquet') AS wr1
      WHERE
        ws1.ws_order_number = wr1.wr_order_number
  )
ORDER BY
  COUNT(DISTINCT ws_order_number)
LIMIT 100