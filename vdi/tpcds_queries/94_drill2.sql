
SELECT count(DISTINCT web_sales.ws_order_number) AS "order count" ,
       sum(web_sales.ws_ext_ship_cost) AS "total shipping cost" ,
       sum(web_sales.ws_net_profit) AS "total net profit"
FROM dfs.`tmp/web_sales.parquet` ws1 ,
     dfs.`tmp/date_dim.parquet` AS date_dim ,
     dfs.`tmp/customer_address.parquet` AS customer_address ,
     dfs.`tmp/web_site.parquet` AS web_site
WHERE date_dim.d_date BETWEEN '1999-02-01' AND cast('1999-04-02' AS date)
  AND ws1.ws_ship_date_sk = date_dim.d_date_sk
  AND ws1.ws_ship_addr_sk = customer_address.ca_address_sk
  AND customer_address.ca_state = 'IL'
  AND ws1.ws_web_site_sk = web_site.web_site_sk
  AND web_site.web_company_name = 'pri'
  AND EXISTS
    (SELECT *
     FROM dfs.`tmp/web_sales.parquet` ws2
     WHERE ws1.ws_order_number = ws2.ws_order_number
       AND ws1.ws_warehouse_sk <> ws2.ws_warehouse_sk)
  AND NOT exists
    (SELECT *
     FROM dfs.`tmp/web_returns.parquet` wr1
     WHERE ws1.ws_order_number = wr1.wr_order_number)
ORDER BY count(DISTINCT web_sales.ws_order_number)
LIMIT 100;

