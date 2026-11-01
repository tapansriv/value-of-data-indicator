-- R2D7 rg-selective: base query22, target inventory, level 4/4, authored 2026-10-21
-- start query 22 in stream 0 using template query22.tpl 
SELECT i_product_name, 
               i_brand, 
               i_class, 
               i_category, 
               Avg(inv_quantity_on_hand) qoh 
FROM   inventory, 
       date_dim, 
       item, 
       warehouse 
WHERE  inv_date_sk = d_date_sk 
       AND inv_item_sk = i_item_sk 
       AND inv_warehouse_sk = w_warehouse_sk 
       AND d_month_seq BETWEEN 1205 AND 1205 + 11 
       AND inv_date_sk BETWEEN 2451697 AND 2452061 -- 2000-06-01 .. 2001-05-31 (d_month_seq 1205..1216)
GROUP  BY rollup( i_product_name, i_brand, i_class, i_category ) 
ORDER  BY qoh, 
          i_product_name, 
          i_brand, 
          i_class, 
          i_category
LIMIT 100; 
