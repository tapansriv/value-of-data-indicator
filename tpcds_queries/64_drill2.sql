WITH cs_ui AS
  (SELECT catalog_sales.cs_item_sk,
          sum(catalog_sales.cs_ext_list_price) AS sale,
          sum(catalog_returns.cr_refunded_cash+cr_reversed_charge+cr_store_credit) AS refund
   FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales,
        dfs.`tmp/catalog_returns.parquet` AS catalog_returns
   WHERE catalog_sales.cs_item_sk = catalog_returns.cr_item_sk
     AND catalog_sales.cs_order_number = catalog_returns.cr_order_number
   GROUP BY catalog_sales.cs_item_sk
   HAVING sum(catalog_sales.cs_ext_list_price)>2*sum(catalog_returns.cr_refunded_cash+cr_reversed_charge+cr_store_credit)),
cross_sales AS
  (SELECT item.i_product_name product_name,
          item.i_item_sk item_sk,
          store.s_store_name store_name,
          store.s_zip store_zip,
          ad1.ca_street_number b_street_number,
          ad1.ca_street_name b_street_name,
          ad1.ca_city b_city,
          ad1.ca_zip b_zip,
          ad2.ca_street_number c_street_number,
          ad2.ca_street_name c_street_name,
          ad2.ca_city c_city,
          ad2.ca_zip c_zip,
          d1.d_year AS syear,
          d2.d_year AS fsyear,
          d3.d_year s2year,
          count(*) cnt,
          sum(store_sales.ss_wholesale_cost) s1,
          sum(store_sales.ss_list_price) s2,
          sum(store_sales.ss_coupon_amt) s3
   FROM dfs.`tmp/store_sales.parquet` AS store_sales,
        dfs.`tmp/store_returns.parquet` AS store_returns,
        cs_ui,
        dfs.`tmp/date_dim.parquet` d1,
        dfs.`tmp/date_dim.parquet` d2,
        dfs.`tmp/date_dim.parquet` d3,
        dfs.`tmp/store.parquet` AS store,
        dfs.`tmp/customer.parquet` AS customer,
        dfs.`tmp/customer_demographics.parquet` cd1,
        dfs.`tmp/customer_demographics.parquet` cd2,
        dfs.`tmp/promotion.parquet` AS promotion,
        dfs.`tmp/household_demographics.parquet` hd1,
        dfs.`tmp/household_demographics.parquet` hd2,
        dfs.`tmp/customer_address.parquet` ad1,
        dfs.`tmp/customer_address.parquet` ad2,
        dfs.`tmp/income_band.parquet` ib1,
        dfs.`tmp/income_band.parquet` ib2,
        dfs.`tmp/item.parquet` AS item
   WHERE store_sales.ss_store_sk = store.s_store_sk
     AND store_sales.ss_sold_date_sk = d1.d_date_sk
     AND store_sales.ss_customer_sk = customer.c_customer_sk
     AND store_sales.ss_cdemo_sk= cd1.cd_demo_sk
     AND store_sales.ss_hdemo_sk = hd1.hd_demo_sk
     AND store_sales.ss_addr_sk = ad1.ca_address_sk
     AND store_sales.ss_item_sk = item.i_item_sk
     AND store_sales.ss_item_sk = store_returns.sr_item_sk
     AND store_sales.ss_ticket_number = store_returns.sr_ticket_number
     AND store_sales.ss_item_sk = cs_ui.cs_item_sk
     AND customer.c_current_cdemo_sk = cd2.cd_demo_sk
     AND customer.c_current_hdemo_sk = hd2.hd_demo_sk
     AND customer.c_current_addr_sk = ad2.ca_address_sk
     AND customer.c_first_sales_date_sk = d2.d_date_sk
     AND customer.c_first_shipto_date_sk = d3.d_date_sk
     AND store_sales.ss_promo_sk = promotion.p_promo_sk
     AND hd1.hd_income_band_sk = ib1.ib_income_band_sk
     AND hd2.hd_income_band_sk = ib2.ib_income_band_sk
     AND cd1.cd_marital_status <> cd2.cd_marital_status
     AND item.i_color IN ('purple',
                     'burlywood',
                     'indian',
                     'spring',
                     'floral',
                     'medium')
     AND item.i_current_price BETWEEN 64 AND 64 + 10
     AND item.i_current_price BETWEEN 64 + 1 AND 64 + 15
   GROUP BY item.i_product_name,
            item.i_item_sk,
            store.s_store_name,
            store.s_zip,
            ad1.ca_street_number,
            ad1.ca_street_name,
            ad1.ca_city,
            ad1.ca_zip,
            ad2.ca_street_number,
            ad2.ca_street_name,
            ad2.ca_city,
            ad2.ca_zip,
            d1.d_year,
            d2.d_year,
            d3.d_year)
SELECT cs1.product_name,
       cs1.store_name,
       cs1.store_zip,
       cs1.b_street_number,
       cs1.b_street_name,
       cs1.b_city,
       cs1.b_zip,
       cs1.c_street_number,
       cs1.c_street_name,
       cs1.c_city,
       cs1.c_zip,
       cs1.syear cs1syear,
       cs1.cnt cs1cnt,
       cs1.s1 AS s11,
       cs1.s2 AS s21,
       cs1.s3 AS s31,
       cs2.s1 AS s12,
       cs2.s2 AS s22,
       cs2.s3 AS s32,
       cs2.syear,
       cs2.cnt
FROM cross_sales cs1,
     cross_sales cs2
WHERE cs1.item_sk=cs2.item_sk
  AND cs1.syear = 1999
  AND cs2.syear = 1999 + 1
  AND cs2.cnt <= cs1.cnt
  AND cs1.store_name = cs2.store_name
  AND cs1.store_zip = cs2.store_zip
ORDER BY cs1.product_name,
         cs1.store_name,
         cs2.cnt,
         cs1.s1,
         cs2.s1;

