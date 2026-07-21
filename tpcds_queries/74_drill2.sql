WITH year_total AS
  (SELECT customer.c_customer_id customer_id,
          customer.c_first_name customer_first_name,
          customer.c_last_name customer_last_name,
          date_dim.d_year AS year_,
          sum(store_sales.ss_net_paid) year_total,
          's' sale_type
   FROM dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE customer.c_customer_sk = store_sales.ss_customer_sk
     AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_year IN (2001,
                    2001+1)
   GROUP BY customer.c_customer_id,
            customer.c_first_name,
            customer.c_last_name,
            date_dim.d_year
   UNION ALL SELECT customer.c_customer_id customer_id,
                    customer.c_first_name customer_first_name,
                    customer.c_last_name customer_last_name,
                    date_dim.d_year AS year_,
                    sum(web_sales.ws_net_paid) year_total,
                    'w' sale_type
   FROM dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE customer.c_customer_sk = web_sales.ws_bill_customer_sk
     AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_year IN (2001,
                    2001+1)
   GROUP BY customer.c_customer_id,
            customer.c_first_name,
            customer.c_last_name,
            date_dim.d_year)
SELECT t_s_secyear.customer_id,
       t_s_secyear.customer_first_name,
       t_s_secyear.customer_last_name
FROM year_total t_s_firstyear,
     year_total t_s_secyear,
     year_total t_w_firstyear,
     year_total t_w_secyear
WHERE t_s_secyear.customer_id = t_s_firstyear.customer_id
  AND t_s_firstyear.customer_id = t_w_secyear.customer_id
  AND t_s_firstyear.customer_id = t_w_firstyear.customer_id
  AND t_s_firstyear.sale_type = 's'
  AND t_w_firstyear.sale_type = 'w'
  AND t_s_secyear.sale_type = 's'
  AND t_w_secyear.sale_type = 'w'
  AND t_s_firstyear.year_ = 2001
  AND t_s_secyear.year_ = 2001+1
  AND t_w_firstyear.year_ = 2001
  AND t_w_secyear.year_ = 2001+1
  AND t_s_firstyear.year_total > 0
  AND t_w_firstyear.year_total > 0
  AND CASE
          WHEN t_w_firstyear.year_total > 0 THEN t_w_secyear.year_total / t_w_firstyear.year_total
          ELSE NULL
      END > CASE
                WHEN t_s_firstyear.year_total > 0 THEN t_s_secyear.year_total / t_s_firstyear.year_total
                ELSE NULL
            END
ORDER BY 1 NULLS FIRST
LIMIT 100;

