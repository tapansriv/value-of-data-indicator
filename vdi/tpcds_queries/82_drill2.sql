
SELECT item.i_item_id ,
       item.i_item_desc ,
       item.i_current_price
FROM dfs.`tmp/item.parquet` AS item,
     dfs.`tmp/inventory.parquet` AS inventory,
     dfs.`tmp/date_dim.parquet` AS date_dim,
     dfs.`tmp/store_sales.parquet` AS store_sales
WHERE item.i_current_price BETWEEN 62 AND 62+30
  AND inventory.inv_item_sk = item.i_item_sk
  AND date_dim.d_date_sk=inv_date_sk
  AND date_dim.d_date BETWEEN cast('2000-05-25' AS date) AND cast('2000-07-24' AS date)
  AND item.i_manufact_id IN (129,
                        270,
                        821,
                        423)
  AND inventory.inv_quantity_on_hand BETWEEN 100 AND 500
  AND store_sales.ss_item_sk = item.i_item_sk
GROUP BY item.i_item_id,
         item.i_item_desc,
         item.i_current_price
ORDER BY item.i_item_id
LIMIT 100;

