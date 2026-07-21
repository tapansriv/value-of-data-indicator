SELECT item.i_item_desc,
       warehouse.w_warehouse_name,
       d1.d_week_seq,
       sum(CASE
               WHEN promotion.p_promo_sk IS NULL THEN 1
               ELSE 0
           END) no_promo,
       sum(CASE
               WHEN promotion.p_promo_sk IS NOT NULL THEN 1
               ELSE 0
           END) promo,
       count(*) total_cnt
FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales
JOIN dfs.`tmp/inventory.parquet` AS inventory ON (catalog_sales.cs_item_sk = inventory.inv_item_sk)
JOIN dfs.`tmp/warehouse.parquet` ON (warehouse.w_warehouse_sk=inv_warehouse_sk)
JOIN dfs.`tmp/item.parquet` ON (item.i_item_sk = catalog_sales.cs_item_sk)
JOIN dfs.`tmp/customer_demographics.parquet` AS customer_demographics ON (catalog_sales.cs_bill_cdemo_sk = customer_demographics.cd_demo_sk)
JOIN dfs.`tmp/household_demographics.parquet` AS household_demographics ON (catalog_sales.cs_bill_hdemo_sk = household_demographics.hd_demo_sk)
JOIN dfs.`tmp/date_dim.parquet` d1 ON (catalog_sales.cs_sold_date_sk = d1.d_date_sk)
JOIN dfs.`tmp/date_dim.parquet` d2 ON (inventory.inv_date_sk = d2.d_date_sk)
JOIN dfs.`tmp/date_dim.parquet` d3 ON (catalog_sales.cs_ship_date_sk = d3.d_date_sk)
LEFT OUTER JOIN dfs.`tmp/promotion.parquet` AS promotion ON (catalog_sales.cs_promo_sk=p_promo_sk)
LEFT OUTER JOIN dfs.`tmp/catalog_returns.parquet` AS catalog_returns ON (catalog_returns.cr_item_sk = catalog_sales.cs_item_sk
                                    AND catalog_returns.cr_order_number = catalog_sales.cs_order_number)
WHERE d1.d_week_seq = d2.d_week_seq
  AND inventory.inv_quantity_on_hand < catalog_sales.cs_quantity
  AND cast(d3.d_date as date) > cast(d1.d_date as date) + 5 -- SQL Server: DATEADD(day, 5, d1.d_date)
  AND household_demographics.hd_buy_potential = '>10000'
  AND d1.d_year = 1999
  AND customer_demographics.cd_marital_status = 'D'
GROUP BY item.i_item_desc,
         warehouse.w_warehouse_name,
         d1.d_week_seq
ORDER BY total_cnt DESC NULLS FIRST,
         item.i_item_desc NULLS FIRST,
         warehouse.w_warehouse_name NULLS FIRST,
         d1.d_week_seq NULLS FIRST
LIMIT 100;

