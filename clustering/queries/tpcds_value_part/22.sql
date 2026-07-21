WITH results AS (
    SELECT
      i_product_name,
      i_brand,
      i_class,
      i_category,
      inv_quantity_on_hand AS qoh
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/inventory/*.parquet') AS inventory, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_value/item/*.parquet') AS item, READ_PARQUET('/home/cc/tpcds_cluster_base/warehouse/*.parquet') AS warehouse
    WHERE
      inv_date_sk = d_date_sk
      AND inv_item_sk = i_item_sk
      AND inv_warehouse_sk = w_warehouse_sk
      AND d_month_seq BETWEEN 1200 AND 1200 + 11
), results_rollup AS (
    SELECT
      i_product_name,
      i_brand,
      i_class,
      i_category,
      AVG(qoh) AS qoh
    FROM results
    GROUP BY
      i_product_name,
      i_brand,
      i_class,
      i_category
    UNION ALL
    SELECT
      i_product_name,
      i_brand,
      i_class,
      NULL AS i_category,
      AVG(qoh) AS qoh
    FROM results
    GROUP BY
      i_product_name,
      i_brand,
      i_class
    UNION ALL
    SELECT
      i_product_name,
      i_brand,
      NULL AS i_class,
      NULL AS i_category,
      AVG(qoh) AS qoh
    FROM results
    GROUP BY
      i_product_name,
      i_brand
    UNION ALL
    SELECT
      i_product_name,
      NULL AS i_brand,
      NULL AS i_class,
      NULL AS i_category,
      AVG(qoh) AS qoh
    FROM results
    GROUP BY
      i_product_name
    UNION ALL
    SELECT
      NULL AS i_product_name,
      NULL AS i_brand,
      NULL AS i_class,
      NULL AS i_category,
      AVG(qoh) AS qoh
    FROM results
)
SELECT
  i_product_name,
  i_brand,
  i_class,
  i_category,
  qoh
FROM results_rollup
ORDER BY
  qoh NULLS FIRST,
  i_product_name NULLS FIRST,
  i_brand NULLS FIRST,
  i_class NULLS FIRST,
  i_category NULLS FIRST
LIMIT 100