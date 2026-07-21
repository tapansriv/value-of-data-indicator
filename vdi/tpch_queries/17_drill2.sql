select
	sum(lineitem.l_extendedprice) / 7.0 as avg_yearly
from
	dfs.`tmp/lineitem.parquet` lineitem,
	dfs.`tmp/part.parquet` part
where
	part.p_partkey = lineitem.l_partkey
	and part.p_brand = 'Brand#23'
	and part.p_container = 'MED BOX'
	and lineitem.l_quantity < (
		select
			0.2 * avg(lineitem.l_quantity)
		from
			dfs.`tmp/lineitem.parquet` lineitem
		where
			lineitem.l_partkey = part.p_partkey
	);
