WITH ss AS
  (SELECT store.s_store_sk,
          sum(store_sales.ss_ext_sales_price) AS sales,
          sum(store_sales.ss_net_profit) AS profit
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-22' AS date)
     AND store_sales.ss_store_sk = store.s_store_sk
   GROUP BY store.s_store_sk),
sr AS
  (SELECT store.s_store_sk,
          sum(store_returns.sr_return_amt) AS returns_,
          sum(store_returns.sr_net_loss) AS profit_loss
   FROM dfs.`tmp/store_returns.parquet` AS store_returns,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store
   WHERE store_returns.sr_returned_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-22' AS date)
     AND store_returns.sr_store_sk = store.s_store_sk
   GROUP BY store.s_store_sk),
cs AS
  (SELECT catalog_sales.cs_call_center_sk,
          sum(catalog_sales.cs_ext_sales_price) AS sales,
          sum(catalog_sales.cs_net_profit) AS profit
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-22' AS date)
   GROUP BY catalog_sales.cs_call_center_sk),
cr AS
  (SELECT catalog_returns.cr_call_center_sk,
          sum(catalog_returns.cr_return_amount) AS returns_,
          sum(catalog_returns.cr_net_loss) AS profit_loss
   FROM dfs.`tmp/catalog_returns.parquet` AS catalog_returns,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE catalog_returns.cr_returned_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-22' AS date)
   GROUP BY catalog_returns.cr_call_center_sk),
ws AS
  (SELECT web_page.wp_web_page_sk,
          sum(web_sales.ws_ext_sales_price) AS sales,
          sum(web_sales.ws_net_profit) AS profit
   FROM dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/web_page.parquet` AS web_page
   WHERE web_sales.ws_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-22' AS date)
     AND web_sales.ws_web_page_sk = web_page.wp_web_page_sk
   GROUP BY web_page.wp_web_page_sk),
wr AS
  (SELECT web_page.wp_web_page_sk,
          sum(web_returns.wr_return_amt) AS returns_,
          sum(web_returns.wr_net_loss) AS profit_loss
   FROM dfs.`tmp/web_returns.parquet` AS web_returns,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/web_page.parquet` AS web_page
   WHERE web_returns.wr_returned_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-22' AS date)
     AND web_returns.wr_web_page_sk = web_page.wp_web_page_sk
   GROUP BY web_page.wp_web_page_sk),
results AS
  (SELECT channel ,
          id ,
          sum(sales) AS sales ,
          sum(returns_) AS returns_ ,
          sum(profit) AS profit
   FROM
     (SELECT 'store channel' AS channel ,
             ss.s_store_sk AS id ,
             sales ,
             coalesce(returns_, 0) AS returns_ ,
             (profit - coalesce(profit_loss,0)) AS profit
      FROM ss
      LEFT JOIN sr ON ss.s_store_sk = sr.s_store_sk
      UNION ALL SELECT 'catalog channel' AS channel ,
                       catalog_sales.cs_call_center_sk AS id ,
                       sales ,
                       returns_ ,
                       (profit - profit_loss) AS profit
      FROM cs ,
           cr
      UNION ALL SELECT 'web channel' AS channel ,
                       ws.wp_web_page_sk AS id ,
                       sales ,
                       coalesce(returns_, 0) returns_ ,
                       (profit - coalesce(profit_loss,0)) AS profit
      FROM ws
      LEFT JOIN wr ON ws.wp_web_page_sk = wr.wp_web_page_sk ) x
   GROUP BY channel,
            id)
SELECT *
FROM
  ( SELECT channel,
           id,
           sales,
           returns_,
           profit
   FROM results
   UNION SELECT channel,
                NULL AS id,
                sum(sales) AS sales,
                sum(returns_) AS returns_,
                sum(profit) AS profit
   FROM results
   GROUP BY channel
   UNION SELECT NULL AS channel,
                NULL AS id,
                sum(sales) AS sales,
                sum(returns_) AS returns_,
                sum(profit) AS profit
   FROM results) foo
ORDER BY channel NULLS FIRST,
         id NULLS FIRST
LIMIT 100;

