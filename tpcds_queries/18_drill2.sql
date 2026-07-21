WITH results AS
  (SELECT item.i_item_id,
          customer_address.ca_country,
          customer_address.ca_state,
          customer_address.ca_county,
          cast(catalog_sales.cs_quantity AS decimal(12,2)) agg1,
          cast(catalog_sales.cs_list_price AS decimal(12,2)) agg2,
          cast(catalog_sales.cs_coupon_amt AS decimal(12,2)) agg3,
          cast(catalog_sales.cs_sales_price AS decimal(12,2)) agg4,
          cast(catalog_sales.cs_net_profit AS decimal(12,2)) agg5,
          cast(customer.c_birth_year AS decimal(12,2)) agg6,
          cast(cd1.cd_dep_count AS decimal(12,2)) agg7
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/customer_demographics.parquet` cd1,
        dfs.`tmp/customer_demographics.parquet` cd2,
        dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/customer_address.parquet` AS customer_address,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/item.parquet` AS item
   WHERE catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
     AND catalog_sales.cs_item_sk = item.i_item_sk
     AND catalog_sales.cs_bill_cdemo_sk = cd1.cd_demo_sk
     AND catalog_sales.cs_bill_customer_sk = customer.c_customer_sk
     AND cd1.cd_gender = 'F'
     AND cd1.cd_education_status = 'Unknown'
     AND customer.c_current_cdemo_sk = cd2.cd_demo_sk
     AND customer.c_current_addr_sk = customer_address.ca_address_sk
     AND customer.c_birth_month IN (1,
                           6,
                           8,
                           9,
                           12,
                           2)
     AND date_dim.d_year = 1998
     AND customer_address.ca_state IN ('MS',
                      'IN',
                      'ND',
                      'OK',
                      'NM',
                      'VA',
                      'MS') )
SELECT i_item_id,
       ca_country,
       ca_state,
       ca_county,
       agg1,
       agg2,
       agg3,
       agg4,
       agg5,
       agg6,
       agg7
FROM
    results
  --( SELECT i_item_id,
  --         ca_country,
  --         ca_state,
  --         ca_county,
  --         avg(agg1) agg1,
  --         avg(agg2) agg2,
  --         avg(agg3) agg3,
  --         avg(agg4) agg4,
  --         avg(agg5) agg5,
  --         avg(agg6) agg6,
  --         avg(agg7) agg7
  -- FROM results
  -- GROUP BY i_item_id,
  --          ca_country,
  --          ca_state,
  --          ca_county
  -- UNION ALL SELECT i_item_id,
  --                  ca_country,
  --                  ca_state,
  --                  NULL AS county,
  --                  avg(agg1) agg1,
  --                  avg(agg2) agg2,
  --                  avg(agg3) agg3,
  --                  avg(agg4) agg4,
  --                  avg(agg5) agg5,
  --                  avg(agg6) agg6,
  --                  avg(agg7) agg7
  -- FROM results
  -- GROUP BY i_item_id,
  --          ca_country,
  --          ca_state
  -- UNION ALL SELECT i_item_id,
  --                  ca_country,
  --                  NULL AS ca_state,
  --                  NULL AS county,
  --                  avg(agg1) agg1,
  --                  avg(agg2) agg2,
  --                  avg(agg3) agg3,
  --                  avg(agg4) agg4,
  --                  avg(agg5) agg5,
  --                  avg(agg6) agg6,
  --                  avg(agg7) agg7
  -- FROM results
  -- GROUP BY i_item_id,
  --          ca_country
  -- UNION ALL SELECT i_item_id,
  --                  NULL AS ca_country,
  --                  NULL AS ca_state,
  --                  NULL AS county,
  --                  avg(agg1) agg1,
  --                  avg(agg2) agg2,
  --                  avg(agg3) agg3,
  --                  avg(agg4) agg4,
  --                  avg(agg5) agg5,
  --                  avg(agg6) agg6,
  --                  avg(agg7) agg7
  -- FROM results
  -- GROUP BY i_item_id
  -- UNION ALL SELECT NULL AS i_item_id,
  --                  NULL AS ca_country,
  --                  NULL AS ca_state,
  --                  NULL AS county,
  --                  avg(agg1) agg1,
  --                  avg(agg2) agg2,
  --                  avg(agg3) agg3,
  --                  avg(agg4) agg4,
  --                  avg(agg5) agg5,
  --                  avg(agg6) agg6,
  --                  avg(agg7) agg7
  -- FROM results ) foo
ORDER BY ca_country NULLS FIRST,
         ca_state NULLS FIRST,
         ca_county NULLS FIRST,
         i_item_id NULLS FIRST
LIMIT 100;

