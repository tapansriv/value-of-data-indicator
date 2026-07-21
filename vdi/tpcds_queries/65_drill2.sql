SELECT store.s_store_name,
       item.i_item_desc,
       sc.revenue,
       item.i_current_price,
       item.i_wholesale_cost,
       item.i_brand
FROM dfs.`tmp/store.parquet` AS store,
     dfs.`tmp/item.parquet` AS item,
  (SELECT store_sales.ss_store_sk,
          avg(revenue) AS ave
   FROM
     (SELECT store_sales.ss_store_sk,
             store_sales.ss_item_sk,
             sum(store_sales.ss_sales_price) AS revenue
      FROM dfs.`tmp/store_sales.parquet` AS store_sales,
           dfs.`tmp/date_dim.parquet` AS date_dim
      WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
        AND date_dim.d_month_seq BETWEEN 1176 AND 1176+11
      GROUP BY store_sales.ss_store_sk,
               store_sales.ss_item_sk) sa
   GROUP BY store_sales.ss_store_sk) sb,
  (SELECT store_sales.ss_store_sk,
          store_sales.ss_item_sk,
          sum(store_sales.ss_sales_price) AS revenue
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_month_seq BETWEEN 1176 AND 1176+11
   GROUP BY store_sales.ss_store_sk,
            store_sales.ss_item_sk) sc
WHERE sb.ss_store_sk = sc.ss_store_sk
  AND sc.revenue <= 0.1 * sb.ave
  AND store.s_store_sk = sc.ss_store_sk
  AND item.i_item_sk = sc.ss_item_sk
ORDER BY store.s_store_name NULLS FIRST,
         item.i_item_desc NULLS FIRST
LIMIT 100;

