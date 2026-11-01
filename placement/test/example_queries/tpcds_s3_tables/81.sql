CREATE TABLE customer_total_return AS
  (SELECT cr_returning_customer_sk AS ctr_customer_sk ,
          ca_state AS ctr_state,
          sum(cr_return_amt_inc_tax) AS ctr_total_return
   FROM 's3://vod-tpcds-10gb/catalog_returns.parquet' AS catalog_returns ,
        's3://vod-tpcds-10gb/date_dim.parquet' AS date_dim ,
        's3://vod-tpcds-10gb/customer_address.parquet' AS customer_address
   WHERE cr_returned_date_sk = d_date_sk
     AND d_year = 2000
     AND cr_returning_addr_sk = ca_address_sk
   GROUP BY cr_returning_customer_sk ,
            ca_state);
SELECT c_customer_id,
       c_salutation,
       c_first_name,
       c_last_name,
       ca_street_number,
       ca_street_name ,
       ca_street_type,
       ca_suite_number,
       ca_city,
       ca_county,
       ca_state,
       ca_zip,
       ca_country,
       ca_gmt_offset ,
       ca_location_type,
       ctr_total_return
FROM customer_total_return ctr1 ,
     's3://vod-tpcds-10gb/customer_address.parquet' AS customer_address ,
     's3://vod-tpcds-10gb/customer.parquet' AS customer
WHERE ctr1.ctr_total_return >
    (SELECT avg(ctr_total_return)*1.2
     FROM customer_total_return ctr2
     WHERE ctr1.ctr_state = ctr2.ctr_state)
  AND ca_address_sk = c_current_addr_sk
  AND ca_state = 'GA'
  AND ctr1.ctr_customer_sk = c_customer_sk
ORDER BY c_customer_id,
         c_salutation,
         c_first_name,
         c_last_name,
         ca_street_number,
         ca_street_name ,
         ca_street_type,
         ca_suite_number,
         ca_city,
         ca_county,
         ca_state,
         ca_zip,
         ca_country,
         ca_gmt_offset ,
         ca_location_type,
         ctr_total_return
LIMIT 100;

