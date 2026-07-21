SELECT item.i_item_id ,
       item.i_item_desc,
       item.i_category,
       item.i_class,
       item.i_current_price ,
       sum(store_sales.ss_ext_sales_price) AS itemrevenue,
       sum(store_sales.ss_ext_sales_price)*100.0000/sum(sum(store_sales.ss_ext_sales_price)) OVER (PARTITION BY item.i_class) AS revenueratio
FROM dfs.`tmp/store_sales.parquet` AS store_sales ,
     dfs.`tmp/item.parquet` AS item,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE store_sales.ss_item_sk = item.i_item_sk
  AND item.i_category IN ('Sports',
                     'Books',
                     'Home')
  AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
  AND date_dim.d_date BETWEEN cast('1999-02-22' AS date) AND cast('1999-03-24' AS date)
GROUP BY item.i_item_id ,
         item.i_item_desc,
         item.i_category ,
         item.i_class ,
         item.i_current_price
ORDER BY item.i_category  NULLS FIRST,
         item.i_class  NULLS FIRST,
         item.i_item_id  NULLS FIRST,
         item.i_item_desc  NULLS FIRST,
         revenueratio NULLS FIRST;
