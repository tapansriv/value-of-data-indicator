
SELECT SUBSTRING(reason.r_reason_desc,1,20) ,
       avg(web_sales.ws_quantity) avg1,
       avg(web_returns.wr_refunded_cash) avg2,
       avg(web_returns.wr_fee)
FROM dfs.`tmp/web_sales.parquet` AS web_sales,
     dfs.`tmp/web_returns.parquet` AS web_returns,
     dfs.`tmp/web_page.parquet` AS web_page,
     dfs.`tmp/customer_demographics.parquet` cd1,
     dfs.`tmp/customer_demographics.parquet` cd2,
     dfs.`tmp/customer_address.parquet` AS customer_address,
     dfs.`tmp/date_dim.parquet` AS date_dim,
     dfs.`tmp/reason.parquet` AS reason
WHERE web_sales.ws_web_page_sk = web_page.wp_web_page_sk
  AND web_sales.ws_item_sk = web_returns.wr_item_sk
  AND web_sales.ws_order_number = web_returns.wr_order_number
  AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
  AND date_dim.d_year = 2000
  AND cd1.cd_demo_sk = web_returns.wr_refunded_cdemo_sk
  AND cd2.cd_demo_sk = web_returns.wr_returning_cdemo_sk
  AND customer_address.ca_address_sk = web_returns.wr_refunded_addr_sk
  AND reason.r_reason_sk = web_returns.wr_reason_sk
  AND ( ( cd1.cd_marital_status = 'M'
         AND cd1.cd_marital_status = cd2.cd_marital_status
         AND cd1.cd_education_status = 'Advanced Degree'
         AND cd1.cd_education_status = cd2.cd_education_status
         AND web_sales.ws_sales_price BETWEEN 100.00 AND 150.00 )
       OR ( cd1.cd_marital_status = 'S'
           AND cd1.cd_marital_status = cd2.cd_marital_status
           AND cd1.cd_education_status = 'College'
           AND cd1.cd_education_status = cd2.cd_education_status
           AND web_sales.ws_sales_price BETWEEN 50.00 AND 100.00 )
       OR ( cd1.cd_marital_status = 'W'
           AND cd1.cd_marital_status = cd2.cd_marital_status
           AND cd1.cd_education_status = '2 yr Degree'
           AND cd1.cd_education_status = cd2.cd_education_status
           AND web_sales.ws_sales_price BETWEEN 150.00 AND 200.00 ) )
  AND ( ( customer_address.ca_country = 'United States'
         AND customer_address.ca_state IN ('IN',
                          'OH',
                          'NJ')
         AND web_sales.ws_net_profit BETWEEN 100 AND 200)
       OR ( customer_address.ca_country = 'United States'
           AND customer_address.ca_state IN ('WI',
                            'CT',
                            'KY')
           AND web_sales.ws_net_profit BETWEEN 150 AND 300)
       OR ( customer_address.ca_country = 'United States'
           AND customer_address.ca_state IN ('LA',
                            'IA',
                            'AR')
           AND web_sales.ws_net_profit BETWEEN 50 AND 250) )
GROUP BY reason.r_reason_desc
ORDER BY SUBSTRING(reason.r_reason_desc,1,20) ,
         avg(web_sales.ws_quantity) ,
         avg(web_returns.wr_refunded_cash) ,
         avg(web_returns.wr_fee)
LIMIT 100;
