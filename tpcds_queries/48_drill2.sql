SELECT SUM (store_sales.ss_quantity)
FROM dfs.`tmp/store_sales.parquet` AS store_sales,
     dfs.`tmp/store.parquet` AS store,
     dfs.`tmp/customer_demographics.parquet` AS customer_demographics,
     dfs.`tmp/customer_address.parquet` AS customer_address,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE store.s_store_sk = store_sales.ss_store_sk
  AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
  AND date_dim.d_year = 2000
  AND ((customer_demographics.cd_demo_sk = store_sales.ss_cdemo_sk
        AND customer_demographics.cd_marital_status = 'M'
        AND customer_demographics.cd_education_status = '4 yr Degree'
        AND store_sales.ss_sales_price BETWEEN 100.00 AND 150.00)
       OR (customer_demographics.cd_demo_sk = store_sales.ss_cdemo_sk
           AND customer_demographics.cd_marital_status = 'D'
           AND customer_demographics.cd_education_status = '2 yr Degree'
           AND store_sales.ss_sales_price BETWEEN 50.00 AND 100.00)
       OR (customer_demographics.cd_demo_sk = store_sales.ss_cdemo_sk
           AND customer_demographics.cd_marital_status = 'S'
           AND customer_demographics.cd_education_status = 'College'
           AND store_sales.ss_sales_price BETWEEN 150.00 AND 200.00))
  AND ((store_sales.ss_addr_sk = customer_address.ca_address_sk
        AND customer_address.ca_country = 'United States'
        AND customer_address.ca_state IN ('CO',
                         'OH',
                         'TX')
        AND store_sales.ss_net_profit BETWEEN 0 AND 2000)
       OR (store_sales.ss_addr_sk = customer_address.ca_address_sk
           AND customer_address.ca_country = 'United States'
           AND customer_address.ca_state IN ('OR',
                            'MN',
                            'KY')
           AND store_sales.ss_net_profit BETWEEN 150 AND 3000)
       OR (store_sales.ss_addr_sk = customer_address.ca_address_sk
           AND customer_address.ca_country = 'United States'
           AND customer_address.ca_state IN ('VA',
                            'CA',
                            'MS')
           AND store_sales.ss_net_profit BETWEEN 50 AND 25000)) ;

