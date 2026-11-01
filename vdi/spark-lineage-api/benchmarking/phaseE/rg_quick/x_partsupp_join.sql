select p_brand, count(*) as n, sum(ps_supplycost) as cost
from partsupp, part
where ps_partkey = p_partkey and p_size = 15
group by p_brand
order by p_brand
