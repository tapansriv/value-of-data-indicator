SELECT customer.c_customer_id AS customer_id ,
       concat(concat(coalesce(customer.c_last_name, '') , ', '), coalesce(customer.c_first_name, '')) AS customername
FROM dfs.`tmp/customer.parquet` AS customer ,
     dfs.`tmp/customer_address.parquet` AS customer_address ,
     dfs.`tmp/customer_demographics.parquet` AS customer_demographics ,
     dfs.`tmp/household_demographics.parquet` AS household_demographics ,
     dfs.`tmp/income_band.parquet` AS income_band ,
     dfs.`tmp/store_returns.parquet` AS store_returns
WHERE customer_address.ca_city = 'Edgewood'
  AND customer.c_current_addr_sk = customer_address.ca_address_sk
  AND income_band.ib_lower_bound >= 38128
  AND income_band.ib_upper_bound <= 38128 + 50000
  AND income_band.ib_income_band_sk = household_demographics.hd_income_band_sk
  AND customer_demographics.cd_demo_sk = customer.c_current_cdemo_sk
  AND household_demographics.hd_demo_sk = customer.c_current_hdemo_sk
  AND store_returns.sr_cdemo_sk = customer_demographics.cd_demo_sk
  AND store_returns.sr_item_sk < 30000
ORDER BY customer.c_customer_id NULLS FIRST
LIMIT 100;
