WITH my_customers AS
  (SELECT DISTINCT customer.c_customer_sk,
                   customer.c_current_addr_sk
   FROM
     (SELECT catalog_sales.cs_sold_date_sk sold_date_sk,
             catalog_sales.cs_bill_customer_sk customer_sk,
             catalog_sales.cs_item_sk item_sk
      FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales
      UNION ALL SELECT web_sales.ws_sold_date_sk sold_date_sk,
                       web_sales.ws_bill_customer_sk customer_sk,
                       web_sales.ws_item_sk item_sk
      FROM dfs.`tmp/web_sales.parquet` AS web_sales) cs_or_ws_sales,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer.parquet` AS customer
   WHERE sold_date_sk = date_dim.d_date_sk
     AND item_sk = item.i_item_sk
     AND item.i_category = 'Women'
     AND item.i_class = 'maternity'
     AND customer.c_customer_sk = cs_or_ws_sales.customer_sk
     AND date_dim.d_moy = 12
     AND date_dim.d_year = 1998 ),
my_revenue AS
  (SELECT customer.c_customer_sk,
          sum(store_sales.ss_ext_sales_price) AS revenue
   FROM my_customers,
        dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/customer_address.parquet` AS customer_address,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE customer.c_current_addr_sk = customer_address.ca_address_sk
     AND customer_address.ca_county = store.s_county
     AND customer_address.ca_state = store.s_state
     AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND customer.c_customer_sk = store_sales.ss_customer_sk
     AND date_dim.d_month_seq BETWEEN
       (SELECT DISTINCT date_dim.d_month_seq+1
        FROM dfs.`tmp/date_dim.parquet` AS date_dim
        WHERE date_dim.d_year = 1998
          AND date_dim.d_moy = 12) AND
       (SELECT DISTINCT date_dim.d_month_seq+3
        FROM dfs.`tmp/date_dim.parquet` AS date_dim
        WHERE date_dim.d_year = 1998
          AND date_dim.d_moy = 12)
   GROUP BY customer.c_customer_sk),
segments AS
  (SELECT cast(round(revenue/50) AS int) AS SEGMENT
   FROM my_revenue)
SELECT SEGMENT,
       count(*) AS num_customers,
       SEGMENT*50 AS segment_base
FROM segments
GROUP BY SEGMENT
ORDER BY SEGMENT NULLS FIRST,
         num_customers NULLS FIRST,
         segment_base
LIMIT 100;

