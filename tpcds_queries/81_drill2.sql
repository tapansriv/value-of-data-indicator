WITH customer_total_return AS
  (SELECT catalog_returns.cr_returning_customer_sk AS ctr_customer_sk ,
          customer_address.ca_state AS ctr_state,
          sum(catalog_returns.cr_return_amt_inc_tax) AS ctr_total_return
   FROM dfs.`tmp/catalog_returns.parquet` AS catalog_returns ,
        dfs.`tmp/date_dim.parquet` AS date_dim ,
        dfs.`tmp/customer_address.parquet` AS customer_address
   WHERE catalog_returns.cr_returned_date_sk = date_dim.d_date_sk
     AND date_dim.d_year = 2000
     AND catalog_returns.cr_returning_addr_sk = customer_address.ca_address_sk
   GROUP BY catalog_returns.cr_returning_customer_sk ,
            customer_address.ca_state)
SELECT customer.c_customer_id,
       customer.c_salutation,
       customer.c_first_name,
       customer.c_last_name,
       customer_address.ca_street_number,
       customer_address.ca_street_name ,
       customer_address.ca_street_type,
       customer_address.ca_suite_number,
       customer_address.ca_city,
       customer_address.ca_county,
       customer_address.ca_state,
       customer_address.ca_zip,
       customer_address.ca_country,
       customer_address.ca_gmt_offset ,
       customer_address.ca_location_type,
       ctr_total_return
FROM customer_total_return ctr1 ,
     dfs.`tmp/customer_address.parquet` AS customer_address ,
     dfs.`tmp/customer.parquet` AS customer
WHERE ctr1.ctr_total_return >
    (SELECT avg(ctr_total_return)*1.2
     FROM customer_total_return ctr2
     WHERE ctr1.ctr_state = ctr2.ctr_state)
  AND customer_address.ca_address_sk = customer.c_current_addr_sk
  AND customer_address.ca_state = 'GA'
  AND ctr1.ctr_customer_sk = customer.c_customer_sk
ORDER BY customer.c_customer_id,
         customer.c_salutation,
         customer.c_first_name,
         customer.c_last_name,
         customer_address.ca_street_number,
         customer_address.ca_street_name ,
         customer_address.ca_street_type,
         customer_address.ca_suite_number,
         customer_address.ca_city,
         customer_address.ca_county,
         customer_address.ca_state,
         customer_address.ca_zip,
         customer_address.ca_country,
         customer_address.ca_gmt_offset ,
         customer_address.ca_location_type,
         ctr_total_return
LIMIT 100;

