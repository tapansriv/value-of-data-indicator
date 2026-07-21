SELECT customer.c_last_name ,
       customer.c_first_name ,
       customer.c_salutation ,
       customer.c_preferred_cust_flag ,
       dn.ss_ticket_number ,
       dn.cnt
FROM
  (SELECT store_sales.ss_ticket_number ,
          store_sales.ss_customer_sk ,
          count(*) cnt
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/household_demographics.parquet` AS household_demographics
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND store_sales.ss_hdemo_sk = household_demographics.hd_demo_sk
     AND (date_dim.d_dom BETWEEN 1 AND 3
          OR date_dim.d_dom BETWEEN 25 AND 28)
     AND (household_demographics.hd_buy_potential = '>10000'
          OR household_demographics.hd_buy_potential = 'Unknown')
     AND household_demographics.hd_vehicle_count > 0
     AND (CASE
              WHEN household_demographics.hd_vehicle_count > 0 THEN (household_demographics.hd_dep_count*1.000)/ household_demographics.hd_vehicle_count
              ELSE NULL
          END) > 1.2
     AND date_dim.d_year IN (1999,
                             1999+1,
                             1999+2)
     AND store.s_county = 'Williamson County'
   GROUP BY store_sales.ss_ticket_number,
            store_sales.ss_customer_sk) dn,
     dfs.`tmp/customer.parquet` AS customer
WHERE dn.ss_customer_sk = customer.c_customer_sk
  AND dn.cnt BETWEEN 15 AND 20
ORDER BY customer.c_last_name NULLS FIRST,
         customer.c_first_name NULLS FIRST,
         customer.c_salutation NULLS FIRST,
         customer.c_preferred_cust_flag DESC NULLS FIRST,
         dn.ss_ticket_number NULLS FIRST;

