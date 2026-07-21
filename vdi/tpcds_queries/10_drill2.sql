SELECT customer_demographics.cd_gender,
       customer_demographics.cd_marital_status,
       customer_demographics.cd_education_status,
       count(*) cnt1,
       customer_demographics.cd_purchase_estimate,
       count(*) cnt2,
       customer_demographics.cd_credit_rating,
       count(*) cnt3,
       customer_demographics.cd_dep_count,
       count(*) cnt4,
       customer_demographics.cd_dep_employed_count,
       count(*) cnt5,
       customer_demographics.cd_dep_college_count,
       count(*) cnt6
FROM dfs.`tmp/customer.parquet` c,
     dfs.`tmp/customer_address.parquet` ca,
     dfs.`tmp/customer_demographics.parquet` AS customer_demographics
WHERE c.c_current_addr_sk = ca.ca_address_sk
  AND ca.ca_county IN ('Rush County',
                    'Toole County',
                    'Jefferson County',
                    'Dona Ana County',
                    'La Porte County')
  AND customer_demographics.cd_demo_sk = c.c_current_cdemo_sk
  AND EXISTS
    (SELECT *
     FROM dfs.`tmp/store_sales.parquet` AS store_sales,
          dfs.`tmp/date_dim.parquet` AS date_dim
     WHERE c.c_customer_sk = store_sales.ss_customer_sk
       AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
       AND date_dim.d_year = 2002
       AND date_dim.d_moy BETWEEN 1 AND 1+3)
  AND (EXISTS
         (SELECT *
          FROM dfs.`tmp/web_sales.parquet` AS web_sales,
               dfs.`tmp/date_dim.parquet` AS date_dim
          WHERE c.c_customer_sk = web_sales.ws_bill_customer_sk
            AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
            AND date_dim.d_year = 2002
            AND date_dim.d_moy BETWEEN 1 AND 1+3)
       OR EXISTS
         (SELECT *
          FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
               dfs.`tmp/date_dim.parquet` AS date_dim
          WHERE c.c_customer_sk = catalog_sales.cs_ship_customer_sk
            AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
            AND date_dim.d_year = 2002
            AND date_dim.d_moy BETWEEN 1 AND 1+3))
GROUP BY customer_demographics.cd_gender,
         customer_demographics.cd_marital_status,
         customer_demographics.cd_education_status,
         customer_demographics.cd_purchase_estimate,
         customer_demographics.cd_credit_rating,
         customer_demographics.cd_dep_count,
         customer_demographics.cd_dep_employed_count,
         customer_demographics.cd_dep_college_count
ORDER BY customer_demographics.cd_gender,
         customer_demographics.cd_marital_status,
         customer_demographics.cd_education_status,
         customer_demographics.cd_purchase_estimate,
         customer_demographics.cd_credit_rating,
         customer_demographics.cd_dep_count,
         customer_demographics.cd_dep_employed_count,
         customer_demographics.cd_dep_college_count
LIMIT 100;

