SELECT ca_zip,
       sum(cs_sales_price)
FROM 's3://vod-tpcds-10gb/catalog_sales.parquet' AS catalog_sales,
     's3://vod-tpcds-10gb/customer.parquet' AS customer,
     's3://vod-tpcds-10gb/customer_address.parquet' AS customer_address,
     's3://vod-tpcds-10gb/date_dim.parquet' AS date_dim
WHERE cs_bill_customer_sk = c_customer_sk
  AND c_current_addr_sk = ca_address_sk
  AND (SUBSTRING(ca_zip, 1, 5) IN ('85669',
                                '86197',
                                '88274',
                                '83405',
                                '86475',
                                '85392',
                                '85460',
                                '80348',
                                '81792')
       OR ca_state IN ('CA',
                       'WA',
                       'GA')
       OR cs_sales_price > 500)
  AND cs_sold_date_sk = d_date_sk
  AND d_qoy = 2
  AND d_year = 2001
GROUP BY ca_zip
ORDER BY ca_zip NULLS FIRST
LIMIT 100;

