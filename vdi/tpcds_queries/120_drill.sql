SELECT c_customer_id AS customer_id ,
       concat(concat(coalesce(c_last_name, '') , ', '), coalesce(c_first_name, '')) AS customername
FROM dfs.`tmp/customer.parquet` AS customer ,
     dfs.`tmp/customer_address.parquet` AS customer_address ,
     dfs.`tmp/customer_demographics.parquet` AS customer_demographics ,
     dfs.`tmp/household_demographics.parquet` AS household_demographics ,
     dfs.`tmp/income_band.parquet` AS income_band ,
     dfs.`tmp/store_returns.parquet` AS store_returns
WHERE ca_city = 'Edgewood'
  AND c_current_addr_sk = ca_address_sk
  AND ib_lower_bound >= 38128
  AND ib_upper_bound <= 38128 + 50000
  AND ib_income_band_sk = hd_income_band_sk
  AND cd_demo_sk = c_current_cdemo_sk
  AND hd_demo_sk = c_current_hdemo_sk
  AND sr_cdemo_sk = cd_demo_sk
  AND sr_item_sk < 2000
ORDER BY c_customer_id NULLS FIRST
LIMIT 100;
