select
	orders.o_orderpriority,
	count(*) as order_count
from
	dfs.`tmp/orders.parquet` orders
where
	orders.o_orderdate >= date '1993-07-01'
	and orders.o_orderdate < date '1993-10-01'
	and exists (
		select
			*
		from
			dfs.`tmp/lineitem.parquet` lineitem
		where
			lineitem.l_orderkey = orders.o_orderkey
			and lineitem.l_commitdate < lineitem.l_receiptdate
	)
group by
	orders.o_orderpriority
order by
	orders.o_orderpriority;
