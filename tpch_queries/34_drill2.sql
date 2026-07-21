select
	nation.n_name,
	sum(lineitem.l_extendedprice * (1 - lineitem.l_discount)) as revenue
from
	dfs.`tmp/customer.parquet` customer,
	dfs.`tmp/orders.parquet` orders,
	dfs.`tmp/lineitem.parquet` lineitem,
	dfs.`tmp/supplier.parquet` supplier,
	dfs.`tmp/nation.parquet` nation,
	dfs.`tmp/region.parquet` region
where
	customer.c_custkey = orders.o_custkey
	and lineitem.l_orderkey = orders.o_orderkey
	and lineitem.l_suppkey = supplier.s_suppkey
	and customer.c_nationkey = supplier.s_nationkey
	and supplier.s_nationkey = nation.n_nationkey
	and nation.n_regionkey = region.r_regionkey
	and region.r_name = 'ASIA'
	and orders.o_orderdate >= date '1994-01-01'
	and orders.o_orderdate < date '1995-01-01'
    and orders.o_orderkey < 135000000
group by
	nation.n_name
order by
	revenue desc;




