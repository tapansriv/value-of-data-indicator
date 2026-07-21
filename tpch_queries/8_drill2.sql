select
	o_year,
	sum(case
		when nation = 'BRAZIL' then volume
		else 0
	end) / sum(volume) as mkt_share
from
	(
		select
			extract(year from orders.o_orderdate) as o_year,
			lineitem.l_extendedprice * (1 - lineitem.l_discount) as volume,
			n2.n_name as nation
		from
			dfs.`tmp/part.parquet` part,
			dfs.`tmp/supplier.parquet` supplier,
			dfs.`tmp/lineitem.parquet` lineitem,
			dfs.`tmp/orders.parquet` orders,
			dfs.`tmp/customer.parquet` customer,
			dfs.`tmp/nation.parquet` n1,
			dfs.`tmp/nation.parquet` n2,
			dfs.`tmp/region.parquet` region
		where
			part.p_partkey = lineitem.l_partkey
			and supplier.s_suppkey = lineitem.l_suppkey
			and lineitem.l_orderkey = orders.o_orderkey
			and orders.o_custkey = customer.c_custkey
			and customer.c_nationkey = n1.n_nationkey
			and n1.n_regionkey = region.r_regionkey
			and region.r_name = 'AMERICA'
			and supplier.s_nationkey = n2.n_nationkey
			and orders.o_orderdate between date '1995-01-01' and date '1996-12-31'
			and part.p_type = 'ECONOMY ANODIZED STEEL'
	) as all_nations
group by
	o_year
order by
	o_year;
