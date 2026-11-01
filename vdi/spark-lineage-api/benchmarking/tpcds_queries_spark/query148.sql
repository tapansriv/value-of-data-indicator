-- R2D7 rg-selective: base query84, target store_returns, level 1/4, authored 2026-10-21
-- start query 84 in stream 0 using template query84.tpl 
SELECT c_customer_id   AS customer_id, 
               c_last_name 
               || ', ' 
               || c_first_name AS customername 
FROM   customer, 
       customer_address, 
       customer_demographics, 
       household_demographics, 
       income_band, 
       store_returns 
WHERE  ca_city = 'Green Acres' 
       AND c_current_addr_sk = ca_address_sk 
       AND ib_lower_bound >= 54986 
       AND ib_upper_bound <= 54986 + 50000 
       AND ib_income_band_sk = hd_income_band_sk 
       AND cd_demo_sk = c_current_cdemo_sk 
       AND hd_demo_sk = c_current_hdemo_sk 
       AND sr_cdemo_sk = cd_demo_sk 
       AND sr_ticket_number <= 106939
ORDER  BY c_customer_id
LIMIT 100; 
