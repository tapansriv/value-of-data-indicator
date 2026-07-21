select
	sum(lineitem.l_extendedprice * lineitem.l_discount) as revenue
from
	dfs.`tmp/lineitem.parquet` lineitem
where
	lineitem.l_shipdate >= date '1994-01-01'
	and lineitem.l_shipdate < date '1995-01-01'
	and lineitem.l_discount between .05 and .07
	and lineitem.l_quantity < 24;
