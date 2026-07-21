select
	lineitem.l_returnflag,
	lineitem.l_linestatus,
	sum(lineitem.l_quantity) as sum_qty,
	sum(lineitem.l_extendedprice) as sum_base_price,
	sum(lineitem.l_extendedprice * (1 - lineitem.l_discount)) as sum_disc_price,
	sum(lineitem.l_extendedprice * (1 - lineitem.l_discount) * (1 + lineitem.l_tax)) as sum_charge,
	avg(lineitem.l_quantity) as avg_qty,
	avg(lineitem.l_extendedprice) as avg_price,
	avg(lineitem.l_discount) as avg_disc,
	count(*) as count_order
from
	dfs.`tmp/lineitem.parquet` lineitem
where
	lineitem.l_shipdate <= date '1998-09-02'
    AND lineitem.l_orderkey < 9000000
group by
	lineitem.l_returnflag,
	lineitem.l_linestatus
order by
	lineitem.l_returnflag,
	lineitem.l_linestatus;
