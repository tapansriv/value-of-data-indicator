
SELECT * from
  (SELECT item.i_category, item.i_class, item.i_brand, store.s_store_name, store.s_company_name, date_dim.d_moy, sum(store_sales.ss_sales_price) sum_sales, avg(sum(store_sales.ss_sales_price)) OVER (PARTITION BY item.i_category, item.i_brand, store.s_store_name, store.s_company_name) avg_monthly_sales
   FROM dfs.`tmp/item.parquet`, dfs.`tmp/store_sales.parquet`, dfs.`tmp/date_dim.parquet`, dfs.`tmp/store.parquet`  
   WHERE store_sales.ss_item_sk = item.i_item_sk
     AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND date_dim.d_year = 1999
     AND ((item.i_category IN ('Books','Electronics','Sports')
           AND item.i_class IN ('computers','stereo','football') )
          OR (item.i_category IN ('Men','Jewelry','Women')
              AND item.i_class IN ('shirts','birdal','dresses')))
   GROUP BY item.i_category, item.i_class, item.i_brand, store.s_store_name, store.s_company_name, date_dim.d_moy) tmp1
WHERE CASE
          WHEN (avg_monthly_sales <> 0) THEN (abs(sum_sales - avg_monthly_sales) / avg_monthly_sales)
          ELSE NULL
      END > 0.1
ORDER BY sum_sales - avg_monthly_sales,
         store.s_store_name, 1, 2, 3, 5, 6, 7, 8
LIMIT 100;

