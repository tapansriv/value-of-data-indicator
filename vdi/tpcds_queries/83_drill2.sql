WITH sr_items AS
  (SELECT item.i_item_id item_id,
          sum(store_returns.sr_return_quantity) sr_item_qty
   FROM dfs.`tmp/store_returns.parquet` AS store_returns,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE store_returns.sr_item_sk = item.i_item_sk
     AND date_dim.d_date IN
       (SELECT date_dim.d_date
        FROM dfs.`tmp/date_dim.parquet` AS date_dim
        WHERE date_dim.d_week_seq IN
            (SELECT date_dim.d_week_seq
             FROM dfs.`tmp/date_dim.parquet` AS date_dim
             WHERE date_dim.d_date IN ('2000-06-30',
                              '2000-09-27',
                              '2000-11-17')))
     AND store_returns.sr_returned_date_sk = date_dim.d_date_sk
   GROUP BY item.i_item_id),
cr_items AS
  (SELECT item.i_item_id item_id,
          sum(catalog_returns.cr_return_quantity) cr_item_qty
   FROM dfs.`tmp/catalog_returns.parquet` AS catalog_returns,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE catalog_returns.cr_item_sk = item.i_item_sk
     AND date_dim.d_date IN
       (SELECT date_dim.d_date
        FROM dfs.`tmp/date_dim.parquet` AS date_dim
        WHERE date_dim.d_week_seq IN
            (SELECT date_dim.d_week_seq
             FROM dfs.`tmp/date_dim.parquet` AS date_dim
             WHERE date_dim.d_date IN ('2000-06-30',
                              '2000-09-27',
                              '2000-11-17')))
     AND catalog_returns.cr_returned_date_sk = date_dim.d_date_sk
   GROUP BY item.i_item_id),
wr_items AS
  (SELECT item.i_item_id item_id,
          sum(web_returns.wr_return_quantity) wr_item_qty
   FROM dfs.`tmp/web_returns.parquet` AS web_returns,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE web_returns.wr_item_sk = item.i_item_sk
     AND date_dim.d_date IN
       (SELECT date_dim.d_date
        FROM dfs.`tmp/date_dim.parquet` AS date_dim
        WHERE date_dim.d_week_seq IN
            (SELECT date_dim.d_week_seq
             FROM dfs.`tmp/date_dim.parquet` AS date_dim
             WHERE date_dim.d_date IN ('2000-06-30',
                              '2000-09-27',
                              '2000-11-17')))
     AND web_returns.wr_returned_date_sk = date_dim.d_date_sk
   GROUP BY item.i_item_id)
SELECT sr_items.item_id ,
       sr_item_qty ,
       (sr_item_qty*1.0000)/(sr_item_qty+cr_item_qty+wr_item_qty)/3.0000 * 100 sr_dev ,
       cr_item_qty ,
       (cr_item_qty*1.0000)/(sr_item_qty+cr_item_qty+wr_item_qty)/3.0000 * 100 cr_dev ,
       wr_item_qty ,
       (wr_item_qty*1.0000)/(sr_item_qty+cr_item_qty+wr_item_qty)/3.0000 * 100 wr_dev ,
       (sr_item_qty+cr_item_qty+wr_item_qty)/3.0 average
FROM sr_items ,
     cr_items ,
     wr_items
WHERE sr_items.item_id=cr_items.item_id
  AND sr_items.item_id=wr_items.item_id
ORDER BY sr_items.item_id NULLS FIRST,
         sr_item_qty NULLS FIRST
LIMIT 100;

