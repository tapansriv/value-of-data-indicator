WITH cross_items AS (
    SELECT
      i_item_sk AS ss_item_sk
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item, (
        SELECT
          iss.i_brand_id AS brand_id,
          iss.i_class_id AS class_id,
          iss.i_category_id AS category_id
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS iss, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS d1
        WHERE
          ss_item_sk = iss.i_item_sk
          AND ss_sold_date_sk = d1.d_date_sk
          AND d1.d_year BETWEEN 1999 AND 1999 + 2
        INTERSECT
        SELECT
          ics.i_brand_id,
          ics.i_class_id,
          ics.i_category_id
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS catalog_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS ics, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS d2
        WHERE
          cs_item_sk = ics.i_item_sk
          AND cs_sold_date_sk = d2.d_date_sk
          AND d2.d_year BETWEEN 1999 AND 1999 + 2
        INTERSECT
        SELECT
          iws.i_brand_id,
          iws.i_class_id,
          iws.i_category_id
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS web_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS iws, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS d3
        WHERE
          ws_item_sk = iws.i_item_sk
          AND ws_sold_date_sk = d3.d_date_sk
          AND d3.d_year BETWEEN 1999 AND 1999 + 2
    ) AS x
    WHERE
      i_brand_id = brand_id AND i_class_id = class_id AND i_category_id = category_id
), avg_sales AS (
    SELECT
      AVG(quantity * list_price) AS average_sales
    FROM (
        SELECT
          ss_quantity AS quantity,
          ss_list_price AS list_price
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim
        WHERE
          ss_sold_date_sk = d_date_sk AND d_year BETWEEN 1999 AND 2001
        UNION ALL
        SELECT
          cs_quantity AS quantity,
          cs_list_price AS list_price
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS catalog_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim
        WHERE
          cs_sold_date_sk = d_date_sk AND d_year BETWEEN 1999 AND 1999 + 2
        UNION ALL
        SELECT
          ws_quantity AS quantity,
          ws_list_price AS list_price
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS web_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim
        WHERE
          ws_sold_date_sk = d_date_sk AND d_year BETWEEN 1999 AND 1999 + 2
    ) AS x
), results AS (
    SELECT
      channel,
      i_brand_id,
      i_class_id,
      i_category_id,
      SUM(sales) AS sum_sales,
      SUM(number_sales) AS number_sales
    FROM (
        SELECT
          'store' AS channel,
          i_brand_id,
          i_class_id,
          i_category_id,
          SUM(ss_quantity * ss_list_price) AS sales,
          COUNT(*) AS number_sales
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/store_sales/*.parquet') AS store_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim
        WHERE
          ss_item_sk IN (
              SELECT
                ss_item_sk
              FROM cross_items
          )
          AND ss_item_sk = i_item_sk
          AND ss_sold_date_sk = d_date_sk
          AND d_year = 1999 + 2
          AND d_moy = 11
        GROUP BY
          i_brand_id,
          i_class_id,
          i_category_id
        HAVING
          SUM(ss_quantity * ss_list_price) > (
              SELECT
                average_sales
              FROM avg_sales
          )
        UNION ALL
        SELECT
          'catalog' AS channel,
          i_brand_id,
          i_class_id,
          i_category_id,
          SUM(cs_quantity * cs_list_price) AS sales,
          COUNT(*) AS number_sales
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS catalog_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim
        WHERE
          cs_item_sk IN (
              SELECT
                ss_item_sk
              FROM cross_items
          )
          AND cs_item_sk = i_item_sk
          AND cs_sold_date_sk = d_date_sk
          AND d_year = 1999 + 2
          AND d_moy = 11
        GROUP BY
          i_brand_id,
          i_class_id,
          i_category_id
        HAVING
          SUM(cs_quantity * cs_list_price) > (
              SELECT
                average_sales
              FROM avg_sales
          )
        UNION ALL
        SELECT
          'web' AS channel,
          i_brand_id,
          i_class_id,
          i_category_id,
          SUM(ws_quantity * ws_list_price) AS sales,
          COUNT(*) AS number_sales
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS web_sales, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item, READ_PARQUET('/home/cc/tpcds_cluster_base/date_dim/*.parquet') AS date_dim
        WHERE
          ws_item_sk IN (
              SELECT
                ss_item_sk
              FROM cross_items
          )
          AND ws_item_sk = i_item_sk
          AND ws_sold_date_sk = d_date_sk
          AND d_year = 1999 + 2
          AND d_moy = 11
        GROUP BY
          i_brand_id,
          i_class_id,
          i_category_id
        HAVING
          SUM(ws_quantity * ws_list_price) > (
              SELECT
                average_sales
              FROM avg_sales
          )
    ) AS y
    GROUP BY
      channel,
      i_brand_id,
      i_class_id,
      i_category_id
)
SELECT
  channel,
  i_brand_id,
  i_class_id,
  i_category_id,
  sum_sales,
  number_sales
FROM (
    SELECT
      channel,
      i_brand_id,
      i_class_id,
      i_category_id,
      sum_sales,
      number_sales
    FROM results
    UNION
    SELECT
      channel,
      i_brand_id,
      i_class_id,
      NULL AS i_category_id,
      SUM(sum_sales),
      SUM(number_sales)
    FROM results
    GROUP BY
      channel,
      i_brand_id,
      i_class_id
    UNION
    SELECT
      channel,
      i_brand_id,
      NULL AS i_class_id,
      NULL AS i_category_id,
      SUM(sum_sales),
      SUM(number_sales)
    FROM results
    GROUP BY
      channel,
      i_brand_id
    UNION
    SELECT
      channel,
      NULL AS i_brand_id,
      NULL AS i_class_id,
      NULL AS i_category_id,
      SUM(sum_sales),
      SUM(number_sales)
    FROM results
    GROUP BY
      channel
    UNION
    SELECT
      NULL AS channel,
      NULL AS i_brand_id,
      NULL AS i_class_id,
      NULL AS i_category_id,
      SUM(sum_sales),
      SUM(number_sales)
    FROM results
) AS z
ORDER BY
  channel NULLS FIRST,
  i_brand_id NULLS FIRST,
  i_class_id NULLS FIRST,
  i_category_id NULLS FIRST
LIMIT 100