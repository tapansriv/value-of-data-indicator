WITH ss AS (
    SELECT
      i_item_id,
      SUM(ss_ext_sales_price) AS total_sales
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_address/*.parquet') AS customer_address, READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item
    WHERE
      i_item_id IN (
          SELECT
            i_item_id
          FROM READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item
          WHERE
            i_category = 'Music'
      )
      AND ss_item_sk = i_item_sk
      AND ss_sold_date_sk = d_date_sk
      AND d_year = 1998
      AND d_moy = 9
      AND ss_addr_sk = ca_address_sk
      AND ca_gmt_offset = -5
    GROUP BY
      i_item_id
), cs AS (
    SELECT
      i_item_id,
      SUM(cs_ext_sales_price) AS total_sales
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS catalog_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_address/*.parquet') AS customer_address, READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item
    WHERE
      i_item_id IN (
          SELECT
            i_item_id
          FROM READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item
          WHERE
            i_category = 'Music'
      )
      AND cs_item_sk = i_item_sk
      AND cs_sold_date_sk = d_date_sk
      AND d_year = 1998
      AND d_moy = 9
      AND cs_bill_addr_sk = ca_address_sk
      AND ca_gmt_offset = -5
    GROUP BY
      i_item_id
), ws AS (
    SELECT
      i_item_id,
      SUM(ws_ext_sales_price) AS total_sales
    FROM READ_PARQUET('/home/cc/tpcds_cluster_value/web_sales/*.parquet') AS web_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/customer_address/*.parquet') AS customer_address, READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item
    WHERE
      i_item_id IN (
          SELECT
            i_item_id
          FROM READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item
          WHERE
            i_category = 'Music'
      )
      AND ws_item_sk = i_item_sk
      AND ws_sold_date_sk = d_date_sk
      AND d_year = 1998
      AND d_moy = 9
      AND ws_bill_addr_sk = ca_address_sk
      AND ca_gmt_offset = -5
    GROUP BY
      i_item_id
)
SELECT
  i_item_id,
  SUM(total_sales) AS total_sales1
FROM (
    SELECT
      *
    FROM ss
    UNION ALL
    SELECT
      *
    FROM cs
    UNION ALL
    SELECT
      *
    FROM ws
) AS tmp1
GROUP BY
  i_item_id
ORDER BY
  i_item_id,
  total_sales1
LIMIT 100