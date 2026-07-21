SELECT *
FROM
  (SELECT warehouse.w_warehouse_name,
          item.i_item_id,
          sum(CASE
                  WHEN (cast(date_dim.d_date AS date) < CAST ('2000-03-11' AS date)) THEN inventory.inv_quantity_on_hand
                  ELSE 0
              END) AS inv_before,
          sum(CASE
                  WHEN (cast(date_dim.d_date AS date) >= CAST ('2000-03-11' AS date)) THEN inventory.inv_quantity_on_hand
                  ELSE 0
              END) AS inv_after
   FROM dfs.`tmp/inventory.parquet` AS inventory,
        dfs.`tmp/warehouse.parquet` AS warehouse,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/date_dim.parquet` AS date_dim
   WHERE item.i_current_price BETWEEN 0.99 AND 1.49
     AND item.i_item_sk = inventory.inv_item_sk
     AND inventory.inv_warehouse_sk = warehouse.w_warehouse_sk
     AND inventory.inv_date_sk = date_dim.d_date_sk
     AND date_dim.d_date BETWEEN CAST ('2000-02-10' AS date) AND CAST ('2000-04-10' AS date)
   GROUP BY warehouse.w_warehouse_name,
            item.i_item_id) x
WHERE (CASE
           WHEN inv_before > 0 THEN (inv_after*1.000) / inv_before
           ELSE NULL
       END) BETWEEN 2.000/3.000 AND 3.000/2.000
ORDER BY w_warehouse_name NULLS FIRST,
         i_item_id NULLS FIRST
LIMIT 100;

