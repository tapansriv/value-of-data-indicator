
SELECT i_item_id ,
       i_item_desc,
       i_category,
       i_class,
       i_current_price ,
       sum(cs_ext_sales_price) AS itemrevenue,
       sum(cs_ext_sales_price)*100.0000/sum(sum(cs_ext_sales_price)) OVER (PARTITION BY i_class) AS revenueratio
FROM 's3://vod-tpcds-10gb/catalog_sales.parquet' AS catalog_sales ,
     's3://vod-tpcds-10gb/item.parquet' AS item,
     's3://vod-tpcds-10gb/date_dim.parquet' AS date_dim
WHERE cs_item_sk = i_item_sk
  AND i_category IN ('Sports',
                     'Books',
                     'Home')
  AND cs_sold_date_sk = d_date_sk
  AND d_date BETWEEN cast('1999-02-22' AS date) AND cast('1999-03-24' AS date)
GROUP BY i_item_id ,
         i_item_desc,
         i_category ,
         i_class ,
         i_current_price
ORDER BY i_category NULLS FIRST,
         i_class NULLS FIRST,
         i_item_id NULLS FIRST,
         i_item_desc NULLS FIRST,
         revenueratio NULLS FIRST
LIMIT 100;

