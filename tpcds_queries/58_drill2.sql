WITH ss_items AS
  (SELECT item.i_item_id item_id,
          sum(store_sales.ss_ext_sales_price) ss_item_rev
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE store_sales.ss_item_sk = item.i_item_sk
     AND date_dim.d_date IN
       (SELECT date_dim.d_date
        FROM dfs.`tmp/date_dim.parquet` AS date_dim
        WHERE date_dim.d_week_seq =
            (SELECT date_dim.d_week_seq
             FROM dfs.`tmp/date_dim.parquet` AS date_dim
             WHERE date_dim.d_date = '2000-01-03'))
     AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
   GROUP BY item.i_item_id),
cs_items AS
  (SELECT item.i_item_id item_id,
          sum(catalog_sales.cs_ext_sales_price) cs_item_rev
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE catalog_sales.cs_item_sk = item.i_item_sk
     AND date_dim.d_date IN
       (SELECT date_dim.d_date
        FROM dfs.`tmp/date_dim.parquet` AS date_dim
        WHERE date_dim.d_week_seq =
            (SELECT date_dim.d_week_seq
             FROM dfs.`tmp/date_dim.parquet` AS date_dim
             WHERE date_dim.d_date = '2000-01-03'))
     AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
   GROUP BY item.i_item_id),
ws_items AS
  (SELECT item.i_item_id item_id,
          sum(web_sales.ws_ext_sales_price) ws_item_rev
   FROM dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE web_sales.ws_item_sk = item.i_item_sk
     AND date_dim.d_date IN
       (SELECT date_dim.d_date
        FROM dfs.`tmp/date_dim.parquet` AS date_dim
        WHERE date_dim.d_week_seq =
            (SELECT date_dim.d_week_seq
             FROM dfs.`tmp/date_dim.parquet` AS date_dim
             WHERE date_dim.d_date = '2000-01-03'))
     AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
   GROUP BY item.i_item_id)
SELECT ss_items.item_id,
       ss_item_rev,
       ss_item_rev/((ss_item_rev+cs_item_rev+ws_item_rev)/3) * 100 ss_dev,
       cs_item_rev,
       cs_item_rev/((ss_item_rev+cs_item_rev+ws_item_rev)/3) * 100 cs_dev,
       ws_item_rev,
       ws_item_rev/((ss_item_rev+cs_item_rev+ws_item_rev)/3) * 100 ws_dev,
       (ss_item_rev+cs_item_rev+ws_item_rev)/3 average
FROM ss_items,
     cs_items,
     ws_items
WHERE ss_items.item_id=cs_items.item_id
  AND ss_items.item_id=ws_items.item_id
  AND ss_item_rev BETWEEN 0.9 * cs_item_rev AND 1.1 * cs_item_rev
  AND ss_item_rev BETWEEN 0.9 * ws_item_rev AND 1.1 * ws_item_rev
  AND cs_item_rev BETWEEN 0.9 * ss_item_rev AND 1.1 * ss_item_rev
  AND cs_item_rev BETWEEN 0.9 * ws_item_rev AND 1.1 * ws_item_rev
  AND ws_item_rev BETWEEN 0.9 * ss_item_rev AND 1.1 * ss_item_rev
  AND ws_item_rev BETWEEN 0.9 * cs_item_rev AND 1.1 * cs_item_rev
ORDER BY ss_items.item_id NULLS FIRST,
         ss_item_rev NULLS FIRST
LIMIT 100;

