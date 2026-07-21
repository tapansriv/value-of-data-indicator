WITH customer_total_return AS
  (SELECT store_returns.sr_customer_sk AS ctr_customer_sk,
          store_returns.sr_store_sk AS ctr_store_sk,
          sum(store_returns.sr_return_amt) AS ctr_total_return
   FROM dfs.`tmp/store_returns.parquet` AS store_returns,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE store_returns.sr_returned_date_sk = date_dim.d_date_sk
     AND date_dim.d_year = 2000
   GROUP BY store_returns.sr_customer_sk,
            store_returns.sr_store_sk)
SELECT customer.c_customer_id
FROM customer_total_return ctr1,
     dfs.`tmp/store.parquet` AS store,
     dfs.`tmp/customer.parquet` AS customer
WHERE ctr1.ctr_total_return >
    (SELECT avg(ctr_total_return)*1.2
     FROM customer_total_return ctr2
     WHERE ctr1.ctr_store_sk = ctr2.ctr_store_sk)
  AND store.s_store_sk = ctr1.ctr_store_sk
  AND store.s_state = 'TN'
  AND ctr1.ctr_customer_sk = customer.c_customer_sk
ORDER BY customer.c_customer_id
LIMIT 100;

