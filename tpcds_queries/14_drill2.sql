WITH cross_items AS
  (SELECT item.i_item_sk AS ss_item_sk
   FROM dfs.`tmp/item.parquet` AS item,
     (SELECT iss.i_brand_id brand_id ,
             iss.i_class_id class_id ,
             iss.i_category_id category_id
      FROM dfs.`tmp/store_sales.parquet` AS store_sales ,
           dfs.`tmp/item.parquet` iss ,
           dfs.`tmp/date_dim.parquet` d1
      WHERE store_sales.ss_item_sk = iss.i_item_sk
        AND store_sales.ss_sold_date_sk = d1.d_date_sk
        AND d1.d_year BETWEEN 1999 AND 1999 + 2 INTERSECT
        SELECT ics.i_brand_id ,
               ics.i_class_id ,
               ics.i_category_id
        FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales ,
             dfs.`tmp/item.parquet` ics ,
             dfs.`tmp/date_dim.parquet` d2 WHERE catalog_sales.cs_item_sk = ics.i_item_sk
        AND catalog_sales.cs_sold_date_sk = d2.d_date_sk
        AND d2.d_year BETWEEN 1999 AND 1999 + 2 INTERSECT
        SELECT iws.i_brand_id ,
               iws.i_class_id ,
               iws.i_category_id
        FROM dfs.`tmp/web_sales.parquet` AS web_sales ,
             dfs.`tmp/item.parquet` iws ,
             dfs.`tmp/date_dim.parquet` d3 WHERE web_sales.ws_item_sk = iws.i_item_sk
        AND web_sales.ws_sold_date_sk = d3.d_date_sk
        AND d3.d_year BETWEEN 1999 AND 1999 + 2) x
   WHERE item.i_brand_id = x.brand_id
     AND item.i_class_id = x.class_id
     AND item.i_category_id = x.category_id ),
avg_sales AS
  (SELECT avg(x.quantity*x.list_price) average_sales
   FROM
     (SELECT store_sales.ss_quantity quantity ,
             store_sales.ss_list_price list_price
      FROM dfs.`tmp/store_sales.parquet` AS store_sales ,
           dfs.`tmp/date_dim.parquet` AS date_dim
      WHERE store_sales.ss_sold_date_sk = date_dim.d_date_sk
        AND date_dim.d_year BETWEEN 1999 AND 2001
      UNION ALL SELECT catalog_sales.cs_quantity quantity,
                       catalog_sales.cs_list_price list_price
      FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales ,
           dfs.`tmp/date_dim.parquet` AS date_dim
      WHERE catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
        AND date_dim.d_year BETWEEN 1999 AND 1999 + 2
      UNION ALL SELECT web_sales.ws_quantity quantity ,
                       web_sales.ws_list_price list_price
      FROM dfs.`tmp/web_sales.parquet` AS web_sales ,
           dfs.`tmp/date_dim.parquet` AS date_dim
      WHERE web_sales.ws_sold_date_sk = date_dim.d_date_sk
        AND date_dim.d_year BETWEEN 1999 AND 1999 + 2) x),
