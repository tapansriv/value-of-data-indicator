-- using default substitutions


select
	sum(lineitem.l_extendedprice* (1 - lineitem.l_discount)) as revenue
from
	dfs.`tmp/lineitem.parquet` lineitem,
	dfs.`tmp/part.parquet` part
where
	(
		part.p_partkey = lineitem.l_partkey
		and part.p_brand = 'Brand#12'
		and part.p_container in ('SM CASE', 'SM BOX', 'SM PACK', 'SM PKG')
		and lineitem.l_quantity >= 1 and lineitem.l_quantity <= 1 + 10
		and part.p_size between 1 and 5
		and lineitem.l_shipmode in ('AIR', 'AIR REG')
		and lineitem.l_shipinstruct = 'DELIVER IN PERSON'
	)
	or
	(
		part.p_partkey = lineitem.l_partkey
		and part.p_brand = 'Brand#23'
		and part.p_container in ('MED BAG', 'MED BOX', 'MED PKG', 'MED PACK')
		and lineitem.l_quantity >= 10 and lineitem.l_quantity <= 10 + 10
		and part.p_size between 1 and 10
		and lineitem.l_shipmode in ('AIR', 'AIR REG')
		and lineitem.l_shipinstruct = 'DELIVER IN PERSON'
	)
	or
	(
		part.p_partkey = lineitem.l_partkey
		and part.p_brand = 'Brand#34'
		and part.p_container in ('LG CASE', 'LG BOX', 'LG PACK', 'LG PKG')
		and lineitem.l_quantity >= 20 and lineitem.l_quantity <= 20 + 10
		and part.p_size between 1 and 15
		and lineitem.l_shipmode in ('AIR', 'AIR REG')
		and lineitem.l_shipinstruct = 'DELIVER IN PERSON'
	);
