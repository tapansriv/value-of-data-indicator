SELECT warehouse.w_state,
       item.i_item_id,
       sum(CASE
               WHEN (cast(date_dim.d_date AS date) < CAST ('2000-03-11' AS date)) THEN catalog_sales.cs_sales_price - coalesce(catalog_returns.cr_refunded_cash,0)
               ELSE 0
           END) AS sales_before,
       sum(CASE
               WHEN (cast(date_dim.d_date AS date) >= CAST ('2000-03-11' AS date)) THEN catalog_sales.cs_sales_price - coalesce(catalog_returns.cr_refunded_cash,0)
               ELSE 0
           END) AS sales_after
FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales
LEFT OUTER JOIN dfs.`tmp/catalog_returns.parquet` AS catalog_returns ON (catalog_sales.cs_order_number = catalog_returns.cr_order_number
                                    AND catalog_sales.cs_item_sk = catalog_returns.cr_item_sk) ,dfs.`tmp/warehouse.parquet` AS warehouse,
                                                                  dfs.`tmp/item.parquet` AS item,
                                                                  dfs.`tmp/date_dim.parquet` AS date_dim
WHERE item.i_current_price BETWEEN 0.99 AND 1.49
  AND item.i_item_sk = catalog_sales.cs_item_sk
  AND catalog_sales.cs_warehouse_sk = warehouse.w_warehouse_sk
  AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
  AND date_dim.d_date BETWEEN CAST ('2000-02-10' AS date) AND CAST ('2000-04-10' AS date)
GROUP BY warehouse.w_state,
         item.i_item_id
ORDER BY warehouse.w_state,
         item.i_item_id
LIMIT 100;

