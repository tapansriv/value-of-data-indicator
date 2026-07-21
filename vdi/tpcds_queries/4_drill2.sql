WITH year_total AS
  (SELECT customer.c_customer_id customer_id,
          customer.c_first_name customer_first_name,
          customer.c_last_name customer_last_name,
          customer.c_preferred_cust_flag customer_preferred_cust_flag,
          customer.c_birth_country customer_birth_country,
          customer.c_login customer_login,
          customer.c_email_address customer_email_address,
          date_dim.d_year dyear,
          sum(((store_sales.ss_ext_list_price-store_sales.ss_ext_wholesale_cost-store_sales.ss_ext_discount_amt)+store_sales.ss_ext_sales_price)/2) year_total,
          's' sale_type
   FROM dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE customer.c_customer_sk = store_sales.ss_customer_sk
     AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
   GROUP BY customer.c_customer_id,
            customer.c_first_name,
            customer.c_last_name,
            customer.c_preferred_cust_flag,
            customer.c_birth_country,
            customer.c_login,
            customer.c_email_address,
            date_dim.d_year
   UNION ALL SELECT customer.c_customer_id customer_id,
                    customer.c_first_name customer_first_name,
                    customer.c_last_name customer_last_name,
                    customer.c_preferred_cust_flag customer_preferred_cust_flag,
                    customer.c_birth_country customer_birth_country,
                    customer.c_login customer_login,
                    customer.c_email_address customer_email_address,
                    date_dim.d_year dyear,
                    sum((((catalog_sales.cs_ext_list_price-catalog_sales.cs_ext_wholesale_cost-catalog_sales.cs_ext_discount_amt)+catalog_sales.cs_ext_sales_price)/2)) year_total,
                    'c' sale_type
   FROM dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE customer.c_customer_sk = catalog_sales.cs_bill_customer_sk
     AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
   GROUP BY customer.c_customer_id,
            customer.c_first_name,
            customer.c_last_name,
            customer.c_preferred_cust_flag,
            customer.c_birth_country,
            customer.c_login,
            customer.c_email_address,
            date_dim.d_year
   UNION ALL SELECT customer.c_customer_id customer_id,
                    customer.c_first_name customer_first_name,
                    customer.c_last_name customer_last_name,
                    customer.c_preferred_cust_flag customer_preferred_cust_flag,
                    customer.c_birth_country customer_birth_country,
                    customer.c_login customer_login,
                    customer.c_email_address customer_email_address,
                    date_dim.d_year dyear,
                    sum((((web_sales.ws_ext_list_price-web_sales.ws_ext_wholesale_cost-web_sales.ws_ext_discount_amt)+web_sales.ws_ext_sales_price)/2)) year_total,
                    'w' sale_type
   FROM dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE customer.c_customer_sk = web_sales.ws_bill_customer_sk
     AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
   GROUP BY customer.c_customer_id,
            customer.c_first_name,
            customer.c_last_name,
            customer.c_preferred_cust_flag,
            customer.c_birth_country,
            customer.c_login,
            customer.c_email_address,
            date_dim.d_year)
SELECT t_s_secyear.customer_id,
       t_s_secyear.customer_first_name,
       t_s_secyear.customer_last_name,
       t_s_secyear.customer_preferred_cust_flag
FROM year_total t_s_firstyear,
     year_total t_s_secyear,
     year_total t_c_firstyear,
     year_total t_c_secyear,
     year_total t_w_firstyear,
     year_total t_w_secyear
WHERE t_s_secyear.customer_id = t_s_firstyear.customer_id
  AND t_s_firstyear.customer_id = t_c_secyear.customer_id
  AND t_s_firstyear.customer_id = t_c_firstyear.customer_id
  AND t_s_firstyear.customer_id = t_w_firstyear.customer_id
  AND t_s_firstyear.customer_id = t_w_secyear.customer_id
  AND t_s_firstyear.sale_type = 's'
  AND t_c_firstyear.sale_type = 'c'
  AND t_w_firstyear.sale_type = 'w'
  AND t_s_secyear.sale_type = 's'
  AND t_c_secyear.sale_type = 'c'
  AND t_w_secyear.sale_type = 'w'
  AND t_s_firstyear.dyear = 2001
  AND t_s_secyear.dyear = 2001+1
  AND t_c_firstyear.dyear = 2001
  AND t_c_secyear.dyear = 2001+1
  AND t_w_firstyear.dyear = 2001
  AND t_w_secyear.dyear = 2001+1
  AND t_s_firstyear.year_total > 0
  AND t_c_firstyear.year_total > 0
  AND t_w_firstyear.year_total > 0
  AND CASE
          WHEN t_c_firstyear.year_total > 0 THEN t_c_secyear.year_total / t_c_firstyear.year_total
          ELSE NULL
      END > CASE
                WHEN t_s_firstyear.year_total > 0 THEN t_s_secyear.year_total / t_s_firstyear.year_total
                ELSE NULL
            END
  AND CASE
          WHEN t_c_firstyear.year_total > 0 THEN t_c_secyear.year_total / t_c_firstyear.year_total
          ELSE NULL
      END > CASE
                WHEN t_w_firstyear.year_total > 0 THEN t_w_secyear.year_total / t_w_firstyear.year_total
                ELSE NULL
            END
ORDER BY t_s_secyear.customer_id NULLS FIRST,
         t_s_secyear.customer_first_name NULLS FIRST,
         t_s_secyear.customer_last_name NULLS FIRST,
         t_s_secyear.customer_preferred_cust_flag NULLS FIRST
LIMIT 100;

