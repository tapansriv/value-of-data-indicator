WITH customer_total_return AS
  (SELECT web_returns.wr_returning_customer_sk AS ctr_customer_sk,
          customer_address.ca_state AS ctr_state,
          sum(web_returns.wr_return_amt) AS ctr_total_return
   FROM dfs.`tmp/web_returns.parquet` AS web_returns,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer_address.parquet` AS customer_address
   WHERE web_returns.wr_returned_date_sk = date_dim.d_date_sk
     AND date_dim.d_year = 2002
     AND web_returns.wr_returning_addr_sk = customer_address.ca_address_sk
   GROUP BY web_returns.wr_returning_customer_sk,
            customer_address.ca_state)
SELECT customer.c_customer_id,
       customer.c_salutation,
       customer.c_first_name,
       customer.c_last_name,
       customer.c_preferred_cust_flag,
       customer.c_birth_day,
       customer.c_birth_month,
       customer.c_birth_year,
       customer.c_birth_country,
       customer.c_login,
       customer.c_email_address,
       customer.c_last_review_date_sk,
       ctr1.ctr_total_return
FROM customer_total_return ctr1,
     dfs.`tmp/customer_address.parquet` AS customer_address,
     dfs.`tmp/customer.parquet` AS customer
WHERE ctr1.ctr_total_return >
    (SELECT avg(ctr2.ctr_total_return)*1.2
     FROM customer_total_return ctr2
     WHERE ctr1.ctr_state = ctr2.ctr_state)
  AND customer_address.ca_address_sk = customer.c_current_addr_sk
  AND customer_address.ca_state = 'GA'
  AND ctr1.ctr_customer_sk = customer.c_customer_sk
ORDER BY customer.c_customer_id NULLS FIRST,
         customer.c_salutation NULLS FIRST,
         customer.c_first_name NULLS FIRST,
         customer.c_last_name NULLS FIRST,
         customer.c_preferred_cust_flag NULLS FIRST,
         customer.c_birth_day NULLS FIRST,
         customer.c_birth_month NULLS FIRST,
         customer.c_birth_year NULLS FIRST,
         customer.c_birth_country NULLS FIRST,
         customer.c_login NULLS FIRST,
         customer.c_email_address NULLS FIRST,
         customer.c_last_review_date_sk NULLS FIRST,
         ctr_total_return NULLS FIRST
LIMIT 100;

