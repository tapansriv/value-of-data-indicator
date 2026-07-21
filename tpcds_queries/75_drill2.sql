WITH all_sales AS
  ( SELECT date_dim.d_year ,
           item.i_brand_id ,
           item.i_class_id ,
           item.i_category_id ,
           item.i_manufact_id ,
           SUM(sales_cnt) AS sales_cnt ,
           SUM(sales_amt) AS sales_amt
   FROM
     (SELECT date_dim.d_year ,
             item.i_brand_id ,
             item.i_class_id ,
             item.i_category_id ,
             item.i_manufact_id ,
             catalog_sales.cs_quantity - COALESCE(catalog_returns.cr_return_quantity,0) AS sales_cnt ,
             catalog_sales.cs_ext_sales_price - COALESCE(catalog_returns.cr_return_amount,0.0) AS sales_amt
      FROM dfs.`tmp/catalog_sales.parquet` AS catalog_sales
      JOIN dfs.`tmp/item.parquet` ON item.i_item_sk=cs_item_sk
      JOIN dfs.`tmp/date_dim.parquet` AS date_dim ON date_dim.d_date_sk=cs_sold_date_sk
      LEFT JOIN dfs.`tmp/catalog_returns.parquet` AS catalog_returns ON (catalog_sales.cs_order_number=cr_order_number
                                    AND catalog_sales.cs_item_sk=cr_item_sk)
      WHERE item.i_category='Books'
      UNION SELECT date_dim.d_year ,
                   item.i_brand_id ,
                   item.i_class_id ,
                   item.i_category_id ,
                   item.i_manufact_id ,
                   store_sales.ss_quantity - COALESCE(store_returns.sr_return_quantity,0) AS sales_cnt ,
                   store_sales.ss_ext_sales_price - COALESCE(store_returns.sr_return_amt,0.0) AS sales_amt
      FROM dfs.`tmp/store_sales.parquet` AS store_sales
      JOIN dfs.`tmp/item.parquet` ON item.i_item_sk=ss_item_sk
      JOIN dfs.`tmp/date_dim.parquet` AS date_dim ON date_dim.d_date_sk=ss_sold_date_sk
      LEFT JOIN dfs.`tmp/store_returns.parquet` AS store_returns ON (store_sales.ss_ticket_number=sr_ticket_number
                                  AND store_sales.ss_item_sk=sr_item_sk)
      WHERE item.i_category='Books'
      UNION SELECT date_dim.d_year ,
                   item.i_brand_id ,
                   item.i_class_id ,
                   item.i_category_id ,
                   item.i_manufact_id ,
                   web_sales.ws_quantity - COALESCE(web_returns.wr_return_quantity,0) AS sales_cnt ,
                   web_sales.ws_ext_sales_price - COALESCE(web_returns.wr_return_amt,0.0) AS sales_amt
      FROM dfs.`tmp/web_sales.parquet` AS web_sales
      JOIN dfs.`tmp/item.parquet` ON item.i_item_sk=ws_item_sk
      JOIN dfs.`tmp/date_dim.parquet` AS date_dim ON date_dim.d_date_sk=ws_sold_date_sk
      LEFT JOIN dfs.`tmp/web_returns.parquet` AS web_returns ON (web_sales.ws_order_number=wr_order_number
                                AND web_sales.ws_item_sk=wr_item_sk)
      WHERE item.i_category='Books') sales_detail
   GROUP BY date_dim.d_year,
            item.i_brand_id,
            item.i_class_id,
            item.i_category_id,
            item.i_manufact_id)
SELECT prev_yr.d_year AS prev_year ,
       curr_yr.d_year AS year_ ,
       curr_yr.i_brand_id ,
       curr_yr.i_class_id ,
       curr_yr.i_category_id ,
       curr_yr.i_manufact_id ,
       prev_yr.sales_cnt AS prev_yr_cnt ,
       curr_yr.sales_cnt AS curr_yr_cnt ,
       curr_yr.sales_cnt-prev_yr.sales_cnt AS sales_cnt_diff ,
       curr_yr.sales_amt-prev_yr.sales_amt AS sales_amt_diff
FROM all_sales curr_yr,
     all_sales prev_yr
WHERE curr_yr.i_brand_id=prev_yr.i_brand_id
  AND curr_yr.i_class_id=prev_yr.i_class_id
  AND curr_yr.i_category_id=prev_yr.i_category_id
  AND curr_yr.i_manufact_id=prev_yr.i_manufact_id
  AND curr_yr.d_year=2002
  AND prev_yr.d_year=2002-1
  AND CAST(curr_yr.sales_cnt AS DECIMAL(17,2))/CAST(prev_yr.sales_cnt AS DECIMAL(17,2))<0.9
ORDER BY sales_cnt_diff,
         sales_amt_diff
LIMIT 100;

