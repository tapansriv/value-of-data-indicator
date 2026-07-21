select
	100.00 * sum(case
		when part.p_type like 'PROMO%'
			then lineitem.l_extendedprice * (1 - lineitem.l_discount)
		else 0
	end) / sum(lineitem.l_extendedprice * (1 - lineitem.l_discount)) as promo_revenue
from
	dfs.`tmp/lineitem.parquet` lineitem,
	dfs.`tmp/part.parquet` part
where
	lineitem.l_partkey = part.p_partkey
	and lineitem.l_shipdate >= date '1995-09-01'
	and lineitem.l_shipdate < date '1995-10-01'
    and part.p_partkey < 3000000;



