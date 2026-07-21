SELECT
  COUNT(DISTINCT cs_order_number) AS "order count",
  SUM(cs_ext_ship_cost) AS "total shipping cost",
  SUM(cs_net_profit) AS "total net profit"
FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS cs1, READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_address/*.parquet') AS customer_address, READ_PARQUET('/home/cc/tpcds_cluster_base/call_center/*.parquet') AS call_center
WHERE
  d_date BETWEEN '2002-02-01' AND CAST('2002-04-02' AS DATE)
  AND cs1.cs_ship_date_sk = d_date_sk
  AND cs1.cs_ship_addr_sk = ca_address_sk
  AND ca_state = 'GA'
  AND cs1.cs_call_center_sk = cc_call_center_sk
  AND cc_county = 'Williamson County'
  AND EXISTS(
      SELECT
        *
      FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS cs2
      WHERE
        cs1.cs_order_number = cs2.cs_order_number
        AND cs1.cs_warehouse_sk <> cs2.cs_warehouse_sk
  )
  AND NOT EXISTS(
      SELECT
        *
      FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_returns/*.parquet') AS cr1
      WHERE
        cs1.cs_order_number = cr1.cr_order_number
  )
ORDER BY
  COUNT(DISTINCT cs_order_number)
LIMIT 100