results AS
  (SELECT channel,
          i_brand_id,
          i_class_id,
          i_category_id,
          sum(sales) sum_sales,
          sum(number_sales) number_sales
   FROM
     ( SELECT 'store' channel,
                      item.i_brand_id,
                      item.i_class_id ,
                      item.i_category_id,
                      sum(store_sales.ss_quantity*store_sales.ss_list_price) sales ,
                      count(*) number_sales
      FROM dfs.`tmp/store_sales.parquet` AS store_sales ,
           dfs.`tmp/item.parquet` AS item ,
           dfs.`tmp/date_dim.parquet` AS date_dim
      WHERE store_sales.ss_item_sk IN
          (SELECT ss_item_sk
           FROM cross_items)
        AND store_sales.ss_item_sk = item.i_item_sk
        AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
        AND date_dim.d_year = 1999+2
        AND date_dim.d_moy = 11
      GROUP BY item.i_brand_id,
               item.i_class_id,
               item.i_category_id
      HAVING sum(store_sales.ss_quantity*store_sales.ss_list_price) >
        (SELECT average_sales
         FROM avg_sales)
      UNION ALL SELECT 'catalog' channel,
                                 item.i_brand_id,
                                 item.i_class_id,
                                 item.i_category_id,
                                 sum(catalog_sales.cs_quantity*catalog_sales.cs_list_price) sales,
                                 count(*) number_sales
      FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales ,
           dfs.`tmp/item.parquet` AS item ,
           dfs.`tmp/date_dim.parquet` AS date_dim
      WHERE catalog_sales.cs_item_sk IN
          (SELECT ss_item_sk
           FROM cross_items)
        AND catalog_sales.cs_item_sk = item.i_item_sk
        AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
        AND date_dim.d_year = 1999+2
        AND date_dim.d_moy = 11
      GROUP BY item.i_brand_id,
               item.i_class_id,
               item.i_category_id
      HAVING sum(catalog_sales.cs_quantity*catalog_sales.cs_list_price) >
        (SELECT average_sales
         FROM avg_sales)
      UNION ALL SELECT 'web' channel,
                             item.i_brand_id,
                             item.i_class_id,
                             item.i_category_id,
                             sum(web_sales.ws_quantity*web_sales.ws_list_price) sales,
                             count(*) number_sales
      FROM dfs.`tmp/web_sales.parquet` AS web_sales ,
           dfs.`tmp/item.parquet` AS item ,
           dfs.`tmp/date_dim.parquet` AS date_dim
      WHERE web_sales.ws_item_sk IN
          (SELECT cross_items.ss_item_sk
           FROM cross_items)
        AND web_sales.ws_item_sk = item.i_item_sk
        AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
        AND date_dim.d_year = 1999+2
        AND date_dim.d_moy = 11
      GROUP BY i_brand_id,
               i_class_id,
               i_category_id
      HAVING sum(web_sales.ws_quantity*web_sales.ws_list_price) >
        (SELECT average_sales
         FROM avg_sales) ) y
   GROUP BY channel,
            i_brand_id,
            i_class_id,
            i_category_id)
SELECT channel,
       i_brand_id,
       i_class_id,
       i_category_id,
       sum_sales,
       number_sales
FROM
    results
  -- ( SELECT channel,
  --          i_brand_id,
  --          i_class_id,
  --          i_category_id,
  --          sum_sales,
  --          number_sales
  --  FROM results
  --  UNION SELECT channel,
  --               i_brand_id,
  --               i_class_id,
  --               NULL AS i_category_id,
  --               sum(sum_sales),
  --               sum(number_sales)
  --  FROM results
  --  GROUP BY channel,
  --           i_brand_id,
  --           i_class_id
  --  UNION SELECT channel,
  --               i_brand_id,
  --               NULL AS i_class_id,
  --               NULL AS i_category_id,
  --               sum(sum_sales),
  --               sum(number_sales)
  --  FROM results
  --  GROUP BY channel,
  --           i_brand_id
  --  UNION SELECT channel,
  --               NULL AS i_brand_id,
  --               NULL AS i_class_id,
  --               NULL AS i_category_id,
  --               sum(sum_sales),
  --               sum(number_sales)
  --  FROM results
  --  GROUP BY channel
  --  UNION SELECT NULL AS channel,
  --               NULL AS i_brand_id,
  --               NULL AS i_class_id,
  --               NULL AS i_category_id,
  --               sum(sum_sales),
  --               sum(number_sales)
  --  FROM results) z
ORDER BY channel NULLS FIRST,
         i_brand_id NULLS FIRST,
         i_class_id NULLS FIRST,
         i_category_id NULLS FIRST
LIMIT 100;

