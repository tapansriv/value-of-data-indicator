select
	customer.c_name,
	customer.c_custkey,
	orders.o_orderkey,
	orders.o_orderdate,
	orders.o_totalprice,
	sum(lineitem.l_quantity)
from
	dfs.`tmp/customer.parquet` customer,
	dfs.`tmp/orders.parquet` orders,
	dfs.`tmp/lineitem.parquet` lineitem
where
	orders.o_orderkey in (
		select
			lineitem.l_orderkey
		from
			dfs.`tmp/lineitem.parquet` lineitem
		group by
			lineitem.l_orderkey having
				sum(lineitem.l_quantity) > 300
	)
	and customer.c_custkey = orders.o_custkey
	and orders.o_orderkey = lineitem.l_orderkey
group by
	customer.c_name,
	customer.c_custkey,
	orders.o_orderkey,
	orders.o_orderdate,
	orders.o_totalprice
order by
	orders.o_totalprice desc,
	orders.o_orderdate
LIMIT 100;
