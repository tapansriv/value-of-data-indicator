WITH results AS
  (SELECT sum(store_sales.ss_net_profit) AS total_sum,
          store.s_state,
          store.s_county,
          0 AS gstate,
          0 AS g_county
   FROM dfs.`tmp/store_sales.parquet` AS store_sales ,
        dfs.`tmp/date_dim.parquet` d1 ,
        dfs.`tmp/store.parquet` AS store
   WHERE d1.d_month_seq BETWEEN 1200 AND 1200 + 11
     AND d1.d_date_sk = store_sales.ss_sold_date_sk
     AND store.s_store_sk = store_sales.ss_store_sk
     AND store.s_state IN
       (SELECT store.s_state
        FROM
          (SELECT store.s_state AS store.s_state,
                  rank() OVER (PARTITION BY store.s_state
                               ORDER BY sum(store_sales.ss_net_profit) DESC) AS ranking
           FROM dfs.`tmp/store_sales.parquet` AS store_sales,
                dfs.`tmp/store.parquet` AS store,
                dfs.`tmp/date_dim.parquet` AS date_dim
           WHERE date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11
             AND date_dim.d_date_sk = store_sales.ss_sold_date_sk
             AND store.s_store_sk = store_sales.ss_store_sk
           GROUP BY store.s_state ) tmp1
        WHERE ranking <= 5)
   GROUP BY store.s_state,
            store.s_county),
results_rollup AS
  (SELECT total_sum,
          store.s_state,
          store.s_county,
          0 AS g_state,
          0 AS g_county,
          0 AS lochierarchy
   FROM results
   UNION SELECT sum(total_sum) AS total_sum,
                store.s_state,
                NULL AS store.s_county,
                0 AS g_state,
                1 AS g_county,
                1 AS lochierarchy
   FROM results
   GROUP BY store.s_state
   UNION SELECT sum(total_sum) AS total_sum,
                NULL AS store.s_state,
                NULL AS store.s_county,
                1 AS g_state,
                1 AS g_county,
                2 AS lochierarchy
   FROM results)
SELECT total_sum,
       store.s_state,
       store.s_county,
       lochierarchy,
       rank() OVER ( PARTITION BY lochierarchy,
                                  CASE
                                      WHEN g_county = 0 THEN store.s_state
                                  END
                    ORDER BY total_sum DESC) AS rank_within_parent
FROM results_rollup
ORDER BY lochierarchy DESC ,
         CASE
             WHEN lochierarchy = 0 THEN store.s_state
         END ,
         rank_within_parent
LIMIT 100;

