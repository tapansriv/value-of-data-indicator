SELECT call_center.cc_call_center_id Call_Center,
       call_center.cc_name Call_Center_Name,
       call_center.cc_manager Manager,
       sum(catalog_returns.cr_net_loss) Returns_Loss
FROM dfs.`tmp/call_center.parquet` AS call_center,
     dfs.`tmp/catalog_returns.parquet` AS catalog_returns,
     dfs.`tmp/date_dim.parquet` AS date_dim,
     dfs.`tmp/customer.parquet` AS customer,
     dfs.`tmp/customer_address.parquet` AS customer_address,
     dfs.`tmp/customer_demographics.parquet` AS customer_demographics,
     dfs.`tmp/household_demographics.parquet` AS household_demographics
WHERE catalog_returns.cr_call_center_sk = call_center.cc_call_center_sk
  AND catalog_returns.cr_returned_date_sk = date_dim.d_date_sk
  AND catalog_returns.cr_returning_customer_sk= customer.c_customer_sk
  AND customer_demographics.cd_demo_sk = customer.c_current_cdemo_sk
  AND household_demographics.hd_demo_sk = customer.c_current_hdemo_sk
  AND customer_address.ca_address_sk = customer.c_current_addr_sk
  AND date_dim.d_year = 1998
  AND date_dim.d_moy = 11
  AND ((customer_demographics.cd_marital_status = 'M'
        AND customer_demographics.cd_education_status = 'Unknown') or(customer_demographics.cd_marital_status = 'W'
                                                AND customer_demographics.cd_education_status = 'Advanced Degree'))
  AND household_demographics.hd_buy_potential LIKE 'Unknown%'
  AND customer_address.ca_gmt_offset = -7
  AND catalog_returns.cr_item_sk < 2000
GROUP BY call_center.cc_call_center_id,
         call_center.cc_name,
         call_center.cc_manager,
         customer_demographics.cd_marital_status,
         customer_demographics.cd_education_status
ORDER BY sum(catalog_returns.cr_net_loss) DESC;

