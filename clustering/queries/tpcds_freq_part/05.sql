WITH ssr AS (
    SELECT
      s_store_id,
      SUM(sales_price) AS sales,
      SUM(profit) AS profit,
      SUM(return_amt) AS returns_,
      SUM(net_loss) AS profit_loss
    FROM (
        SELECT
          ss_store_sk AS store_sk,
          ss_sold_date_sk AS date_sk,
          ss_ext_sales_price AS sales_price,
          ss_net_profit AS profit,
          CAST(0 AS DECIMAL(7, 2)) AS return_amt,
          CAST(0 AS DECIMAL(7, 2)) AS net_loss
        FROM READ_PARQUET('/home/cc/tpcds_cluster_freq/store_sales/*.parquet') AS store_sales
        UNION ALL
        SELECT
          sr_store_sk AS store_sk,
          sr_returned_date_sk AS date_sk,
          CAST(0 AS DECIMAL(7, 2)) AS sales_price,
          CAST(0 AS DECIMAL(7, 2)) AS profit,
          sr_return_amt AS return_amt,
          sr_net_loss AS net_loss
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/store_returns/*.parquet') AS store_returns
    ) AS salesreturns, READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/store/*.parquet') AS store
    WHERE
      date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-06' AS DATE)
      AND store_sk = s_store_sk
    GROUP BY
      s_store_id
), csr AS (
    SELECT
      cp_catalog_page_id,
      SUM(sales_price) AS sales,
      SUM(profit) AS profit,
      SUM(return_amt) AS returns_,
      SUM(net_loss) AS profit_loss
    FROM (
        SELECT
          cs_catalog_page_sk AS page_sk,
          cs_sold_date_sk AS date_sk,
          cs_ext_sales_price AS sales_price,
          cs_net_profit AS profit,
          CAST(0 AS DECIMAL(7, 2)) AS return_amt,
          CAST(0 AS DECIMAL(7, 2)) AS net_loss
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_sales/*.parquet') AS catalog_sales
        UNION ALL
        SELECT
          cr_catalog_page_sk AS page_sk,
          cr_returned_date_sk AS date_sk,
          CAST(0 AS DECIMAL(7, 2)) AS sales_price,
          CAST(0 AS DECIMAL(7, 2)) AS profit,
          cr_return_amount AS return_amt,
          cr_net_loss AS net_loss
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_returns/*.parquet') AS catalog_returns
    ) AS salesreturns, READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/catalog_page/*.parquet') AS catalog_page
    WHERE
      date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-06' AS DATE)
      AND page_sk = cp_catalog_page_sk
    GROUP BY
      cp_catalog_page_id
), wsr AS (
    SELECT
      web_site_id,
      SUM(sales_price) AS sales,
      SUM(profit) AS profit,
      SUM(return_amt) AS returns_,
      SUM(net_loss) AS profit_loss
    FROM (
        SELECT
          ws_web_site_sk AS wsr_web_site_sk,
          ws_sold_date_sk AS date_sk,
          ws_ext_sales_price AS sales_price,
          ws_net_profit AS profit,
          CAST(0 AS DECIMAL(7, 2)) AS return_amt,
          CAST(0 AS DECIMAL(7, 2)) AS net_loss
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS web_sales
        UNION ALL
        SELECT
          ws_web_site_sk AS wsr_web_site_sk,
          wr_returned_date_sk AS date_sk,
          CAST(0 AS DECIMAL(7, 2)) AS sales_price,
          CAST(0 AS DECIMAL(7, 2)) AS profit,
          wr_return_amt AS return_amt,
          wr_net_loss AS net_loss
        FROM READ_PARQUET('/home/cc/tpcds_cluster_base/web_returns/*.parquet') AS web_returns
        LEFT OUTER JOIN READ_PARQUET('/home/cc/tpcds_cluster_base/web_sales/*.parquet') AS web_sales
          ON (
            wr_item_sk = ws_item_sk AND wr_order_number = ws_order_number
          )
    ) AS salesreturns, READ_PARQUET('/home/cc/tpcds_cluster_freq/date_dim/*.parquet') AS date_dim, READ_PARQUET('/home/cc/tpcds_cluster_base/web_site/*.parquet') AS web_site
    WHERE
      date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-06' AS DATE)
      AND wsr_web_site_sk = web_site_sk
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
          'store' || s_store_id AS id,
          sales,
          returns_,
          (
            profit - profit_loss
          ) AS profit
        FROM ssr
        UNION ALL
        SELECT
          'catalog channel' AS channel,
          'catalog_page' || cp_catalog_page_id AS id,
          sales,
          returns_,
          (
            profit - profit_loss
          ) AS profit
        FROM csr
        UNION ALL
        SELECT
          'web channel' AS channel,
          'web_site' || web_site_id AS id,
          sales,
          returns_,
          (
            profit - profit_loss
          ) AS profit
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
      SUM(sales),
      SUM(returns_),
      SUM(profit)
    FROM results
    GROUP BY
      channel
    UNION
    SELECT
      NULL AS channel,
      NULL AS id,
      SUM(sales),
      SUM(returns_),
      SUM(profit)
    FROM results
) AS foo
ORDER BY
  channel NULLS FIRST,
  id NULLS FIRST
LIMIT 100