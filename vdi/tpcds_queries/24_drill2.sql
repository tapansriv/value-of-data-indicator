WITH ssales AS
  (SELECT customer.c_last_name,
          customer.c_first_name,
          store.s_store_name,
          customer_address.ca_state,
          store.s_state,
          item.i_color,
          item.i_current_price,
          item.i_manager_id,
          item.i_units,
          item.i_size,
          sum(store_sales.ss_net_paid) netpaid
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/store_returns.parquet` AS store_returns,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/item.parquet` AS item,
        dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/customer_address.parquet` AS customer_address
   WHERE store_sales.ss_ticket_number = store_returns.sr_ticket_number
     AND store_sales.ss_item_sk = store_returns.sr_item_sk
     AND store_sales.ss_customer_sk = customer.c_customer_sk
     AND store_sales.ss_item_sk = item.i_item_sk
     AND store_sales.ss_store_sk = store.s_store_sk
     AND customer.c_current_addr_sk = customer_address.ca_address_sk
     AND customer.c_birth_country <> upper(customer_address.ca_country)
     AND store.s_zip = customer_address.ca_zip
     AND store.s_market_id=8
   GROUP BY customer.c_last_name,
            customer.c_first_name,
            store.s_store_name,
            customer_address.ca_state,
            store.s_state,
            item.i_color,
            item.i_current_price,
            item.i_manager_id,
            item.i_units,
            item.i_size)
SELECT ssales.c_last_name,
       ssales.c_first_name,
       ssales.s_store_name,
       sum(ssales.netpaid) paid
FROM ssales
WHERE ssales.i_color = 'peach'
GROUP BY ssales.c_last_name,
         ssales.c_first_name,
         ssales.s_store_name
HAVING sum(netpaid) >
  (SELECT 0.05*avg(netpaid)
   FROM ssales)
ORDER BY ssales.c_last_name,
         ssales.c_first_name,
         ssales.s_store_name ;
