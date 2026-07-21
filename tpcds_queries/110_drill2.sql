SELECT item.i_item_id,
       item.i_item_desc,
       item.i_category,
       item.i_class,
       item.i_current_price,
       sum(web_sales.ws_ext_sales_price) AS itemrevenue,
       sum(web_sales.ws_ext_sales_price)*100.0000/sum(sum(web_sales.ws_ext_sales_price)) OVER (PARTITION BY item.i_class) AS revenueratio
FROM dfs.`tmp/web_sales.parquet` AS web_sales,
     dfs.`tmp/item.parquet` AS item,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE web_sales.ws_item_sk = item.i_item_sk
  AND item.i_category IN ('Sports',
                     'Books',
                     'Home')
  AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
  AND date_dim.d_date BETWEEN cast('1999-02-22' AS date) AND cast('1999-03-24' AS date)
  AND web_sales.ws_item_sk < 20000 
GROUP BY item.i_item_id,
         item.i_item_desc,
         item.i_category,
         item.i_class,
         item.i_current_price
ORDER BY item.i_category,
         item.i_class,
         item.i_item_id,
         item.i_item_desc,
         revenueratio
LIMIT 100;

