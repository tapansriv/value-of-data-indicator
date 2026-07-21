
SELECT *
FROM
  (SELECT item.i_manager_id,
          sum(store_sales.ss_sales_price) sum_sales,
          avg(sum(store_sales.ss_sales_price)) OVER (PARTITION BY item.i_manager_id) avg_monthly_sales
   FROM dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store
   WHERE store_sales.ss_item_sk = item.i_item_sk
     AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND date_dim.d_month_seq IN (1200,
                         1200+1,
                         1200+2,
                         1200+3,
                         1200+4,
                         1200+5,
                         1200+6,
                         1200+7,
                         1200+8,
                         1200+9,
                         1200+10,
                         1200+11)
     AND ((item.i_category IN ('Books',
                          'Children',
                          'Electronics')
           AND item.i_class IN ('personal',
                           'portable',
                           'reference',
                           'self-help')
           AND item.i_brand IN ('scholaramalgamalg #14',
                           'scholaramalgamalg #7',
                           'exportiunivamalg #9',
                           'scholaramalgamalg #9')) or(item.i_category IN ('Women','Music','Men')
                                                       AND item.i_class IN ('accessories','classical','fragrances','pants')
                                                       AND item.i_brand IN ('amalgimporto #1','edu packscholar #1','exportiimporto #1', 'importoamalg #1')))
   GROUP BY item.i_manager_id,
            date_dim.d_moy) tmp1
WHERE CASE
          WHEN avg_monthly_sales > 0 THEN ABS (sum_sales - avg_monthly_sales) / avg_monthly_sales
          ELSE NULL
      END > 0.1
ORDER BY item.i_manager_id,
         avg_monthly_sales,
         sum_sales
LIMIT 100;

