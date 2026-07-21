select
	supplier.s_name,
	supplier.s_address
from
	dfs.`tmp/supplier.parquet` supplier,
	dfs.`tmp/nation.parquet` nation
where
	supplier.s_suppkey in (
		select
			partsupp.ps_suppkey
		from
			dfs.`tmp/partsupp.parquet` partsupp
		where
			partsupp.ps_partkey in (
				select
					part.p_partkey
				from
					dfs.`tmp/part.parquet` part
				where
					part.p_name like 'forest%'
			)
			and partsupp.ps_availqty > (
				select
					0.5 * sum(lineitem.l_quantity)
				from
					dfs.`tmp/lineitem.parquet` lineitem
				where
					lineitem.l_partkey = partsupp.ps_partkey
					and lineitem.l_suppkey = partsupp.ps_suppkey
					and lineitem.l_shipdate >= date '1994-01-01'
					and lineitem.l_shipdate < date '1995-01-01'
			)
	)
	and supplier.s_nationkey = nation.n_nationkey
	and nation.n_name = 'CANADA'
order by
	supplier.s_name;
