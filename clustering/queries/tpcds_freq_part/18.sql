WITH results AS (
    SELECT
      i_item_id,
      ca_country,
      ca_state,
      ca_county,
      CAST(cs_quantity AS DECIMAL(12, 2)) AS agg1,
      CAST(cs_list_price AS DECIMAL(12, 2)) AS agg2,
      CAST(cs_coupon_amt AS DECIMAL(12, 2)) AS agg3,
      CAST(cs_sales_price AS DECIMAL(12, 2)) AS agg4,
      CAST(cs_net_profit AS DECIMAL(12, 2)) AS agg5,
      CAST(c_birth_year AS DECIMAL(12, 2)) AS agg6,
      CAST(cd1.cd_dep_count AS DECIMAL(12, 2)) AS agg7
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS catalog_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_demographics/*.parquet') AS cd1, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_demographics/*.parquet') AS cd2, READ_PARQUET('/home/cc/tpcds_cluster_base/customer/*.parquet') AS customer, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_address/*.parquet') AS customer_address, READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item
    WHERE
      cs_sold_date_sk = d_date_sk
      AND cs_item_sk = i_item_sk
      AND cs_bill_cdemo_sk = cd1.cd_demo_sk
      AND cs_bill_customer_sk = c_customer_sk
      AND cd1.cd_gender = 'F'
      AND cd1.cd_education_status = 'Unknown'
      AND c_current_cdemo_sk = cd2.cd_demo_sk
      AND c_current_addr_sk = ca_address_sk
      AND c_birth_month IN (1, 6, 8, 9, 12, 2)
      AND d_year = 1998
      AND ca_state IN ('MS', 'IN', 'ND', 'OK', 'NM', 'VA', 'MS')
)
SELECT
  i_item_id,
  ca_country,
  ca_state,
  ca_county,
  agg1,
  agg2,
  agg3,
  agg4,
  agg5,
  agg6,
  agg7
FROM (
    SELECT
      i_item_id,
      ca_country,
      ca_state,
      ca_county,
      AVG(agg1) AS agg1,
      AVG(agg2) AS agg2,
      AVG(agg3) AS agg3,
      AVG(agg4) AS agg4,
      AVG(agg5) AS agg5,
      AVG(agg6) AS agg6,
      AVG(agg7) AS agg7
    FROM results
    GROUP BY
      i_item_id,
      ca_country,
      ca_state,
      ca_county
    UNION ALL
    SELECT
      i_item_id,
      ca_country,
      ca_state,
      NULL AS county,
      AVG(agg1) AS agg1,
      AVG(agg2) AS agg2,
      AVG(agg3) AS agg3,
      AVG(agg4) AS agg4,
      AVG(agg5) AS agg5,
      AVG(agg6) AS agg6,
      AVG(agg7) AS agg7
    FROM results
    GROUP BY
      i_item_id,
      ca_country,
      ca_state
    UNION ALL
    SELECT
      i_item_id,
      ca_country,
      NULL AS ca_state,
      NULL AS county,
      AVG(agg1) AS agg1,
      AVG(agg2) AS agg2,
      AVG(agg3) AS agg3,
      AVG(agg4) AS agg4,
      AVG(agg5) AS agg5,
      AVG(agg6) AS agg6,
      AVG(agg7) AS agg7
    FROM results
    GROUP BY
      i_item_id,
      ca_country
    UNION ALL
    SELECT
      i_item_id,
      NULL AS ca_country,
      NULL AS ca_state,
      NULL AS county,
      AVG(agg1) AS agg1,
      AVG(agg2) AS agg2,
      AVG(agg3) AS agg3,
      AVG(agg4) AS agg4,
      AVG(agg5) AS agg5,
      AVG(agg6) AS agg6,
      AVG(agg7) AS agg7
    FROM results
    GROUP BY
      i_item_id
    UNION ALL
    SELECT
      NULL AS i_item_id,
      NULL AS ca_country,
      NULL AS ca_state,
      NULL AS county,
      AVG(agg1) AS agg1,
      AVG(agg2) AS agg2,
      AVG(agg3) AS agg3,
      AVG(agg4) AS agg4,
      AVG(agg5) AS agg5,
      AVG(agg6) AS agg6,
      AVG(agg7) AS agg7
    FROM results
) AS foo
ORDER BY
  ca_country NULLS FIRST,
  ca_state NULLS FIRST,
  ca_county NULLS FIRST,
  i_item_id NULLS FIRST
LIMIT 100