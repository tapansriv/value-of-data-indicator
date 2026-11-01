select count(*) as n, sum(o_totalprice) as total
from orders
where o_orderdate >= date '1995-03-01' and o_orderdate < date '1995-04-01'
