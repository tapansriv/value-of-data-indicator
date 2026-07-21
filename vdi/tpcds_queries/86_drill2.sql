 with results as
( select sum(web_sales.ws_net_paid) as total_sum, item.i_category, item.i_class, 0 as g_category, 0 as g_class
 from
    dfs.`tmp/web_sales.parquet` AS web_sales
   ,dfs.`tmp/date_dim.parquet` d1
   ,dfs.`tmp/item.parquet` AS item
 where
    d1.d_month_seq between 1200 and 1200+11
 and d1.d_date_sk = web_sales.ws_sold_date_sk
 and item.i_item_sk  = web_sales.ws_item_sk
 group by item.i_category,item.i_class
 ) ,

 results_rollup as
( select total_sum ,item.i_category ,item.i_class, g_category, g_class, 0 as lochierarchy from results
  union
  select sum(total_sum) as total_sum, item.i_category, NULL as item.i_class, 0 as g_category, 1 as g_class, 1 as lochierarchy from results group by item.i_category
  union
  select sum(total_sum) as total_sum, NULL as item.i_category, NULL as item.i_class, 1 as g_category, 1 as g_class, 2 as lochierarchy from results)
select
 total_sum ,item.i_category ,item.i_class, lochierarchy
   ,rank() over (
  partition by lochierarchy,
  case when g_class = 0 then item.i_category end
  order by total_sum desc) as rank_within_parent
 from
 results_rollup
 order by
   lochierarchy desc NULLS FIRST,
   case when lochierarchy = 0 then item.i_category end NULLS FIRST,
   rank_within_parent NULLS FIRST
LIMIT 100;
