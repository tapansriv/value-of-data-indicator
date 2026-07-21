WITH v1 AS
  (SELECT item.i_category,
          item.i_brand,
          store.s_store_name,
          store.s_company_name,
          date_dim.d_year,
          date_dim.d_moy,
          sum(store_sales.ss_sales_price) sum_sales,
          avg(sum(store_sales.ss_sales_price)) OVER (PARTITION BY item.i_category,
                                                      item.i_brand,
                                                      store.s_store_name,
                                                      store.s_company_name,
                                                      date_dim.d_year) avg_monthly_sales,
                                        rank() OVER (PARTITION BY item.i_category,
                                                                  item.i_brand,
                                                                  store.s_store_name,
                                                                  store.s_company_name
                                                     ORDER BY date_dim.d_year,
                                                              date_dim.d_moy) rn
   FROM dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store
   WHERE store_sales.ss_item_sk = item.i_item_sk
     AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND (date_dim.d_year = 1999
          OR (date_dim.d_year = 1999-1
              AND date_dim.d_moy =12)
          OR (date_dim.d_year = 1999+1
              AND date_dim.d_moy =1))
   GROUP BY item.i_category,
            item.i_brand,
            store.s_store_name,
            store.s_company_name,
            date_dim.d_year,
            date_dim.d_moy),
v2 AS
  (SELECT v1.i_category,
          v1.i_brand,
          v1.s_store_name,
          v1.s_company_name,
          v1.d_year,
          v1.d_moy,
          v1.avg_monthly_sales,
          v1.sum_sales,
          v1_lag.sum_sales psum,
          v1_lead.sum_sales nsum
   FROM v1,
        v1 v1_lag,
        v1 v1_lead
   WHERE v1.i_category = v1_lag.i_category
     AND v1.i_category = v1_lead.i_category
     AND v1.i_brand = v1_lag.i_brand
     AND v1.i_brand = v1_lead.i_brand
     AND v1.s_store_name = v1_lag.s_store_name
     AND v1.s_store_name = v1_lead.s_store_name
     AND v1.s_company_name = v1_lag.s_company_name
     AND v1.s_company_name = v1_lead.s_company_name
     AND v1.rn = v1_lag.rn + 1
     AND v1.rn = v1_lead.rn - 1)
SELECT *
FROM v2
WHERE d_year = 1999
  AND avg_monthly_sales > 0
  AND CASE
          WHEN avg_monthly_sales > 0 THEN abs(sum_sales - avg_monthly_sales) / avg_monthly_sales
          ELSE NULL
      END > 0.1
ORDER BY sum_sales - avg_monthly_sales, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
LIMIT 100;

