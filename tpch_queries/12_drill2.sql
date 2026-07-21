select
	lineitem.l_shipmode,
	sum(case
		when orders.o_orderpriority = '1-URGENT'
			or orders.o_orderpriority = '2-HIGH'
			then 1
		else 0
	end) as high_line_count,
	sum(case
		when orders.o_orderpriority <> '1-URGENT'
			and orders.o_orderpriority <> '2-HIGH'
			then 1
		else 0
	end) as low_line_count
from
	dfs.`tmp/orders.parquet` orders,
	dfs.`tmp/lineitem.parquet` lineitem
where
	orders.o_orderkey = lineitem.l_orderkey
	and lineitem.l_shipmode in ('MAIL', 'SHIP')
	and lineitem.l_commitdate < lineitem.l_receiptdate
	and lineitem.l_shipdate < lineitem.l_commitdate
	and lineitem.l_receiptdate >= date '1994-01-01'
	and lineitem.l_receiptdate < date '1995-01-01'
group by
	lineitem.l_shipmode
order by
	lineitem.l_shipmode;
