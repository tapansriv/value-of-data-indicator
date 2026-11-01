SELECT a.ca_state state,
       count(*) cnt
FROM 's3://vod-tpcds-10gb/customer_address.parquet' a ,
     's3://vod-tpcds-10gb/customer.parquet' c ,
     's3://vod-tpcds-10gb/store_sales.parquet' s ,
     's3://vod-tpcds-10gb/date_dim.parquet' d ,
     's3://vod-tpcds-10gb/item.parquet' i
WHERE a.ca_address_sk = c.c_current_addr_sk
  AND c.c_customer_sk = s.ss_customer_sk
  AND s.ss_sold_date_sk = d.d_date_sk
  AND s.ss_item_sk = i.i_item_sk
  AND d.d_month_seq =
    (SELECT DISTINCT (d_month_seq)
     FROM 's3://vod-tpcds-10gb/date_dim.parquet' AS date_dim
     WHERE d_year = 2001
       AND d_moy = 1 )
  AND i.i_current_price > 1.2 *
    (SELECT avg(j.i_current_price)
     FROM 's3://vod-tpcds-10gb/item.parquet' j
     WHERE j.i_category = i.i_category)
GROUP BY a.ca_state
HAVING count(*) >= 10
ORDER BY cnt NULLS FIRST,
         a.ca_state NULLS FIRST
LIMIT 100;

