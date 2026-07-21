SELECT store_sales.ss_customer_sk,
       sum(act_sales) sumsales
FROM
  (SELECT store_sales.ss_item_sk,
          store_sales.ss_ticket_number,
          store_sales.ss_customer_sk,
          CASE
              WHEN store_returns.sr_return_quantity IS NOT NULL THEN (store_sales.ss_quantity-sr_return_quantity)*ss_sales_price
              ELSE (store_sales.ss_quantity*ss_sales_price)
          END act_sales
   FROM dfs.`tmp/store_sales.parquet` AS store_sales
   LEFT OUTER JOIN dfs.`tmp/store_returns.parquet` AS store_returns ON (store_returns.sr_item_sk = store_sales.ss_item_sk
                                     AND store_returns.sr_ticket_number = store_sales.ss_ticket_number) ,dfs.`tmp/reason.parquet` AS reason
   WHERE store_returns.sr_reason_sk = reason.r_reason_sk
     AND reason.r_reason_desc = 'reason 28') t
GROUP BY store_sales.ss_customer_sk
ORDER BY sumsales NULLS FIRST,
         store_sales.ss_customer_sk NULLS FIRST
LIMIT 100;

