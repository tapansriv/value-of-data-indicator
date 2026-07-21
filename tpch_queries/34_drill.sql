select
	n_name,
	sum(l_extendedprice * (1 - l_discount)) as revenue
from
	dfs.`tmp/customer.parquet` customer,
	dfs.`tmp/orders.parquet` orders,
	dfs.`tmp/lineitem.parquet` lineitem,
	dfs.`tmp/supplier.parquet` supplier,
	dfs.`tmp/nation.parquet` nation,
	dfs.`tmp/region.parquet` region
where
	c_custkey = o_custkey
	and l_orderkey = o_orderkey
	and l_suppkey = s_suppkey
	and c_nationkey = s_nationkey
	and s_nationkey = n_nationkey
	and n_regionkey = r_regionkey
	and r_name = 'ASIA'
	and o_orderdate >= date '1994-01-01'
	and o_orderdate < date '1995-01-01'
    and o_orderkey < 135000000
group by
	n_name
order by
	revenue desc;




