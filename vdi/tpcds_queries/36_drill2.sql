WITH results AS
  (SELECT sum(store_sales.ss_net_profit) AS ss_net_profit,
          sum(store_sales.ss_ext_sales_price) AS ss_ext_sales_price,
          (sum(store_sales.ss_net_profit)*1.0000)/sum(store_sales.ss_ext_sales_price) AS gross_margin ,
          item.i_category ,
          item.i_class ,
          0 AS g_category,
          0 AS g_class
   FROM dfs.`tmp/store_sales.parquet` AS store_sales ,
        dfs.`tmp/date_dim.parquet` d1 ,
        dfs.`tmp/item.parquet` AS item ,
        dfs.`tmp/store.parquet` AS store
   WHERE d1.d_year = 2001
     AND d1.d_date_sk = store_sales.ss_sold_date_sk
     AND item.i_item_sk = store_sales.ss_item_sk
     AND store.s_store_sk = store_sales.ss_store_sk
     AND store.s_state ='TN'
   GROUP BY item.i_category,
            item.i_class),
results_rollup AS
  (SELECT gross_margin,
          i_category,
          i_class,
          0 AS t_category,
          0 AS t_class,
          0 AS lochierarchy
   FROM results
   -- UNION SELECT (sum(ss_net_profit)*1.0000)/sum(ss_ext_sales_price) AS gross_margin,
   --              i_category,
   --              NULL AS i_class,
   --              0 AS t_category,
   --              1 AS t_class,
   --              1 AS lochierarchy
   -- FROM results
   -- GROUP BY i_category
   -- UNION SELECT (sum(ss_net_profit)*1.0000)/sum(ss_ext_sales_price) AS gross_margin,
   --              NULL AS i_category,
   --              NULL AS i_class,
   --              1 AS t_category,
   --              1 AS t_class,
   --              2 AS lochierarchy
   -- FROM results
   )
SELECT gross_margin,
       i_category,
       i_class,
       lochierarchy,
       rank() OVER ( PARTITION BY lochierarchy,
                                  CASE
                                      WHEN t_class = 0 THEN i_category
                                  END
                    ORDER BY gross_margin ASC) AS rank_within_parent
FROM results_rollup
ORDER BY lochierarchy DESC NULLS FIRST,
         CASE
             WHEN lochierarchy = 0 THEN i_category
         END NULLS FIRST,
         rank_within_parent NULLS FIRST
LIMIT 100;

