
SELECT item.i_item_id ,
       item.i_item_desc,
       item.i_category,
       item.i_class,
       item.i_current_price ,
       sum(catalog_sales.cs_ext_sales_price) AS itemrevenue,
       sum(catalog_sales.cs_ext_sales_price)*100.0000/sum(sum(catalog_sales.cs_ext_sales_price)) OVER (PARTITION BY item.i_class) AS revenueratio
FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales ,
     dfs.`tmp/item.parquet` AS item,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE catalog_sales.cs_item_sk = item.i_item_sk
  AND item.i_category IN ('Sports',
                     'Books',
                     'Home')
  AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
  AND date_dim.d_date BETWEEN cast('1999-02-22' AS date) AND cast('1999-03-24' AS date)
GROUP BY item.i_item_id ,
         item.i_item_desc,
         item.i_category ,
         item.i_class ,
         item.i_current_price
ORDER BY item.i_category NULLS FIRST,
         item.i_class NULLS FIRST,
         item.i_item_id NULLS FIRST,
         item.i_item_desc NULLS FIRST,
         revenueratio NULLS FIRST
LIMIT 100;

