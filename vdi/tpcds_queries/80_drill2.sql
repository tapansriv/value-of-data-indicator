WITH ssr AS
  (SELECT store.s_store_id AS store_id,
          sum(store_sales.ss_ext_sales_price) AS sales,
          sum(coalesce(store_returns.sr_return_amt, 0)) AS returns_,
          sum(store_sales.ss_net_profit - coalesce(store_returns.sr_net_loss, 0)) AS profit
   FROM dfs.`tmp/store_sales.parquet` AS store_sales
   LEFT OUTER JOIN dfs.`tmp/store_returns.parquet` AS store_returns ON (store_sales.ss_item_sk = store_returns.sr_item_sk
                                     AND store_sales.ss_ticket_number = store_returns.sr_ticket_number), dfs.`tmp/date_dim.parquet` AS date_dim,
                                                                               dfs.`tmp/store.parquet` AS store,
                                                                               dfs.`tmp/item.parquet` AS item,
                                                                               dfs.`tmp/promotion.parquet` AS promotion
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-22' AS date)
     AND store_sales.ss_store_sk = store.s_store_sk
     AND store_sales.ss_item_sk = item.i_item_sk
     AND item.i_current_price > 50
     AND store_sales.ss_promo_sk = promotion.p_promo_sk
     AND promotion.p_channel_tv = 'N'
   GROUP BY store.s_store_id),
csr AS
  (SELECT catalog_page.cp_catalog_page_id AS catalog_page_id,
          sum(catalog_sales.cs_ext_sales_price) AS sales,
          sum(coalesce(catalog_returns.cr_return_amount, 0)) AS returns_,
          sum(catalog_sales.cs_net_profit - coalesce(catalog_returns.cr_net_loss, 0)) AS profit
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales
   LEFT OUTER JOIN dfs.`tmp/catalog_returns.parquet` AS catalog_returns ON (catalog_sales.cs_item_sk = catalog_returns.cr_item_sk
                                       AND catalog_sales.cs_order_number = catalog_returns.cr_order_number), dfs.`tmp/date_dim.parquet` AS date_dim,
                                                                               dfs.`tmp/catalog_page.parquet` AS catalog_page,
                                                                               dfs.`tmp/item.parquet` AS item,
                                                                               dfs.`tmp/promotion.parquet` AS promotion
   WHERE catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-22' AS date)
     AND catalog_sales.cs_catalog_page_sk = catalog_page.cp_catalog_page_sk
     AND catalog_sales.cs_item_sk = item.i_item_sk
     AND item.i_current_price > 50
     AND catalog_sales.cs_promo_sk = promotion.p_promo_sk
     AND promotion.p_channel_tv = 'N'
   GROUP BY catalog_page.cp_catalog_page_id),
wsr AS
  (SELECT web_site.web_site_id,
          sum(web_sales.ws_ext_sales_price) AS sales,
          sum(coalesce(web_returns.wr_return_amt, 0)) AS returns_,
          sum(web_sales.ws_net_profit - coalesce(web_returns.wr_net_loss, 0)) AS profit
   FROM dfs.`tmp/web_sales.parquet` AS web_sales
   LEFT OUTER JOIN dfs.`tmp/web_returns.parquet` AS web_returns ON (web_sales.ws_item_sk = web_returns.wr_item_sk
                                   AND web_sales.ws_order_number = web_returns.wr_order_number), dfs.`tmp/date_dim.parquet` AS date_dim,
                                                                           dfs.`tmp/web_site.parquet` AS web_site,
                                                                           dfs.`tmp/item.parquet` AS item,
                                                                           dfs.`tmp/promotion.parquet` AS promotion
   WHERE web_sales.ws_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN cast('2000-08-23' AS date) AND cast('2000-09-22' AS date)
     AND web_sales.ws_web_site_sk = web_site.web_site_sk
     AND web_sales.ws_item_sk = item.i_item_sk
     AND item.i_current_price > 50
     AND web_sales.ws_promo_sk = promotion.p_promo_sk
     AND promotion.p_channel_tv = 'N'
   GROUP BY web_site.web_site_id),
results AS
  (SELECT channel ,
          id ,
          sum(sales) AS sales ,
          sum(returns_) AS returns_ ,
          sum(profit) AS profit
   FROM
     (SELECT 'store channel' AS channel ,
             concat('store', store_id) AS id ,
             sales ,
             returns_ ,
             profit
      FROM ssr
      UNION ALL SELECT 'catalog channel' AS channel ,
                       concat('catalog_page', catalog_page_id) AS id ,
                       sales ,
                       returns_ ,
                       profit
      FROM csr
      UNION ALL SELECT 'web channel' AS channel ,
                       concat('web_site', web_site.web_site_id) AS id ,
                       sales ,
                       returns_ ,
                       profit
      FROM wsr ) x
   GROUP BY channel,
            id)
SELECT channel ,
       id ,
       sales ,
       returns_ ,
       profit
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
   FROM results ) foo
ORDER BY channel NULLS FIRST,
         id NULLS FIRST
LIMIT 100;

