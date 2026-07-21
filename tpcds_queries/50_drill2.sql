SELECT store.s_store_name,
       store.s_company_id,
       store.s_street_number,
       store.s_street_name,
       store.s_street_type,
       store.s_suite_number,
       store.s_city,
       store.s_county,
       store.s_state,
       store.s_zip,
       sum(CASE
               WHEN (store_returns.sr_returned_date_sk - store_sales.ss_sold_date_sk <= 30) THEN 1
               ELSE 0
           END) AS days_30,
       sum(CASE
               WHEN (store_returns.sr_returned_date_sk - store_sales.ss_sold_date_sk > 30)
                    AND (store_returns.sr_returned_date_sk - store_sales.ss_sold_date_sk <= 60) THEN 1
               ELSE 0
           END) AS days_31_60,
       sum(CASE
               WHEN (store_returns.sr_returned_date_sk - store_sales.ss_sold_date_sk > 60)
                    AND (store_returns.sr_returned_date_sk - store_sales.ss_sold_date_sk <= 90) THEN 1
               ELSE 0
           END) AS days_61_90,
       sum(CASE
               WHEN (store_returns.sr_returned_date_sk - store_sales.ss_sold_date_sk > 90)
                    AND (store_returns.sr_returned_date_sk - store_sales.ss_sold_date_sk <= 120) THEN 1
               ELSE 0
           END) AS days_91_120,
       sum(CASE
               WHEN (store_returns.sr_returned_date_sk - store_sales.ss_sold_date_sk > 120) THEN 1
               ELSE 0
           END) AS days_120_up
FROM dfs.`tmp/store_sales.parquet` AS store_sales,
     dfs.`tmp/store_returns.parquet` AS store_returns,
     dfs.`tmp/store.parquet` AS store,
     dfs.`tmp/date_dim.parquet` d1,
     dfs.`tmp/date_dim.parquet` d2
WHERE d2.d_year = 2001
  AND d2.d_moy = 8
  AND store_sales.ss_ticket_number = store_returns.sr_ticket_number
  AND store_sales.ss_item_sk = store_returns.sr_item_sk
  AND store_sales.ss_sold_date_sk = d1.d_date_sk
  AND store_returns.sr_returned_date_sk = d2.d_date_sk
  AND store_sales.ss_customer_sk = store_returns.sr_customer_sk
  AND store_sales.ss_store_sk = store.s_store_sk
GROUP BY store.s_store_name,
         store.s_company_id,
         store.s_street_number,
         store.s_street_name,
         store.s_street_type,
         store.s_suite_number,
         store.s_city,
         store.s_county,
         store.s_state,
         store.s_zip
ORDER BY store.s_store_name,
         store.s_company_id,
         store.s_street_number,
         store.s_street_name,
         store.s_street_type,
         store.s_suite_number,
         store.s_city,
         store.s_county,
         store.s_state,
         store.s_zip
LIMIT 100;

