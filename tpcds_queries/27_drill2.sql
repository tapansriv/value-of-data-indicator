WITH results AS
  (SELECT item.i_item_id,
          store.s_state,
          0 AS g_state,
          store_sales.ss_quantity agg1,
          store_sales.ss_list_price agg2,
          store_sales.ss_coupon_amt agg3,
          store_sales.ss_sales_price agg4
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/customer_demographics.parquet` AS customer_demographics,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/item.parquet` AS item
   WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND store_sales.ss_item_sk = item.i_item_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND store_sales.ss_cdemo_sk = customer_demographics.cd_demo_sk
     AND customer_demographics.cd_gender = 'M'
     AND customer_demographics.cd_marital_status = 'S'
     AND customer_demographics.cd_education_status = 'College'
     AND date_dim.d_year = 2002
     AND store.s_state = 'TN' )
SELECT i_item_id,
       s_state,
       g_state,
       agg1,
       agg2,
       agg3,
       agg4
FROM results
  -- ( SELECT item.i_item_id,
  --          store.s_state,
  --          0 AS g_state,
  --          avg(agg1) agg1,
  --          avg(agg2) agg2,
  --          avg(agg3) agg3,
  --          avg(agg4) agg4
  --  FROM results
  --  GROUP BY item.i_item_id ,
  --           store.s_state
  --  UNION ALL SELECT item.i_item_id,
  --                   NULL AS store.s_state,
  --                   1 AS g_state,
  --                   avg(agg1) agg1,
  --                   avg(agg2) agg2,
  --                   avg(agg3) agg3,
  --                   avg(agg4) agg4
  --  FROM results
  --  GROUP BY item.i_item_id
  --  UNION ALL SELECT NULL AS item.i_item_id,
  --                   NULL AS store.s_state,
  --                   1 AS g_state,
  --                   avg(agg1) agg1,
  --                   avg(agg2) agg2,
  --                   avg(agg3) agg3,
  --                   avg(agg4) agg4
  --  FROM results ) foo
ORDER BY i_item_id NULLS FIRST,
         s_state NULLS FIRST
LIMIT 100;
