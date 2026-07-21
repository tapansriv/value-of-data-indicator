select
	lineitem.l_orderkey,
	sum(lineitem.l_extendedprice * (1 - lineitem.l_discount)) as revenue,
	orders.o_orderdate,
	orders.o_shippriority
from
	dfs.`tmp/customer.parquet` customer,
	dfs.`tmp/orders.parquet` orders,
	dfs.`tmp/lineitem.parquet` lineitem
where
	customer.c_mktsegment = 'BUILDING'
	and customer.c_custkey = orders.o_custkey
	and lineitem.l_orderkey = orders.o_orderkey
	and orders.o_orderdate < date '1995-03-15'
	and lineitem.l_shipdate > date '1995-03-15'
    and customer.c_custkey < 2250000
group by
	lineitem.l_orderkey,
	orders.o_orderdate,
	orders.o_shippriority
order by
	revenue desc,
	orders.o_orderdate
LIMIT 10;


