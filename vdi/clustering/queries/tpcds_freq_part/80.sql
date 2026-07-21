WITH ssr AS (
    SELECT
      s_store_id AS store_id,
      SUM(ss_ext_sales_price) AS sales,
      SUM(COALESCE(sr_return_amt, 0)) AS returns_,
      SUM(ss_net_profit - COALESCE(sr_net_loss, 0)) AS profit
    FROM READ_PARQUET('/home/cc/tpcds_cluster_freq/store_sales/*.parquet') AS store_sales
    LEFT OUTER JOIN READ_PARQUET('/home/cc/tpcds_cluster_base/store_returns/*.parquet') AS store_returns
      ON (
        ss_item_sk = sr_item_sk AND ss_ticket_number = sr_ticket_number
      ), READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/store/*.parquet') AS store, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item, READ_PARQUET('/home/cc/tpcds_cluster_base/promotion/*.parquet') AS promotion
    WHERE
      ss_sold_date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-22' AS DATE)
      AND ss_store_sk = s_store_sk
      AND ss_item_sk = i_item_sk
      AND i_current_price > 50
      AND ss_promo_sk = p_promo_sk
      AND p_channel_tv = 'N'
    GROUP BY
      s_store_id
), csr AS (
    SELECT
      cp_catalog_page_id AS catalog_page_id,
      SUM(cs_ext_sales_price) AS sales,
      SUM(COALESCE(cr_return_amount, 0)) AS returns_,
      SUM(cs_net_profit - COALESCE(cr_net_loss, 0)) AS profit
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS catalog_sales
    LEFT OUTER JOIN READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_returns/*.parquet') AS catalog_returns
      ON (
        cs_item_sk = cr_item_sk AND cs_order_number = cr_order_number
      ), READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_page/*.parquet') AS catalog_page, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item, READ_PARQUET('/home/cc/tpcds_cluster_base/promotion/*.parquet') AS promotion
    WHERE
      cs_sold_date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-22' AS DATE)
      AND cs_catalog_page_sk = cp_catalog_page_sk
      AND cs_item_sk = i_item_sk
      AND i_current_price > 50
      AND cs_promo_sk = p_promo_sk
      AND p_channel_tv = 'N'
    GROUP BY
      cp_catalog_page_id
), wsr AS (
    SELECT
      web_site_id,
      SUM(ws_ext_sales_price) AS sales,
      SUM(COALESCE(wr_return_amt, 0)) AS returns_,
      SUM(ws_net_profit - COALESCE(wr_net_loss, 0)) AS profit
    FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS web_sales
    LEFT OUTER JOIN READ_PARQUET('/home/cc/tpcds_cluster_base/web_returns/*.parquet') AS web_returns
      ON (
        ws_item_sk = wr_item_sk AND ws_order_number = wr_order_number
      ), READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/web_site/*.parquet') AS web_site, READ_PARQUET('/home/cc/tpcds_cluster_base/item/*.parquet') AS item, READ_PARQUET('/home/cc/tpcds_cluster_base/promotion/*.parquet') AS promotion
    WHERE
      ws_sold_date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-22' AS DATE)
      AND ws_web_site_sk = web_site_sk
      AND ws_item_sk = i_item_sk
      AND i_current_price > 50
      AND ws_promo_sk = p_promo_sk
      AND p_channel_tv = 'N'
    GROUP BY
      web_site_id
), results AS (
    SELECT
      channel,
      id,
      SUM(sales) AS sales,
      SUM(returns_) AS returns_,
      SUM(profit) AS profit
    FROM (
        SELECT
          'store channel' AS channel,
          'store' || store_id AS id,
          sales,
          returns_,
          profit
        FROM ssr
        UNION ALL
        SELECT
          'catalog channel' AS channel,
          'catalog_page' || catalog_page_id AS id,
          sales,
          returns_,
          profit
        FROM csr
        UNION ALL
        SELECT
          'web channel' AS channel,
          'web_site' || web_site_id AS id,
          sales,
          returns_,
          profit
        FROM wsr
    ) AS x
    GROUP BY
      channel,
      id
)
SELECT
  channel,
  id,
  sales,
  returns_,
  profit
FROM (
    SELECT
      channel,
      id,
      sales,
      returns_,
      profit
    FROM results
    UNION
    SELECT
      channel,
      NULL AS id,
      SUM(sales) AS sales,
      SUM(returns_) AS returns_,
      SUM(profit) AS profit
    FROM results
    GROUP BY
      channel
    UNION
    SELECT
      NULL AS channel,
      NULL AS id,
      SUM(sales) AS sales,
      SUM(returns_) AS returns_,
      SUM(profit) AS profit
    FROM results
) AS foo
ORDER BY
  channel NULLS FIRST,
  id NULLS FIRST
LIMIT 100