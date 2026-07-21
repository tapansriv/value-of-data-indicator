WITH results AS (
    SELECT
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year,
      d_qoy,
      d_moy,
      s_store_id,
      SUM(COALESCE(ss_sales_price * ss_quantity, 0)) AS sumsales
    FROM READ_PARQUET('store_sales.parquet') AS store_sales, READ_PARQUET('date_dim.parquet') AS date_dim, READ_PARQUET('store.parquet') AS store, READ_PARQUET('/home/cc/tpcds_partitioned_value/item/**/*.parquet', hive_partitioning = 1) AS item
    WHERE
      ss_sold_date_sk = d_date_sk
      AND ss_item_sk = i_item_sk
      AND ss_store_sk = s_store_sk
      AND d_month_seq BETWEEN 1200 AND 1200 + 11
    GROUP BY
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year,
      d_qoy,
      d_moy,
      s_store_id
), results_rollup AS (
    SELECT
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year,
      d_qoy,
      d_moy,
      s_store_id,
      sumsales
    FROM results
    UNION ALL
    SELECT
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year,
      d_qoy,
      d_moy,
      NULL AS s_store_id,
      SUM(sumsales) AS sumsales
    FROM results
    GROUP BY
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year,
      d_qoy,
      d_moy
    UNION ALL
    SELECT
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year,
      d_qoy,
      NULL AS d_moy,
      NULL AS s_store_id,
      SUM(sumsales) AS sumsales
    FROM results
    GROUP BY
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year,
      d_qoy
    UNION ALL
    SELECT
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year,
      NULL AS d_qoy,
      NULL AS d_moy,
      NULL AS s_store_id,
      SUM(sumsales) AS sumsales
    FROM results
    GROUP BY
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year
    UNION ALL
    SELECT
      i_category,
      i_class,
      i_brand,
      i_product_name,
      NULL AS d_year,
      NULL AS d_qoy,
      NULL AS d_moy,
      NULL AS s_store_id,
      SUM(sumsales) AS sumsales
    FROM results
    GROUP BY
      i_category,
      i_class,
      i_brand,
      i_product_name
    UNION ALL
    SELECT
      i_category,
      i_class,
      i_brand,
      NULL AS i_product_name,
      NULL AS d_year,
      NULL AS d_qoy,
      NULL AS d_moy,
      NULL AS s_store_id,
      SUM(sumsales) AS sumsales
    FROM results
    GROUP BY
      i_category,
      i_class,
      i_brand
    UNION ALL
    SELECT
      i_category,
      i_class,
      NULL AS i_brand,
      NULL AS i_product_name,
      NULL AS d_year,
      NULL AS d_qoy,
      NULL AS d_moy,
      NULL AS s_store_id,
      SUM(sumsales) AS sumsales
    FROM results
    GROUP BY
      i_category,
      i_class
    UNION ALL
    SELECT
      i_category,
      NULL AS i_class,
      NULL AS i_brand,
      NULL AS i_product_name,
      NULL AS d_year,
      NULL AS d_qoy,
      NULL AS d_moy,
      NULL AS s_store_id,
      SUM(sumsales) AS sumsales
    FROM results
    GROUP BY
      i_category
    UNION ALL
    SELECT
      NULL AS i_category,
      NULL AS i_class,
      NULL AS i_brand,
      NULL AS i_product_name,
      NULL AS d_year,
      NULL AS d_qoy,
      NULL AS d_moy,
      NULL AS s_store_id,
      SUM(sumsales) AS sumsales
    FROM results
)
SELECT
  *
FROM (
    SELECT
      i_category,
      i_class,
      i_brand,
      i_product_name,
      d_year,
      d_qoy,
      d_moy,
      s_store_id,
      sumsales,
      RANK() OVER (PARTITION BY i_category ORDER BY sumsales DESC) AS rk
    FROM results_rollup
) AS dw2
WHERE
  rk <= 100
ORDER BY
  i_category,
  i_class,
  i_brand,
  i_product_name,
  d_year,
  d_qoy,
  d_moy,
  s_store_id,
  sumsales,
  rk
LIMIT 100