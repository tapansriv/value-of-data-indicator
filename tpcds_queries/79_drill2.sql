
SELECT customer.c_last_name,
       customer.c_first_name,
       SUBSTRING(store.s_city,1,30),
       store_sales.ss_ticket_number,
       amt,
       profit
FROM
  (SELECT store_sales.ss_ticket_number ,
          store_sales.ss_customer_sk ,
          store.s_city ,
          sum(store_sales.ss_coupon_amt) amt ,
          sum(store_sales.ss_net_profit) profit
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/household_demographics.parquet` AS household_demographics
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND store_sales.ss_hdemo_sk = household_demographics.hd_demo_sk
     AND (household_demographics.hd_dep_count = 6
          OR household_demographics.hd_vehicle_count > 2)
     AND date_dim.d_dow = 1
     AND date_dim.d_year IN (1999,
                             1999+1,
                             1999+2)
     AND store.s_number_employees BETWEEN 200 AND 295
   GROUP BY store_sales.ss_ticket_number,
            store_sales.ss_customer_sk,
            store_sales.ss_addr_sk,
            store.s_city) ms,
     dfs.`tmp/customer.parquet` AS customer
WHERE store_sales.ss_customer_sk = customer.c_customer_sk
ORDER BY customer.c_last_name  NULLS FIRST,
         customer.c_first_name  NULLS FIRST,
         SUBSTRING(store.s_city,1,30)  NULLS FIRST,
         profit NULLS FIRST
LIMIT 100;

