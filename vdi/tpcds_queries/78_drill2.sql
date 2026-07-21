WITH ws AS
  (SELECT date_dim.d_year AS ws_sold_year,
          web_sales.ws_item_sk,
          web_sales.ws_bill_customer_sk ws_customer_sk,
          sum(web_sales.ws_quantity) ws_qty,
          sum(web_sales.ws_wholesale_cost) ws_wc,
          sum(web_sales.ws_sales_price) ws_sp
   FROM dfs.`tmp/web_sales.parquet` AS web_sales
   LEFT JOIN dfs.`tmp/web_returns.parquet` AS web_returns ON web_returns.wr_order_number=ws_order_number
   AND web_sales.ws_item_sk=wr_item_sk
   JOIN dfs.`tmp/date_dim.parquet` AS date_dim ON web_sales.ws_sold_date_sk = date_dim.d_date_sk
   WHERE web_returns.wr_order_number IS NULL
   GROUP BY date_dim.d_year,
            web_sales.ws_item_sk,
            web_sales.ws_bill_customer_sk ),
cs AS
  (SELECT date_dim.d_year AS cs_sold_year,
          catalog_sales.cs_item_sk,
          catalog_sales.cs_bill_customer_sk cs_customer_sk,
          sum(catalog_sales.cs_quantity) cs_qty,
          sum(catalog_sales.cs_wholesale_cost) cs_wc,
          sum(catalog_sales.cs_sales_price) cs_sp
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales
   LEFT JOIN dfs.`tmp/catalog_returns.parquet` AS catalog_returns ON catalog_returns.cr_order_number=cs_order_number
   AND catalog_sales.cs_item_sk=cr_item_sk
   JOIN dfs.`tmp/date_dim.parquet` AS date_dim ON catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
   WHERE catalog_returns.cr_order_number IS NULL
   GROUP BY date_dim.d_year,
            catalog_sales.cs_item_sk,
            catalog_sales.cs_bill_customer_sk ),
ss AS
  (SELECT date_dim.d_year AS ss_sold_year,
          store_sales.ss_item_sk,
          store_sales.ss_customer_sk,
          sum(store_sales.ss_quantity) ss_qty,
          sum(store_sales.ss_wholesale_cost) ss_wc,
          sum(store_sales.ss_sales_price) ss_sp
   FROM dfs.`tmp/store_sales.parquet` AS store_sales
   LEFT JOIN dfs.`tmp/store_returns.parquet` AS store_returns ON store_returns.sr_ticket_number=ss_ticket_number
   AND store_sales.ss_item_sk=sr_item_sk
   JOIN dfs.`tmp/date_dim.parquet` AS date_dim ON store_sales.ss_sold_date_sk = date_dim.d_date_sk
   WHERE store_returns.sr_ticket_number IS NULL
   GROUP BY date_dim.d_year,
            store_sales.ss_item_sk,
            store_sales.ss_customer_sk )
SELECT ss_sold_year,
       store_sales.ss_item_sk,
       store_sales.ss_customer_sk,
       round((ss_qty*1.00)/(coalesce(ws_qty,0)+coalesce(cs_qty,0)),2) ratio,
       ss_qty store_qty,
       ss_wc store_wholesale_cost,
       ss_sp store_sales_price,
       coalesce(ws_qty,0)+coalesce(cs_qty,0) other_chan_qty,
       coalesce(ws_wc,0)+coalesce(cs_wc,0) other_chan_wholesale_cost,
       coalesce(ws_sp,0)+coalesce(cs_sp,0) other_chan_sales_price
FROM ss
LEFT JOIN ws ON (ws_sold_year=ss_sold_year
                 AND web_sales.ws_item_sk=ss_item_sk
                 AND ws_customer_sk=ss_customer_sk)
LEFT JOIN cs ON (cs_sold_year=ss_sold_year
                 AND catalog_sales.cs_item_sk=ss_item_sk
                 AND cs_customer_sk=ss_customer_sk)
WHERE (coalesce(ws_qty,0)>0
       OR coalesce(cs_qty, 0)>0)
  AND ss_sold_year=2000
ORDER BY ss_sold_year,
         store_sales.ss_item_sk,
         store_sales.ss_customer_sk,
         ss_qty DESC,
         ss_wc DESC,
         ss_sp DESC,
         other_chan_qty,
         other_chan_wholesale_cost,
         other_chan_sales_price,
         ratio
LIMIT 100;

