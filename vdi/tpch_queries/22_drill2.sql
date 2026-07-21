select
	cntrycode,
	count(*) as numcust,
	sum(customer.c_acctbal) as totacctbal
from
	(
		select
			substring(customer.c_phone from 1 for 2) as cntrycode,
			customer.c_acctbal
		from
			dfs.`tmp/customer.parquet` customer
		where
			substring(customer.c_phone from 1 for 2) in
				('13', '31', '23', '29', '30', '18', '17')
			and customer.c_acctbal > (
				select
					avg(customer.c_acctbal)
				from
					dfs.`tmp/customer.parquet` customer
				where
					customer.c_acctbal > 0.00
					and substring(customer.c_phone from 1 for 2) in
						('13', '31', '23', '29', '30', '18', '17')
			)
			and not exists (
				select
					*
				from
					dfs.`tmp/orders.parquet` orders
				where
					orders.o_custkey = customer.c_custkey
			)
	) as custsale
group by
	cntrycode
order by
	cntrycode;
