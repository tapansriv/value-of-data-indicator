select
	supplier.s_acctbal,
	supplier.s_name,
	nation.n_name,
	part.p_partkey,
	part.p_mfgr,
	supplier.s_address,
	supplier.s_phone,
	supplier.s_comment
from
	dfs.`tmp/part.parquet` part,
	dfs.`tmp/supplier.parquet` supplier,
	dfs.`tmp/partsupp.parquet` partsupp,
	dfs.`tmp/nation.parquet` nation,
	dfs.`tmp/region.parquet` region
where
	part.p_partkey = partsupp.ps_partkey
	and supplier.s_suppkey = partsupp.ps_suppkey
	and part.p_size = 15
	and part.p_type like '%BRASS'
	and supplier.s_nationkey = nation.n_nationkey
	and nation.n_regionkey = region.r_regionkey
	and region.r_name = 'EUROPE'
	and partsupp.ps_supplycost = (
		select
			min(partsupp.ps_supplycost)
		from
			dfs.`tmp/partsupp.parquet` partsupp,
			dfs.`tmp/supplier.parquet` supplier,
			dfs.`tmp/nation.parquet` nation,
			dfs.`tmp/region.parquet` region
		where
			part.p_partkey = partsupp.ps_partkey
			and supplier.s_suppkey = partsupp.ps_suppkey
			and supplier.s_nationkey = nation.n_nationkey
			and nation.n_regionkey = region.r_regionkey
			and region.r_name = 'EUROPE'
	)
order by
	supplier.s_acctbal desc,
	nation.n_name,
	supplier.s_name,
	part.p_partkey
LIMIT 100;
