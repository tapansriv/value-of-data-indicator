CREATE TABLE results AS
  (SELECT i_item_id,
          s_state,
          0 AS g_state,
          ss_quantity agg1,
          ss_list_price agg2,
          ss_coupon_amt agg3,
          ss_sales_price agg4
   FROM 's3://vod-tpcds-10gb/store_sales.parquet' AS store_sales,
        's3://vod-tpcds-10gb/customer_demographics.parquet' AS customer_demographics,
        's3://vod-tpcds-10gb/date_dim.parquet' AS date_dim,
        's3://vod-tpcds-10gb/store.parquet' AS store,
        's3://vod-tpcds-10gb/item.parquet' AS item
   WHERE ss_sold_date_sk = d_date_sk
     AND ss_item_sk = i_item_sk
     AND ss_store_sk = s_store_sk
     AND ss_cdemo_sk = cd_demo_sk
     AND cd_gender = 'M'
     AND cd_marital_status = 'S'
     AND cd_education_status = 'College'
     AND d_year = 2002
     AND s_state = 'TN' );
SELECT i_item_id,
       s_state,
       g_state,
       agg1,
       agg2,
       agg3,
       agg4
FROM
  ( SELECT i_item_id,
           s_state,
           0 AS g_state,
           avg(agg1) agg1,
           avg(agg2) agg2,
           avg(agg3) agg3,
           avg(agg4) agg4
   FROM results
   GROUP BY i_item_id ,
            s_state
   UNION ALL SELECT i_item_id,
                    NULL AS s_state,
                    1 AS g_state,
                    avg(agg1) agg1,
                    avg(agg2) agg2,
                    avg(agg3) agg3,
                    avg(agg4) agg4
   FROM results
   GROUP BY i_item_id
   UNION ALL SELECT NULL AS i_item_id,
                    NULL AS s_state,
                    1 AS g_state,
                    avg(agg1) agg1,
                    avg(agg2) agg2,
                    avg(agg3) agg3,
                    avg(agg4) agg4
   FROM results ) foo
ORDER BY i_item_id NULLS FIRST,
         s_state NULLS FIRST
LIMIT 100;
