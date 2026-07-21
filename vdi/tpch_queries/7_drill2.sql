select
	supp_nation,
	cust_nation,
	l_year,
	sum(volume) as revenue
from
	(
		select
			n1.n_name as supp_nation,
			n2.n_name as cust_nation,
			extract(year from lineitem.l_shipdate) as l_year,
			lineitem.l_extendedprice * (1 - lineitem.l_discount) as volume
		from
			dfs.`tmp/supplier.parquet` supplier,
			dfs.`tmp/lineitem.parquet` lineitem,
			dfs.`tmp/orders.parquet` orders,
			dfs.`tmp/customer.parquet` customer,
			dfs.`tmp/nation.parquet` n1,
			dfs.`tmp/nation.parquet` n2
		where
			supplier.s_suppkey = lineitem.l_suppkey
			and orders.o_orderkey = lineitem.l_orderkey
			and customer.c_custkey = orders.o_custkey
			and supplier.s_nationkey = n1.n_nationkey
			and customer.c_nationkey = n2.n_nationkey
			and (
				(n1.n_name = 'FRANCE' and n2.n_name = 'GERMANY')
				or (n1.n_name = 'GERMANY' and n2.n_name = 'FRANCE')
			)
			and lineitem.l_shipdate between date '1995-01-01' and date '1996-12-31'
	) as shipping
group by
	supp_nation,
	cust_nation,
	l_year
order by
	supp_nation,
	cust_nation,
	l_year;
