SELECT customer_address.ca_zip,
       sum(catalog_sales.cs_sales_price)
FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
     dfs.`tmp/customer.parquet` AS customer,
     dfs.`tmp/customer_address.parquet` AS customer_address,
     dfs.`tmp/date_dim.parquet` AS date_dim
WHERE catalog_sales.cs_bill_customer_sk = customer.c_customer_sk
  AND customer.c_current_addr_sk = customer_address.ca_address_sk
  AND (SUBSTRING(customer_address.ca_zip, 1, 5) IN ('85669',
                                '86197',
                                '88274',
                                '83405',
                                '86475',
                                '85392',
                                '85460',
                                '80348',
                                '81792')
       OR customer_address.ca_state IN ('CA',
                       'WA',
                       'GA')
       OR catalog_sales.cs_sales_price > 500)
  AND catalog_sales.cs_sold_date_sk = date_dim.d_date_sk
  AND date_dim.d_qoy = 2
  AND date_dim.d_year = 2001
  AND customer.c_customer_sk < 108250
GROUP BY customer_address.ca_zip
ORDER BY customer_address.ca_zip NULLS FIRST
LIMIT 100;

