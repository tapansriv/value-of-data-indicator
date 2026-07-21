SELECT customer.c_last_name,
       customer.c_first_name,
       customer_address.ca_city,
       bought_city,
       store_sales.ss_ticket_number,
       extended_price,
       extended_tax,
       list_price
FROM
  (SELECT store_sales.ss_ticket_number,
          store_sales.ss_customer_sk,
          customer_address.ca_city bought_city,
          sum(store_sales.ss_ext_sales_price) extended_price,
          sum(store_sales.ss_ext_list_price) list_price,
          sum(store_sales.ss_ext_tax) extended_tax
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/household_demographics.parquet` AS household_demographics,
        dfs.`tmp/customer_address.parquet` AS customer_address
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND store_sales.ss_hdemo_sk = household_demographics.hd_demo_sk
     AND store_sales.ss_addr_sk = customer_address.ca_address_sk
     AND date_dim.d_dom BETWEEN 1 AND 2
     AND (household_demographics.hd_dep_count = 4
          OR household_demographics.hd_vehicle_count= 3)
     AND date_dim.d_year IN (1999,
                             1999+1,
                             1999+2)
     AND store.s_city IN ('Fairview',
                          'Midway')
   GROUP BY store_sales.ss_ticket_number,
            store_sales.ss_customer_sk,
            store_sales.ss_addr_sk,
            customer_address.ca_city) dn,
     dfs.`tmp/customer.parquet` AS customer,
     dfs.`tmp/customer_address.parquet` current_addr
WHERE store_sales.ss_customer_sk = customer.c_customer_sk
  AND customer.c_current_addr_sk = current_addr.ca_address_sk
  AND current_addr.ca_city <> bought_city
ORDER BY customer.c_last_name NULLS FIRST,
         store_sales.ss_ticket_number NULLS FIRST
LIMIT 100;

