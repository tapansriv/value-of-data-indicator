SELECT customer_address.ca_zip,
       customer_address.ca_city,
       sum(web_sales.ws_sales_price)
FROM dfs.`tmp/web_sales.parquet` AS web_sales,
     dfs.`tmp/customer.parquet` AS customer,
     dfs.`tmp/customer_address.parquet` AS customer_address,
     dfs.`tmp/date_dim.parquet` AS date_dim,
     dfs.`tmp/item.parquet` AS item
WHERE web_sales.ws_bill_customer_sk = customer.c_customer_sk
  AND customer.c_current_addr_sk = customer_address.ca_address_sk
  AND web_sales.ws_item_sk = item.i_item_sk
  AND (SUBSTRING(customer_address.ca_zip,1,5) IN ('85669',
                              '86197',
                              '88274',
                              '83405',
                              '86475',
                              '85392',
                              '85460',
                              '80348',
                              '81792')
       OR item.i_item_id IN
         (SELECT item.i_item_id
          FROM dfs.`tmp/item.parquet` AS item
          WHERE item.i_item_sk IN (2,
                              3,
                              5,
                              7,
                              11,
                              13,
                              17,
                              19,
                              23,
                              29) ))
  AND web_sales.ws_sold_date_sk = date_dim.d_date_sk
  AND date_dim.d_qoy = 2
  AND date_dim.d_year = 2001
GROUP BY customer_address.ca_zip,
         customer_address.ca_city
ORDER BY customer_address.ca_zip,
         customer_address.ca_city
LIMIT 100;

