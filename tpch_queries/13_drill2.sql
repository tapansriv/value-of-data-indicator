select
	c_count,
	count(*) as custdist
from
	(
		select
			customer.c_custkey,
			count(orders.o_orderkey)
		from
			dfs.`tmp/customer.parquet` customer left outer join dfs.`tmp/orders.parquet` orders on
				customer.c_custkey = orders.o_custkey
				and orders.o_comment not like '%special%requests%'
		group by
			customer.c_custkey
	) as c_orders (customer.c_custkey, c_count)
group by
	c_count
order by
	custdist desc,
	c_count desc;
