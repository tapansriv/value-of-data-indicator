WITH frequent_ss_items AS
  (SELECT sq1.itemdesc,
          sq1.i_item_sk item_sk,
          date_dim.d_date solddate,
          count(*) cnt
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
     (SELECT SUBSTRING(item.i_item_desc, 1, 30) itemdesc,
             *
      FROM dfs.`tmp/item.parquet` AS item) sq1
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_item_sk = sq1.i_item_sk
     AND date_dim.d_year IN (2000,
                    2000+1,
                    2000+2,
                    2000+3)
   GROUP BY sq1.itemdesc,
            sq1.i_item_sk,
            date_dim.d_date
   HAVING count(*) >4),
max_store_sales AS
  (SELECT max(csales) tpcds_cmax
   FROM
     (SELECT customer.c_customer_sk,
             sum(store_sales.ss_quantity*store_sales.ss_sales_price) csales
      FROM dfs.`tmp/store_sales.parquet` AS store_sales,
           dfs.`tmp/customer.parquet` AS customer,
           dfs.`tmp/date_dim.parquet` AS date_dim
      WHERE store_sales.ss_customer_sk = customer.c_customer_sk
        AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
        AND date_dim.d_year IN (2000,
                       2000+1,
                       2000+2,
                       2000+3)
      GROUP BY customer.c_customer_sk) sq2),
best_ss_customer AS
  (SELECT customer.c_customer_sk,
          sum(store_sales.ss_quantity*store_sales.ss_sales_price) ssales
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/customer.parquet` AS customer,
        max_store_sales
   WHERE store_sales.ss_customer_sk = customer.c_customer_sk
   GROUP BY customer.c_customer_sk
   HAVING sum(store_sales.ss_quantity*store_sales.ss_sales_price) > (50/100.0) * max(max_store_sales.tpcds_cmax))
SELECT sq3.c_last_name,
       sq3.c_first_name,
       sq3.sales
FROM
  (SELECT customer.c_last_name,
          customer.c_first_name,
          sum(catalog_sales.cs_quantity*catalog_sales.cs_list_price) sales
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        frequent_ss_items,
        best_ss_customer
   WHERE date_dim.d_year = 2000
     AND date_dim.d_moy = 2
     AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
     AND catalog_sales.cs_item_sk = frequent_ss_items.item_sk
     AND catalog_sales.cs_bill_customer_sk = best_ss_customer.c_customer_sk
     AND catalog_sales.cs_bill_customer_sk = customer.c_customer_sk
   GROUP BY customer.c_last_name,
            customer.c_first_name
   UNION ALL SELECT customer.c_last_name,
                    customer.c_first_name,
                    sum(web_sales.ws_quantity*web_sales.ws_list_price) sales
   FROM dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        frequent_ss_items,
        best_ss_customer
   WHERE date_dim.d_year = 2000
     AND date_dim.d_moy = 2
     AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
     AND web_sales.ws_item_sk = frequent_ss_items.item_sk
     AND web_sales.ws_bill_customer_sk = best_ss_customer.c_customer_sk
     AND web_sales.ws_bill_customer_sk = customer.c_customer_sk
   GROUP BY customer.c_last_name,
            customer.c_first_name) sq3
ORDER BY sq3.c_last_name NULLS FIRST,
         sq3.c_first_name NULLS FIRST,
         sq3.sales NULLS FIRST
LIMIT 100;
