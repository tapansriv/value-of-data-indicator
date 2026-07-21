WITH ss AS (
    SELECT
      s_store_sk,
      SUM(ss_ext_sales_price) AS sales,
      SUM(ss_net_profit) AS profit
    FROM READ_PARQUET('store_sales.parquet') AS store_sales, READ_PARQUET('date_dim.parquet') AS date_dim, READ_PARQUET('store.parquet') AS store
    WHERE
      ss_sold_date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-22' AS DATE)
      AND ss_store_sk = s_store_sk
    GROUP BY
      s_store_sk
), sr AS (
    SELECT
      s_store_sk,
      SUM(sr_return_amt) AS returns_,
      SUM(sr_net_loss) AS profit_loss
    FROM READ_PARQUET('store_returns.parquet') AS store_returns, READ_PARQUET('date_dim.parquet') AS date_dim, READ_PARQUET('store.parquet') AS store
    WHERE
      sr_returned_date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-22' AS DATE)
      AND sr_store_sk = s_store_sk
    GROUP BY
      s_store_sk
), cs AS (
    SELECT
      cs_call_center_sk,
      SUM(cs_ext_sales_price) AS sales,
      SUM(cs_net_profit) AS profit
    FROM READ_PARQUET('catalog_sales.parquet') AS catalog_sales, READ_PARQUET('date_dim.parquet') AS date_dim
    WHERE
      cs_sold_date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-22' AS DATE)
    GROUP BY
      cs_call_center_sk
), cr AS (
    SELECT
      cr_call_center_sk,
      SUM(cr_return_amount) AS returns_,
      SUM(cr_net_loss) AS profit_loss
    FROM READ_PARQUET('catalog_returns.parquet') AS catalog_returns, READ_PARQUET('date_dim.parquet') AS date_dim
    WHERE
      cr_returned_date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-22' AS DATE)
    GROUP BY
      cr_call_center_sk
), ws AS (
    SELECT
      wp_web_page_sk,
      SUM(ws_ext_sales_price) AS sales,
      SUM(ws_net_profit) AS profit
    FROM READ_PARQUET('/home/cc/tpcds_partitioned_value/web_sales/**/*.parquet', hive_partitioning = 1) AS web_sales, READ_PARQUET('date_dim.parquet') AS date_dim, READ_PARQUET('web_page.parquet') AS web_page
    WHERE
      ws_sold_date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-22' AS DATE)
      AND ws_web_page_sk = wp_web_page_sk
    GROUP BY
      wp_web_page_sk
), wr AS (
    SELECT
      wp_web_page_sk,
      SUM(wr_return_amt) AS returns_,
      SUM(wr_net_loss) AS profit_loss
    FROM READ_PARQUET('web_returns.parquet') AS web_returns, READ_PARQUET('date_dim.parquet') AS date_dim, READ_PARQUET('web_page.parquet') AS web_page
    WHERE
      wr_returned_date_sk = d_date_sk
      AND d_date BETWEEN CAST('2000-08-23' AS DATE) AND CAST('2000-09-22' AS DATE)
      AND wr_web_page_sk = wp_web_page_sk
    GROUP BY
      wp_web_page_sk
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
          ss.s_store_sk AS id,
          sales,
          COALESCE(returns_, 0) AS returns_,
          (
            profit - COALESCE(profit_loss, 0)
          ) AS profit
        FROM ss
        LEFT JOIN sr
          ON ss.s_store_sk = sr.s_store_sk
        UNION ALL
        SELECT
          'catalog channel' AS channel,
          cs_call_center_sk AS id,
          sales,
          returns_,
          (
            profit - profit_loss
          ) AS profit
        FROM cs, cr
        UNION ALL
        SELECT
          'web channel' AS channel,
          ws.wp_web_page_sk AS id,
          sales,
          COALESCE(returns_, 0) AS returns_,
          (
            profit - COALESCE(profit_loss, 0)
          ) AS profit
        FROM ws
        LEFT JOIN wr
          ON ws.wp_web_page_sk = wr.wp_web_page_sk
    ) AS x
    GROUP BY
      channel,
      id
)
SELECT
  *
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