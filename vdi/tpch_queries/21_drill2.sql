select
	supplier.s_name,
	count(*) as numwait
from
	dfs.`tmp/supplier.parquet` supplier,
	dfs.`tmp/lineitem.parquet` l1,
	dfs.`tmp/orders.parquet` orders,
	dfs.`tmp/nation.parquet` nation
where
	supplier.s_suppkey = l1.l_suppkey
	and orders.o_orderkey = l1.l_orderkey
	and orders.o_orderstatus = 'F'
	and l1.l_receiptdate > l1.l_commitdate
	and exists (
		select
			*
		from
			dfs.`tmp/lineitem.parquet` l2
		where
			l2.l_orderkey = l1.l_orderkey
			and l2.l_suppkey <> l1.l_suppkey
	)
	and not exists (
		select
			*
		from
			dfs.`tmp/lineitem.parquet` l3
		where
			l3.l_orderkey = l1.l_orderkey
			and l3.l_suppkey <> l1.l_suppkey
			and l3.l_receiptdate > l3.l_commitdate
	)
	and supplier.s_nationkey = nation.n_nationkey
	and nation.n_name = 'SAUDI ARABIA'
group by
	supplier.s_name
order by
	numwait desc,
	supplier.s_name
LIMIT 100;
