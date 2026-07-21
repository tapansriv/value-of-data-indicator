CREATE TABLE frequent_ss_items AS
  (SELECT itemdesc,
          i_item_sk item_sk,
          d_date solddate,
          count(*) cnt
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
     (SELECT SUBSTRING(i_item_desc, 1, 30) itemdesc,
             *
      FROM dfs.`tmp/item.parquet` AS item) sq1
   WHERE ss_sold_date_sk = d_date_sk
     AND ss_item_sk = i_item_sk
     AND d_year IN (2000,
                    2000+1,
                    2000+2,
                    2000+3)
   GROUP BY itemdesc,
            i_item_sk,
            d_date
   HAVING count(*) >4);
CREATE TABLE max_store_sales AS
  (SELECT max(csales) tpcds_cmax
   FROM
     (SELECT c_customer_sk,
             sum(ss_quantity*ss_sales_price) csales
      FROM dfs.`tmp/store_sales.parquet` AS store_sales,
           dfs.`tmp/customer.parquet` AS customer,
           dfs.`tmp/date_dim.parquet` AS date_dim
      WHERE ss_customer_sk = c_customer_sk
        AND ss_sold_date_sk = d_date_sk
        AND d_year IN (2000,
                       2000+1,
                       2000+2,
                       2000+3)
      GROUP BY c_customer_sk) sq2);
CREATE TABLE best_ss_customer AS
  (SELECT c_customer_sk,
          sum(ss_quantity*ss_sales_price) ssales
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/customer.parquet` AS customer,
        max_store_sales
   WHERE ss_customer_sk = c_customer_sk
   GROUP BY c_customer_sk
   HAVING sum(ss_quantity*ss_sales_price) > (50/100.0) * max(tpcds_cmax));
SELECT c_last_name,
       c_first_name,
       sales
FROM
  (SELECT c_last_name,
          c_first_name,
          sum(cs_quantity*cs_list_price) sales
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        frequent_ss_items,
        best_ss_customer
   WHERE d_year = 2000
     AND d_moy = 2
     AND cs_sold_date_sk = d_date_sk
     AND cs_item_sk = item_sk
     AND cs_bill_customer_sk = best_ss_customer.c_customer_sk
     AND cs_bill_customer_sk = customer.c_customer_sk
   GROUP BY c_last_name,
            c_first_name
   UNION ALL SELECT c_last_name,
                    c_first_name,
                    sum(ws_quantity*ws_list_price) sales
   FROM dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        frequent_ss_items,
        best_ss_customer
   WHERE d_year = 2000
     AND d_moy = 2
     AND ws_sold_date_sk = d_date_sk
     AND ws_item_sk = item_sk
     AND ws_bill_customer_sk = best_ss_customer.c_customer_sk
     AND ws_bill_customer_sk = customer.c_customer_sk
   GROUP BY c_last_name,
            c_first_name) sq3
ORDER BY c_last_name NULLS FIRST,
         c_first_name NULLS FIRST,
         sales NULLS FIRST
LIMIT 100;
