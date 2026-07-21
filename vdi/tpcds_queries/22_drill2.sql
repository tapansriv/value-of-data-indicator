-- WITH results AS
  --(
    SELECT item.i_product_name ,
          item.i_brand ,
          item.i_class ,
          item.i_category ,
          inventory.inv_quantity_on_hand qoh
   FROM dfs.`tmp/inventory.parquet` AS inventory ,
        dfs.`tmp/date_dim.parquet` AS date_dim ,
        dfs.`tmp/item.parquet` AS item ,
        dfs.`tmp/warehouse.parquet` AS warehouse
   WHERE inventory.inv_date_sk=date_dim.d_date_sk
     AND inventory.inv_item_sk=item.i_item_sk
     AND inventory.inv_warehouse_sk = warehouse.w_warehouse_sk
     AND date_dim.d_month_seq BETWEEN 1200 AND 1200 + 11; --)
 --results_rollup AS
 -- (SELECT i_product_name,
 --         i_brand,
 --         i_class,
 --         i_category,
 --         avg(qoh) qoh
 --  FROM results
 --  GROUP BY i_product_name,
 --           i_brand,
 --           i_class,
 --           i_category
 --  UNION ALL SELECT i_product_name,
 --                   i_brand,
 --                   i_class,
 --                   NULL i_category,
 --                        avg(qoh) qoh
 --  FROM results
 --  GROUP BY i_product_name,
 --           i_brand,
 --           i_class
 --  UNION ALL SELECT i_product_name,
 --                   i_brand,
 --                   NULL i_class,
 --                        NULL i_category,
 --                             avg(qoh) qoh
 --  FROM results
 --  GROUP BY i_product_name,
 --           i_brand
 --  UNION ALL SELECT i_product_name,
 --                   NULL i_brand,
 --                        NULL i_class,
 --                             NULL i_category,
 --                                  avg(qoh) qoh
 --  FROM results
 --  GROUP BY i_product_name
 --  UNION ALL SELECT NULL i_product_name,
 --                        NULL i_brand,
 --                             NULL i_class,
 --                                  NULL i_category,
 --                                       avg(qoh) qoh
 --  FROM results)
-- SELECT i_product_name,
--        i_brand,
--        i_class,
--        i_category,
--        qoh
-- FROM results_rollup
-- ORDER BY qoh NULLS FIRST,
--          i_product_name NULLS FIRST,
--          i_brand NULLS FIRST,
--          i_class NULLS FIRST,
--          i_category NULLS FIRST
-- LIMIT 100;
-- 
