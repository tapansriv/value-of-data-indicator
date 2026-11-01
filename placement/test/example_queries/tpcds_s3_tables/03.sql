SELECT dt.d_year,
       item.i_brand_id brand_id,
       item.i_brand brand,
       sum(ss_ext_sales_price) sum_agg
FROM 's3://vod-tpcds-10gb/date_dim.parquet' AS dt,
     's3://vod-tpcds-10gb/store_sales.parquet' AS store_sales,
     's3://vod-tpcds-10gb/item.parquet' AS item
WHERE dt.d_date_sk = store_sales.ss_sold_date_sk
  AND store_sales.ss_item_sk = item.i_item_sk
  AND item.i_manufact_id = 128
  AND dt.d_moy=11
GROUP BY dt.d_year,
         item.i_brand,
         item.i_brand_id
ORDER BY dt.d_year,
         sum_agg DESC,
         brand_id
LIMIT 100;

