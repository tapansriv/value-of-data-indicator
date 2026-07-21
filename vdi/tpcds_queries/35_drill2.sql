SELECT ca.ca_state,
       customer_demographics.cd_gender,
       customer_demographics.cd_marital_status,
       customer_demographics.cd_dep_count,
       count(*) cnt1,
       min(customer_demographics.cd_dep_count) min1,
       max(customer_demographics.cd_dep_count) max1,
       avg(customer_demographics.cd_dep_count) avg1,
       customer_demographics.cd_dep_employed_count,
       count(*) cnt2,
       min(customer_demographics.cd_dep_employed_count) min2,
       max(customer_demographics.cd_dep_employed_count) max2,
       avg(customer_demographics.cd_dep_employed_count) avg2,
       customer_demographics.cd_dep_college_count,
       count(*) cnt3,
       min(customer_demographics.cd_dep_college_count),
       max(customer_demographics.cd_dep_college_count),
       avg(customer_demographics.cd_dep_college_count)
FROM dfs.`tmp/customer.parquet` c,
     dfs.`tmp/customer_address.parquet` ca,
     dfs.`tmp/customer_demographics.parquet` AS customer_demographics
WHERE c.c_current_addr_sk = ca.ca_address_sk
  AND customer_demographics.cd_demo_sk = c.c_current_cdemo_sk
  AND EXISTS
    (SELECT *
     FROM dfs.`tmp/store_sales.parquet` AS store_sales,
          dfs.`tmp/date_dim.parquet` AS date_dim
     WHERE c.c_customer_sk = store_sales.ss_customer_sk
       AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
       AND date_dim.d_year = 2002
       AND date_dim.d_qoy < 4)
  AND (EXISTS
         (SELECT *
          FROM dfs.`tmp/web_sales.parquet` AS web_sales,
               dfs.`tmp/date_dim.parquet` AS date_dim
          WHERE c.c_customer_sk = web_sales.ws_bill_customer_sk
            AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
            AND date_dim.d_year = 2002
            AND date_dim.d_qoy < 4)
       OR EXISTS
         (SELECT *
          FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
               dfs.`tmp/date_dim.parquet` AS date_dim
          WHERE c.c_customer_sk = catalog_sales.cs_ship_customer_sk
            AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
            AND date_dim.d_year = 2002
            AND date_dim.d_qoy < 4))
GROUP BY ca.ca_state,
         customer_demographics.cd_gender,
         customer_demographics.cd_marital_status,
         customer_demographics.cd_dep_count,
         customer_demographics.cd_dep_employed_count,
         customer_demographics.cd_dep_college_count
ORDER BY ca.ca_state NULLS FIRST,
         customer_demographics.cd_gender NULLS FIRST,
         customer_demographics.cd_marital_status NULLS FIRST,
         customer_demographics.cd_dep_count NULLS FIRST,
         customer_demographics.cd_dep_employed_count NULLS FIRST,
         customer_demographics.cd_dep_college_count NULLS FIRST
LIMIT 100;

