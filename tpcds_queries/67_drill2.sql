CREATE TABLE results AS
  (SELECT item.i_category,
          item.i_class,
          item.i_brand,
          item.i_product_name,
          date_dim.d_year,
          date_dim.d_qoy,
          date_dim.d_moy,
          store.s_store_id ,
          sum(coalesce(store_sales.ss_sales_price*ss_quantity,0)) sumsales
   FROM dfs.`tmp/store_sales.parquet`,
        dfs.`tmp/date_dim.parquet`,
        dfs.`tmp/store.parquet`,
        dfs.`tmp/item.parquet`
   WHERE store_sales.ss_sold_date_sk=d_date_sk
     AND store_sales.ss_item_sk=i_item_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11
   GROUP BY item.i_category,
            item.i_class,
            item.i_brand,
            item.i_product_name,
            date_dim.d_year,
            date_dim.d_qoy,
            date_dim.d_moy,
            store.s_store_id);
CREATE TABLE results_rollup AS
  (SELECT item.i_category,
          item.i_class,
          item.i_brand,
          item.i_product_name,
          date_dim.d_year,
          date_dim.d_qoy,
          date_dim.d_moy,
          store.s_store_id,
          sumsales
   FROM results
   UNION ALL SELECT item.i_category,
                    item.i_class,
                    item.i_brand,
                    item.i_product_name,
                    date_dim.d_year,
                    date_dim.d_qoy,
                    date_dim.d_moy,
                    NULL store.s_store_id,
                         sum(sumsales) sumsales
   FROM results
   GROUP BY item.i_category,
            item.i_class,
            item.i_brand,
            item.i_product_name,
            date_dim.d_year,
            date_dim.d_qoy,
            date_dim.d_moy
   UNION ALL SELECT item.i_category,
                    item.i_class,
                    item.i_brand,
                    item.i_product_name,
                    date_dim.d_year,
                    date_dim.d_qoy,
                    NULL date_dim.d_moy,
                         NULL store.s_store_id,
                              sum(sumsales) sumsales
   FROM results
   GROUP BY item.i_category,
            item.i_class,
            item.i_brand,
            item.i_product_name,
            date_dim.d_year,
            date_dim.d_qoy
   UNION ALL SELECT item.i_category,
                    item.i_class,
                    item.i_brand,
                    item.i_product_name,
                    date_dim.d_year,
                    NULL date_dim.d_qoy,
                         NULL date_dim.d_moy,
                              NULL store.s_store_id,
                                   sum(sumsales) sumsales
   FROM results
   GROUP BY item.i_category,
            item.i_class,
            item.i_brand,
            item.i_product_name,
            date_dim.d_year
   UNION ALL SELECT item.i_category,
                    item.i_class,
                    item.i_brand,
                    item.i_product_name,
                    NULL date_dim.d_year,
                         NULL date_dim.d_qoy,
                              NULL date_dim.d_moy,
                                   NULL store.s_store_id,
                                        sum(sumsales) sumsales
   FROM results
   GROUP BY item.i_category,
            item.i_class,
            item.i_brand,
            item.i_product_name
   UNION ALL SELECT item.i_category,
                    item.i_class,
                    item.i_brand,
                    NULL item.i_product_name,
                         NULL date_dim.d_year,
                              NULL date_dim.d_qoy,
                                   NULL date_dim.d_moy,
                                        NULL store.s_store_id,
                                             sum(sumsales) sumsales
   FROM results
   GROUP BY item.i_category,
            item.i_class,
            item.i_brand
   UNION ALL SELECT item.i_category,
                    item.i_class,
                    NULL item.i_brand,
                         NULL item.i_product_name,
                              NULL date_dim.d_year,
                                   NULL date_dim.d_qoy,
                                        NULL date_dim.d_moy,
                                             NULL store.s_store_id,
                                                  sum(sumsales) sumsales
   FROM results
   GROUP BY item.i_category,
            item.i_class
   UNION ALL SELECT item.i_category,
                    NULL item.i_class,
                         NULL item.i_brand,
                              NULL item.i_product_name,
                                   NULL date_dim.d_year,
                                        NULL date_dim.d_qoy,
                                             NULL date_dim.d_moy,
                                                  NULL store.s_store_id,
                                                       sum(sumsales) sumsales
   FROM results
   GROUP BY item.i_category
   UNION ALL SELECT NULL item.i_category,
                         NULL item.i_class,
                              NULL item.i_brand,
                                   NULL item.i_product_name,
                                        NULL date_dim.d_year,
                                             NULL date_dim.d_qoy,
                                                  NULL date_dim.d_moy,
                                                       NULL store.s_store_id,
                                                            sum(sumsales) sumsales
   FROM results);
SELECT *
FROM
  (SELECT item.i_category ,
          item.i_class ,
          item.i_brand ,
          item.i_product_name ,
          date_dim.d_year ,
          date_dim.d_qoy ,
          date_dim.d_moy ,
          store.s_store_id ,
          sumsales ,
          rank() OVER (PARTITION BY item.i_category
                       ORDER BY sumsales DESC) rk
   FROM results_rollup) dw2
WHERE rk <= 100
ORDER BY item.i_category NULLS LAST,
         item.i_class NULLS LAST,
         item.i_brand NULLS LAST,
         item.i_product_name NULLS LAST,
         date_dim.d_year NULLS LAST,
         date_dim.d_qoy NULLS LAST,
         date_dim.d_moy NULLS LAST,
         store.s_store_id NULLS LAST,
         sumsales NULLS LAST,
         rk NULLS LAST
LIMIT 100;

