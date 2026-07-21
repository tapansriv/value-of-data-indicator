select
	part.p_brand,
	part.p_type,
	part.p_size,
	count(distinct partsupp.ps_suppkey) as supplier_cnt
from
	dfs.`tmp/partsupp.parquet` partsupp,
	dfs.`tmp/part.parquet` part
where
	part.p_partkey = partsupp.ps_partkey
	and part.p_brand <> 'Brand#45'
	and part.p_type not like 'MEDIUM POLISHED%'
	and part.p_size in (49, 14, 23, 45, 19, 3, 36, 9)
	and partsupp.ps_suppkey not in (
		select
			supplier.s_suppkey
		from
			dfs.`tmp/supplier.parquet` supplier
		where
			supplier.s_comment like '%Customer%Complaints%'
	)
group by
	part.p_brand,
	part.p_type,
	part.p_size
order by
	supplier_cnt desc,
	part.p_brand,
	part.p_type,
	part.p_size;
