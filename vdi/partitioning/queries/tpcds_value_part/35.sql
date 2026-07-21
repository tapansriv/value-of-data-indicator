SELECT
  ca_state,
  cd_gender,
  cd_marital_status,
  cd_dep_count,
  COUNT(*) AS cnt1,
  MIN(cd_dep_count) AS min1,
  MAX(cd_dep_count) AS max1,
  AVG(cd_dep_count) AS avg1,
  cd_dep_employed_count,
  COUNT(*) AS cnt2,
  MIN(cd_dep_employed_count) AS min2,
  MAX(cd_dep_employed_count) AS max2,
  AVG(cd_dep_employed_count) AS avg2,
  cd_dep_college_count,
  COUNT(*) AS cnt3,
  MIN(cd_dep_college_count),
  MAX(cd_dep_college_count),
  AVG(cd_dep_college_count)
FROM READ_PARQUET('customer.parquet') AS c, READ_PARQUET('customer_address.parquet') AS ca, READ_PARQUET('customer_demographics.parquet') AS customer_demographics
WHERE
  c.c_current_addr_sk = ca.ca_address_sk
  AND cd_demo_sk = c.c_current_cdemo_sk
  AND EXISTS(
      SELECT
        *
      FROM READ_PARQUET('store_sales.parquet') AS store_sales, READ_PARQUET('date_dim.parquet') AS date_dim
      WHERE
        c.c_customer_sk = ss_customer_sk
        AND ss_sold_date_sk = d_date_sk
        AND d_year = 2002
        AND d_qoy < 4
  )
  AND (
    EXISTS(
        SELECT
          *
        FROM READ_PARQUET('/home/cc/tpcds_partitioned_value/web_sales/**/*.parquet', hive_partitioning = 1) AS web_sales, READ_PARQUET('date_dim.parquet') AS date_dim
        WHERE
          c.c_customer_sk = ws_bill_customer_sk
          AND ws_sold_date_sk = d_date_sk
          AND d_year = 2002
          AND d_qoy < 4
    )
    OR EXISTS(
        SELECT
          *
        FROM READ_PARQUET('catalog_sales.parquet') AS catalog_sales, READ_PARQUET('date_dim.parquet') AS date_dim
        WHERE
          c.c_customer_sk = cs_ship_customer_sk
          AND cs_sold_date_sk = d_date_sk
          AND d_year = 2002
          AND d_qoy < 4
    )
  )
GROUP BY
  ca_state,
  cd_gender,
  cd_marital_status,
  cd_dep_count,
  cd_dep_employed_count,
  cd_dep_college_count
ORDER BY
  ca_state NULLS FIRST,
  cd_gender NULLS FIRST,
  cd_marital_status NULLS FIRST,
  cd_dep_count NULLS FIRST,
  cd_dep_employed_count NULLS FIRST,
  cd_dep_college_count NULLS FIRST
LIMIT 100