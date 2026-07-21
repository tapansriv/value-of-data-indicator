WITH ssr AS
  (SELECT store.s_store_id s_store_id,
          sum(salesreturns.sales_price) AS sales,
          sum(salesreturns.profit) AS profit,
          sum(salesreturns.return_amt) AS returns_,
          sum(salesreturns.net_loss) AS profit_loss
   FROM
     (SELECT store_sales.ss_store_sk AS store_sk,
             store_sales.ss_sold_date_sk AS date_sk,
             store_sales.ss_ext_sales_price AS sales_price,
             store_sales.ss_net_profit AS profit,
             cast(0 AS decimal(7,2)) AS return_amt,
             cast(0 AS decimal(7,2)) AS net_loss
      FROM dfs.`tmp/store_sales.parquet` AS store_sales
      UNION ALL SELECT store_returns.sr_store_sk AS store_sk,
                       store_returns.sr_returned_date_sk AS date_sk,
                       cast(0 AS decimal(7,2)) AS sales_price,
                       cast(0 AS decimal(7,2)) AS profit,
                       store_returns.sr_return_amt AS return_amt,
                       store_returns.sr_net_loss AS net_loss
      FROM dfs.`tmp/store_returns.parquet` AS store_returns ) salesreturns,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store
   WHERE salesreturns.date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-06' AS date)
     AND salesreturns.store_sk = store.s_store_sk
   GROUP BY store.s_store_id),
csr AS
  (SELECT catalog_page.cp_catalog_page_id cp_catalog_page_id,
          sum(salesreturns.sales_price) AS sales,
          sum(salesreturns.profit) AS profit,
          sum(salesreturns.return_amt) AS returns_,
          sum(salesreturns.net_loss) AS profit_loss
   FROM
     (SELECT catalog_sales.cs_catalog_page_sk AS page_sk,
             catalog_sales.cs_sold_date_sk AS date_sk,
             catalog_sales.cs_ext_sales_price AS sales_price,
             catalog_sales.cs_net_profit AS profit,
             cast(0 AS decimal(7,2)) AS return_amt,
             cast(0 AS decimal(7,2)) AS net_loss
      FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales
      UNION ALL SELECT catalog_returns.cr_catalog_page_sk AS page_sk,
                       catalog_returns.cr_returned_date_sk AS date_sk,
                       cast(0 AS decimal(7,2)) AS sales_price,
                       cast(0 AS decimal(7,2)) AS profit,
                       catalog_returns.cr_return_amount AS return_amt,
                       catalog_returns.cr_net_loss AS net_loss
      FROM dfs.`tmp/catalog_returns.parquet` AS catalog_returns ) salesreturns,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/catalog_page.parquet` AS catalog_page
   WHERE salesreturns.date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-06' AS date)
     AND salesreturns.page_sk = catalog_page.cp_catalog_page_sk
   GROUP BY catalog_page.cp_catalog_page_id),
wsr AS
  (SELECT web_site.web_site_id web_site_id,
          sum(salesreturns.sales_price) AS sales,
          sum(salesreturns.profit) AS profit,
          sum(salesreturns.return_amt) AS returns_,
          sum(salesreturns.net_loss) AS profit_loss
   FROM
     (SELECT web_sales.ws_web_site_sk AS wsr_web_site_sk,
             web_sales.ws_sold_date_sk AS date_sk,
             web_sales.ws_ext_sales_price AS sales_price,
             web_sales.ws_net_profit AS profit,
             cast(0 AS decimal(7,2)) AS return_amt,
             cast(0 AS decimal(7,2)) AS net_loss
      FROM dfs.`tmp/web_sales.parquet` AS web_sales
      UNION ALL SELECT web_sales.ws_web_site_sk AS wsr_web_site_sk,
                       web_returns.wr_returned_date_sk AS date_sk,
                       cast(0 AS decimal(7,2)) AS sales_price,
                       cast(0 AS decimal(7,2)) AS profit,
                       web_returns.wr_return_amt AS return_amt,
                       web_returns.wr_net_loss AS net_loss
      FROM dfs.`tmp/web_returns.parquet` AS web_returns
      LEFT OUTER JOIN dfs.`tmp/web_sales.parquet` AS web_sales ON (web_returns.wr_item_sk = web_sales.ws_item_sk
                                    AND web_returns.wr_order_number = web_sales.ws_order_number) ) salesreturns,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/web_site.parquet` AS web_site
   WHERE salesreturns.date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-06' AS date)
     AND salesreturns.wsr_web_site_sk = web_site.web_site_sk
   GROUP BY web_site.web_site_id),
results AS
  (SELECT channel ,
          cast(id as varchar) id,
          sum(sales) AS sales ,
          sum(returns_) AS returns_ ,
          sum(profit) AS profit
   FROM
     (SELECT 'store channel' AS channel ,
             concat('store', ssr.s_store_id) AS id ,
             ssr.sales ,
             ssr.returns_ ,
             (ssr.profit - ssr.profit_loss) AS profit
      FROM ssr
      UNION ALL SELECT 'catalog channel' AS channel ,
                       concat('catalog_page', csr.cp_catalog_page_id) AS id ,
                       csr.sales ,
                       csr.returns_ ,
                       (csr.profit - csr.profit_loss) AS profit
      FROM csr
      UNION ALL SELECT 'web channel' AS channel ,
                       concat('web_site', wsr.web_site_id) AS id ,
                       wsr.sales ,
                       wsr.returns_ ,
                       (wsr.profit - wsr.profit_loss) AS profit
      FROM wsr ) x
   GROUP BY channel,
            id)
SELECT channel,
       id,
       sales,
       returns_,
       profit
FROM
  (SELECT channel,
          cast(id as varchar) id,
          sales,
          returns_,
          profit
   FROM results) foo
   -- UNION SELECT channel,
   --              cast(NULL as varchar) AS id,
   --              sum(sales),
   --              sum(returns_),
   --              sum(profit)
   -- FROM results
   -- GROUP BY channel
   -- UNION SELECT cast(NULL as varchar) AS channel,
   --              cast(NULL as varchar) AS id,
   --              sum(sales),
   --              sum(returns_),
   --              sum(profit)
   -- FROM results) foo
ORDER BY channel NULLS FIRST,
         id NULLS FIRST
LIMIT 100;

