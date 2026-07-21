select
	customer.c_custkey,
	customer.c_name,
	sum(lineitem.l_extendedprice * (1 - lineitem.l_discount)) as revenue,
	customer.c_acctbal,
	nation.n_name,
	customer.c_address,
	customer.c_phone,
	customer.c_comment
from
	dfs.`tmp/customer.parquet` customer,
	dfs.`tmp/orders.parquet` orders,
	dfs.`tmp/lineitem.parquet` lineitem,
	dfs.`tmp/nation.parquet` nation
where
	customer.c_custkey = orders.o_custkey
	and lineitem.l_orderkey = orders.o_orderkey
	and orders.o_orderdate >= date '1993-10-01'
	and orders.o_orderdate < date '1994-01-01'
	and lineitem.l_returnflag = 'R'
	and customer.c_nationkey = nation.n_nationkey
group by
	customer.c_custkey,
	customer.c_name,
	customer.c_acctbal,
	customer.c_phone,
	nation.n_name,
	customer.c_address,
	customer.c_comment
order by
	revenue desc
LIMIT 20;
