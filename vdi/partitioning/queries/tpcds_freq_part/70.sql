WITH results AS (
    SELECT
      SUM(ss_net_profit) AS total_sum,
      s_state,
      s_county,
      0 AS gstate,
      0 AS g_county
    FROM READ_PARQUET('/home/cc/tpcds_partitioned_freq/store_sales/**/*.parquet', hive_partitioning = 1) AS store_sales, READ_PARQUET('/home/cc/tpcds_partitioned_freq/date_dim/**/*.parquet', hive_partitioning = 1) AS d1, READ_PARQUET('store.parquet') AS store
    WHERE
      d1.d_month_seq BETWEEN 1200 AND 1200 + 11
      AND d1.d_date_sk = ss_sold_date_sk
      AND s_store_sk = ss_store_sk
      AND s_state IN (
          SELECT
            s_state
          FROM (
              SELECT
                s_state AS s_state,
                RANK() OVER (PARTITION BY s_state ORDER BY SUM(ss_net_profit) DESC) AS ranking
              FROM READ_PARQUET('/home/cc/tpcds_partitioned_freq/store_sales/**/*.parquet', hive_partitioning = 1) AS store_sales, READ_PARQUET('store.parquet') AS store, READ_PARQUET('/home/cc/tpcds_partitioned_freq/date_dim/**/*.parquet', hive_partitioning = 1) AS date_dim
              WHERE
                d_month_seq BETWEEN 1200 AND 1200 + 11
                AND d_date_sk = ss_sold_date_sk
                AND s_store_sk = ss_store_sk
              GROUP BY
                s_state
          ) AS tmp1
          WHERE
            ranking <= 5
      )
    GROUP BY
      s_state,
      s_county
), results_rollup AS (
    SELECT
      total_sum,
      s_state,
      s_county,
      0 AS g_state,
      0 AS g_county,
      0 AS lochierarchy
    FROM results
    UNION
    SELECT
      SUM(total_sum) AS total_sum,
      s_state,
      NULL AS s_county,
      0 AS g_state,
      1 AS g_county,
      1 AS lochierarchy
    FROM results
    GROUP BY
      s_state
    UNION
    SELECT
      SUM(total_sum) AS total_sum,
      NULL AS s_state,
      NULL AS s_county,
      1 AS g_state,
      1 AS g_county,
      2 AS lochierarchy
    FROM results
)
SELECT
  total_sum,
  s_state,
  s_county,
  lochierarchy,
  RANK() OVER (PARTITION BY lochierarchy, CASE WHEN g_county = 0 THEN s_state END ORDER BY total_sum DESC) AS rank_within_parent
FROM results_rollup
ORDER BY
  lochierarchy DESC,
  CASE WHEN lochierarchy = 0 THEN s_state END,
  rank_within_parent
LIMIT 100