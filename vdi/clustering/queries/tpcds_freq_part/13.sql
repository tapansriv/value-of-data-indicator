SELECT
  AVG(ss_quantity) AS avg1,
  AVG(ss_ext_sales_price) AS avg2,
  AVG(ss_ext_wholesale_cost) AS avg3,
  SUM(ss_ext_wholesale_cost)
FROM READ_PARQUET('/home/cc/tpcds_cluster_freq/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/store/*.parquet') AS store, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_demographics/*.parquet') AS customer_demographics, READ_PARQUET('/home/cc/tpcds_cluster_base/household_demographics/*.parquet') AS household_demographics, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_address/*.parquet') AS customer_address, READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim
WHERE
  s_store_sk = ss_store_sk
  AND ss_sold_date_sk = d_date_sk
  AND d_year = 2001
  AND (
    (
      ss_hdemo_sk = hd_demo_sk
      AND cd_demo_sk = ss_cdemo_sk
      AND cd_marital_status = 'M'
      AND cd_education_status = 'Advanced Degree'
      AND ss_sales_price BETWEEN 100.00 AND 150.00
      AND hd_dep_count = 3
    )
    OR (
      ss_hdemo_sk = hd_demo_sk
      AND cd_demo_sk = ss_cdemo_sk
      AND cd_marital_status = 'S'
      AND cd_education_status = 'College'
      AND ss_sales_price BETWEEN 50.00 AND 100.00
      AND hd_dep_count = 1
    )
    OR (
      ss_hdemo_sk = hd_demo_sk
      AND cd_demo_sk = ss_cdemo_sk
      AND cd_marital_status = 'W'
      AND cd_education_status = '2 yr Degree'
      AND ss_sales_price BETWEEN 150.00 AND 200.00
      AND hd_dep_count = 1
    )
  )
  AND (
    (
      ss_addr_sk = ca_address_sk
      AND ca_country = 'United States'
      AND ca_state IN ('TX', 'OH', 'TX')
      AND ss_net_profit BETWEEN 100 AND 200
    )
    OR (
      ss_addr_sk = ca_address_sk
      AND ca_country = 'United States'
      AND ca_state IN ('OR', 'NM', 'KY')
      AND ss_net_profit BETWEEN 150 AND 300
    )
    OR (
      ss_addr_sk = ca_address_sk
      AND ca_country = 'United States'
      AND ca_state IN ('VA', 'TX', 'MS')
      AND ss_net_profit BETWEEN 50 AND 250
    )
  )