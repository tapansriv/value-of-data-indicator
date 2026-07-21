SELECT sum(catalog_sales.cs_ext_discount_amt) AS excess_discount_amount
FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales ,
     dfs.`tmp/item.parquet` AS item ,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE item.i_manufact_id = 977
  AND item.i_item_sk = catalog_sales.cs_item_sk
  AND date_dim.d_date BETWEEN cast('2000-01-27' as date) AND cast('2000-04-26' AS date)
  AND date_dim.d_date_sk = catalog_sales.cs_sold_date_sk
  AND catalog_sales.cs_ext_discount_amt >
    ( SELECT 1.3 * avg(catalog_sales.cs_ext_discount_amt)
     FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales ,
          dfs.`tmp/date_dim.parquet` AS date_dim
     WHERE catalog_sales.cs_item_sk = item.i_item_sk
       AND date_dim.d_date BETWEEN cast('2000-01-27' as date) AND cast('2000-04-26' AS date)
       AND date_dim.d_date_sk = catalog_sales.cs_sold_date_sk )
LIMIT 100;

