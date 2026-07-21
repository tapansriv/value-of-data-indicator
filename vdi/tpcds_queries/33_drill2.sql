WITH ss AS
  ( SELECT item.i_manufact_id,
           sum(store_sales.ss_ext_sales_price) total_sales
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer_address.parquet` AS customer_address,
        dfs.`tmp/item.parquet` AS item
   WHERE item.i_manufact_id IN
       (SELECT item.i_manufact_id
        FROM dfs.`tmp/item.parquet` AS item
        WHERE item.i_category IN ('Electronics'))
     AND store_sales.ss_item_sk = item.i_item_sk
     AND store_sales.ss_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_year = 1998
     AND date_dim.d_moy = 5
     AND store_sales.ss_addr_sk = customer_address.ca_address_sk
     AND customer_address.ca_gmt_offset = -5
   GROUP BY item.i_manufact_id),
cs AS
  ( SELECT item.i_manufact_id,
           sum(catalog_sales.cs_ext_sales_price) total_sales
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer_address.parquet` AS customer_address,
        dfs.`tmp/item.parquet` AS item
   WHERE item.i_manufact_id IN
       (SELECT item.i_manufact_id
        FROM dfs.`tmp/item.parquet` AS item
        WHERE item.i_category IN ('Electronics'))
     AND catalog_sales.cs_item_sk = item.i_item_sk
     AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_year = 1998
     AND date_dim.d_moy = 5
     AND catalog_sales.cs_bill_addr_sk = customer_address.ca_address_sk
     AND customer_address.ca_gmt_offset = -5
   GROUP BY item.i_manufact_id),
ws AS
  ( SELECT item.i_manufact_id,
           sum(web_sales.ws_ext_sales_price) total_sales
   FROM dfs.`tmp/web_sales.parquet` AS web_sales,
        dfs.`tmp/date_dim.parquet` AS date_dim,
        dfs.`tmp/customer_address.parquet` AS customer_address,
        dfs.`tmp/item.parquet` AS item
   WHERE item.i_manufact_id IN
       (SELECT item.i_manufact_id
        FROM dfs.`tmp/item.parquet` AS item
        WHERE item.i_category IN ('Electronics'))
     AND web_sales.ws_item_sk = item.i_item_sk
     AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
     AND date_dim.d_year = 1998
     AND date_dim.d_moy = 5
     AND web_sales.ws_bill_addr_sk = customer_address.ca_address_sk
     AND customer_address.ca_gmt_offset = -5
   GROUP BY item.i_manufact_id)
SELECT i_manufact_id,
       sum(total_sales) total_sales
FROM
  (SELECT *
   FROM ss
   UNION ALL SELECT *
   FROM cs
   UNION ALL SELECT *
   FROM ws) tmp1
GROUP BY i_manufact_id
ORDER BY total_sales
LIMIT 100;

