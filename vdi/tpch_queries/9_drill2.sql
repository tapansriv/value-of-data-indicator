select
	nation,
	o_year,
	sum(amount) as sum_profit
from
	(
		select
			nation.n_name as nation,
			extract(year from orders.o_orderdate) as o_year,
			lineitem.l_extendedprice * (1 - lineitem.l_discount) - partsupp.ps_supplycost * lineitem.l_quantity as amount
		from
			dfs.`tmp/part.parquet` part,
			dfs.`tmp/supplier.parquet` supplier,
			dfs.`tmp/lineitem.parquet` lineitem,
			dfs.`tmp/partsupp.parquet` partsupp,
			dfs.`tmp/orders.parquet` orders,
			dfs.`tmp/nation.parquet` nation
		where
			supplier.s_suppkey = lineitem.l_suppkey
			and partsupp.ps_suppkey = lineitem.l_suppkey
			and partsupp.ps_partkey = lineitem.l_partkey
			and part.p_partkey = lineitem.l_partkey
			and orders.o_orderkey = lineitem.l_orderkey
			and supplier.s_nationkey = nation.n_nationkey
			and part.p_name like '%green%'
	) as profit
group by
	nation,
	o_year
order by
	nation,
	o_year desc;
