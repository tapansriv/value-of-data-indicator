SELECT avg(store_sales.ss_quantity) avg1,
       avg(store_sales.ss_ext_sales_price) avg2,
       avg(store_sales.ss_ext_wholesale_cost) avg3,
       sum(store_sales.ss_ext_wholesale_cost)
FROM dfs.`tmp/store_sales.parquet` AS store_sales ,
     dfs.`tmp/store.parquet` AS store ,
     dfs.`tmp/customer_demographics.parquet` AS customer_demographics ,
     dfs.`tmp/household_demographics.parquet` AS household_demographics ,
     dfs.`tmp/customer_address.parquet` AS customer_address ,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE store.s_store_sk = store_sales.ss_store_sk
  AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
  AND date_dim.d_year = 2001 and((store_sales.ss_hdemo_sk=household_demographics.hd_demo_sk
                         AND customer_demographics.cd_demo_sk = store_sales.ss_cdemo_sk
                         AND customer_demographics.cd_marital_status = 'M'
                         AND customer_demographics.cd_education_status = 'Advanced Degree'
                         AND store_sales.ss_sales_price BETWEEN 100.00 AND 150.00
                         AND household_demographics.hd_dep_count = 3)
                        OR (store_sales.ss_hdemo_sk=household_demographics.hd_demo_sk
                            AND customer_demographics.cd_demo_sk = store_sales.ss_cdemo_sk
                            AND customer_demographics.cd_marital_status = 'S'
                            AND customer_demographics.cd_education_status = 'College'
                            AND store_sales.ss_sales_price BETWEEN 50.00 AND 100.00
                            AND household_demographics.hd_dep_count = 1 )
                        OR (store_sales.ss_hdemo_sk=household_demographics.hd_demo_sk
                            AND customer_demographics.cd_demo_sk = store_sales.ss_cdemo_sk
                            AND customer_demographics.cd_marital_status = 'W'
                            AND customer_demographics.cd_education_status = '2 yr Degree'
                            AND store_sales.ss_sales_price BETWEEN 150.00 AND 200.00
                            AND household_demographics.hd_dep_count = 1)) and((store_sales.ss_addr_sk = customer_address.ca_address_sk
                                                        AND customer_address.ca_country = 'United States'
                                                        AND customer_address.ca_state IN ('TX', 'OH', 'TX')
                                                        AND store_sales.ss_net_profit BETWEEN 100 AND 200)
                                                       OR (store_sales.ss_addr_sk = customer_address.ca_address_sk
                                                           AND customer_address.ca_country = 'United States'
                                                           AND customer_address.ca_state IN ('OR', 'NM', 'KY')
                                                           AND store_sales.ss_net_profit BETWEEN 150 AND 300)
                                                       OR (store_sales.ss_addr_sk = customer_address.ca_address_sk
                                                           AND customer_address.ca_country = 'United States'
                                                           AND customer_address.ca_state IN ('VA', 'TX', 'MS')
                                                           AND store_sales.ss_net_profit BETWEEN 50 AND 250)) ;

