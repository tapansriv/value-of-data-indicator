WITH wscs AS
  (SELECT sold_date_sk,
          sales_price
   FROM
     (SELECT web_sales.ws_sold_date_sk sold_date_sk,
             web_sales.ws_ext_sales_price sales_price
      FROM dfs.`tmp/web_sales.parquet` AS web_sales
      UNION ALL SELECT catalog_sales.cs_sold_date_sk sold_date_sk,
                       catalog_sales.cs_ext_sales_price sales_price
      FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales) sq1),
wswscs AS
  (SELECT date_dim.d_week_seq,
          sum(CASE
                  WHEN (date_dim.d_day_name='Sunday') THEN wscs.sales_price
                  ELSE NULL
              END) sun_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Monday') THEN wscs.sales_price
                  ELSE NULL
              END) mon_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Tuesday') THEN wscs.sales_price
                  ELSE NULL
              END) tue_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Wednesday') THEN wscs.sales_price
                  ELSE NULL
              END) wed_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Thursday') THEN wscs.sales_price
                  ELSE NULL
              END) thu_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Friday') THEN wscs.sales_price
                  ELSE NULL
              END) fri_sales,
          sum(CASE
                  WHEN (date_dim.d_day_name='Saturday') THEN wscs.sales_price
                  ELSE NULL
              END) sat_sales
   FROM wscs,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE date_dim.d_date_sk = wscs.sold_date_sk
   GROUP BY date_dim.d_week_seq)
SELECT d_week_seq1,
       round(sun_sales1/sun_sales2, 2) r1,
       round(mon_sales1/mon_sales2, 2) r2,
       round(tue_sales1/tue_sales2, 2) r3,
       round(wed_sales1/wed_sales2, 2) r4,
       round(thu_sales1/thu_sales2, 2) r5,
       round(fri_sales1/fri_sales2, 2) r6,
       round(sat_sales1/sat_sales2, 2)
FROM
  (SELECT wswscs.d_week_seq d_week_seq1,
          wswscs.sun_sales sun_sales1,
          wswscs.mon_sales mon_sales1,
          wswscs.tue_sales tue_sales1,
          wswscs.wed_sales wed_sales1,
          wswscs.thu_sales thu_sales1,
          wswscs.fri_sales fri_sales1,
          wswscs.sat_sales sat_sales1
   FROM wswscs,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE date_dim.d_week_seq = wswscs.d_week_seq
     AND date_dim.d_year = 2001) y,
  (SELECT wswscs.d_week_seq d_week_seq2,
          wswscs.sun_sales sun_sales2,
          wswscs.mon_sales mon_sales2,
          wswscs.tue_sales tue_sales2,
          wswscs.wed_sales wed_sales2,
          wswscs.thu_sales thu_sales2,
          wswscs.fri_sales fri_sales2,
          wswscs.sat_sales sat_sales2
   FROM wswscs,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE date_dim.d_week_seq = wswscs.d_week_seq
     AND date_dim.d_year = 2001+1) z
WHERE d_week_seq1 = d_week_seq2-53
ORDER BY d_week_seq1 NULLS FIRST;
