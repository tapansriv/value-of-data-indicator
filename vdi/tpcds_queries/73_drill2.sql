
SELECT customer.c_last_name,
       customer.c_first_name,
       customer.c_salutation,
       customer.c_preferred_cust_flag,
       store_sales.ss_ticket_number,
       cnt
FROM
  (SELECT store_sales.ss_ticket_number,
          store_sales.ss_customer_sk,
          count(*) cnt
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/household_demographics.parquet` AS household_demographics
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND store_sales.ss_hdemo_sk = household_demographics.hd_demo_sk
     AND date_dim.d_dom BETWEEN 1 AND 2
     AND (household_demographics.hd_buy_potential = 'Unknown'
          OR household_demographics.hd_buy_potential = '>10000')
     AND household_demographics.hd_vehicle_count > 0
     AND CASE
             WHEN household_demographics.hd_vehicle_count > 0 THEN (household_demographics.hd_dep_count*1.000)/ household_demographics.hd_vehicle_count
             ELSE NULL
         END > 1
     AND date_dim.d_year IN (1999,
                             1999+1,
                             1999+2)
     AND store.s_county IN ('Orange County',
                            'Bronx County',
                            'Franklin Parish',
                            'Williamson County')
   GROUP BY store_sales.ss_ticket_number,
            store_sales.ss_customer_sk) dj,
     dfs.`tmp/customer.parquet` AS customer
WHERE store_sales.ss_customer_sk = customer.c_customer_sk
  AND cnt BETWEEN 1 AND 5
ORDER BY cnt DESC,
         customer.c_last_name ASC;

