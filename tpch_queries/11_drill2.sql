select
	partsupp.ps_partkey,
	sum(partsupp.ps_supplycost * partsupp.ps_availqty) as value
from
	dfs.`tmp/partsupp.parquet` partsupp,
	dfs.`tmp/supplier.parquet` supplier,
	dfs.`tmp/nation.parquet` nation
where
	partsupp.ps_suppkey = supplier.s_suppkey
	and supplier.s_nationkey = nation.n_nationkey
	and nation.n_name = 'GERMANY'
group by
	partsupp.ps_partkey having
		sum(partsupp.ps_supplycost * partsupp.ps_availqty) > (
			select
				sum(partsupp.ps_supplycost * partsupp.ps_availqty) * 0.0001000000
			from
				dfs.`tmp/partsupp.parquet` partsupp,
				dfs.`tmp/supplier.parquet` supplier,
				dfs.`tmp/nation.parquet` nation
			where
				partsupp.ps_suppkey = supplier.s_suppkey
				and supplier.s_nationkey = nation.n_nationkey
				and nation.n_name = 'GERMANY'
		)
order by
	value desc;
