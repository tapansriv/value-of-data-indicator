WITH ss AS
  (SELECT customer_address.ca_county,
          date_dim.d_qoy,
          date_dim.d_year,
          sum(ss.ss_ext_sales_price) AS store_sales
   FROM dfs.`tmp/store_sales.parquet` AS ss,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer_address.parquet` AS customer_address
   WHERE ss.ss_sold_date_sk = date_dim.d_date_sk
     AND ss.ss_addr_sk=customer_address.ca_address_sk
   GROUP BY customer_address.ca_county,
            date_dim.d_qoy,
            date_dim.d_year),
ws AS
  (SELECT customer_address.ca_county,
          date_dim.d_qoy,
          date_dim.d_year,
          sum(ws.ws_ext_sales_price) AS web_sales
   FROM dfs.`tmp/web_sales.parquet` AS ws,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer_address.parquet` AS customer_address
   WHERE ws.ws_sold_date_sk = date_dim.d_date_sk
     AND ws.ws_bill_addr_sk=customer_address.ca_address_sk
   GROUP BY customer_address.ca_county,
            date_dim.d_qoy,
            date_dim.d_year)
SELECT ss1.ca_county ,
       ss1.d_year ,
       (ws2.web_sales*1.0000)/ws1.web_sales web_q1_q2_increase ,
       (ss2.store_sales*1.0000)/ss1.store_sales store_q1_q2_increase ,
       (ws3.web_sales*1.0000)/ws2.web_sales web_q2_q3_increase ,
       (ss3.store_sales*1.0000)/ss2.store_sales store_q2_q3_increase
FROM ss ss1 ,
     ss ss2 ,
     ss ss3 ,
     ws ws1 ,
     ws ws2 ,
     ws ws3
WHERE ss1.d_qoy = 1
  AND ss1.d_year = 2000
  AND ss1.ca_county = ss2.ca_county
  AND ss2.d_qoy = 2
  AND ss2.d_year = 2000
  AND ss2.ca_county = ss3.ca_county
  AND ss3.d_qoy = 3
  AND ss3.d_year = 2000
  AND ss1.ca_county = ws1.ca_county
  AND ws1.d_qoy = 1
  AND ws1.d_year = 2000
  AND ws1.ca_county = ws2.ca_county
  AND ws2.d_qoy = 2
  AND ws2.d_year = 2000
  AND ws1.ca_county = ws3.ca_county
  AND ws3.d_qoy = 3
  AND ws3.d_year = 2000
  AND CASE
          WHEN ws1.web_sales > 0 THEN (ws2.web_sales*1.0000)/ws1.web_sales
          ELSE NULL
      END > CASE
                WHEN ss1.store_sales > 0 THEN (ss2.store_sales*1.0000)/ss1.store_sales
                ELSE NULL
            END
  AND CASE
          WHEN ws2.web_sales > 0 THEN (ws3.web_sales*1.0000)/ws2.web_sales
          ELSE NULL
      END > CASE
                WHEN ss2.store_sales > 0 THEN (ss3.store_sales*1.0000)/ss2.store_sales
                ELSE NULL
            END
ORDER BY ss1.ca_county;

