WITH wss AS
  (SELECT date_dim.d_week_seq,
          store_sales.ss_store_sk,
          sum(CASE
                  WHEN (date_dim.d_day_name='Sunday') THEN store_sales.ss_sales_price
                  ELSE NULL
              END) sun_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Monday') THEN store_sales.ss_sales_price
                  ELSE NULL
              END) mon_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Tuesday') THEN store_sales.ss_sales_price
                  ELSE NULL
              END) tue_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Wednesday') THEN store_sales.ss_sales_price
                  ELSE NULL
              END) wed_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Thursday') THEN store_sales.ss_sales_price
                  ELSE NULL
              END) thu_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Friday') THEN store_sales.ss_sales_price
                  ELSE NULL
              END) fri_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Saturday') THEN store_sales.ss_sales_price
                  ELSE NULL
              END) sat_sales
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE date_dim.d_date_sk = store_sales.ss_sold_date_sk
   GROUP BY date_dim.d_week_seq,
            store_sales.ss_store_sk)
SELECT store.s_store_name1,
       store.s_store_id1,
       date_dim.d_week_seq1,
       sun_sales1/sun_sales2,
       mon_sales1/mon_sales2,
       tue_sales1/tue_sales2,
       wed_sales1/wed_sales2,
       thu_sales1/thu_sales2,
       fri_sales1/fri_sales2,
       sat_sales1/sat_sales2
FROM
  (SELECT store.s_store_name store.s_store_name1,
          wss.d_week_seq date_dim.d_week_seq1,
          store.s_store_id store.s_store_id1,
          sun_sales sun_sales1,
          mon_sales mon_sales1,
          tue_sales tue_sales1,
          wed_sales wed_sales1,
          thu_sales thu_sales1,
          fri_sales fri_sales1,
          sat_sales sat_sales1
   FROM wss,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/date_dim.parquet` d
   WHERE d.d_week_seq = wss.d_week_seq
     AND store_sales.ss_store_sk = store.s_store_sk
     AND date_dim.d_month_seq BETWEEN 1212 AND 1212 + 11) y,
  (SELECT store.s_store_name store.s_store_name2,
          wss.d_week_seq date_dim.d_week_seq2,
          store.s_store_id store.s_store_id2,
          sun_sales sun_sales2,
          mon_sales mon_sales2,
          tue_sales tue_sales2,
          wed_sales wed_sales2,
          thu_sales thu_sales2,
          fri_sales fri_sales2,
          sat_sales sat_sales2
   FROM wss,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/date_dim.parquet` d
   WHERE d.d_week_seq = wss.d_week_seq
     AND store_sales.ss_store_sk = store.s_store_sk
     AND date_dim.d_month_seq BETWEEN 1212 + 12 AND 1212 + 23) x
WHERE store.s_store_id1=s_store_id2
  AND date_dim.d_week_seq1=d_week_seq2-52
ORDER BY store.s_store_name1 NULLS FIRST,
         store.s_store_id1 NULLS FIRST,
         date_dim.d_week_seq1 NULLS FIRST
LIMIT 100;

