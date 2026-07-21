select
	supplier.s_suppkey,
	supplier.s_name,
	supplier.s_address,
	supplier.s_phone,
	total_revenue
from
	dfs.`tmp/supplier.parquet` supplier,
    (
        SELECT
            lineitem.l_suppkey AS supplier_no,
            sum(lineitem.l_extendedprice * (1 - lineitem.l_discount)) AS total_revenue
        FROM
            dfs.`tmp/lineitem.parquet` lineitem
        WHERE
            lineitem.l_shipdate >= CAST('1996-01-01' AS date)
            AND lineitem.l_shipdate < CAST('1996-04-01' AS date)
        GROUP BY
            supplier_no) revenue0
where
	supplier.s_suppkey = supplier_no
    AND total_revenue = (
        SELECT
            max(total_revenue)
        FROM (
            SELECT
                lineitem.l_suppkey AS supplier_no,
                sum(lineitem.l_extendedprice * (1 - lineitem.l_discount)) AS total_revenue
            FROM
                dfs.`tmp/lineitem.parquet` lineitem
            WHERE
                lineitem.l_shipdate >= CAST('1996-01-01' AS date)
                AND lineitem.l_shipdate < CAST('1996-04-01' AS date)
            GROUP BY
                supplier_no) revenue1)
order by
	supplier.s_suppkey;
