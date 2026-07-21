# value-of-data-metric
Different implementations for the value of data metric

move files to `/tmp` in dfs.`/tmp`
https://drill.apache.org/download/


in `conf/logback.xml`
```
<logger name="org.apache.drill.exec.store.parquet" level="DEBUG"/>
<logger name="org.apache.drill.exec.physical.impl.scan" level="DEBUG"/>
```

Update conf/drill-env.sh 
`DRILLBIT_MAX_PROC_MEM` maximum total
`DRILL_HEAP` heap size
`DRILL_MAX_DIRECT_MEMORY` direct amount given to each direct memory


Set this to 1.0 to represent full (default is 0.05 which I interpret at 5%)
`ALTER SYSTEM SET planner.memory.percent_per_query = 1.0`
Set this to 158GB which is what i set MAX DIRECT MEMORY to. 
`ALTER SYSTEM SET planner.memory.max_query_memory_per_node = 169651208192`

[configuring memory](https://drill.apache.org/docs/configuring-drill-memory/)
[reference](https://drill.apache.org/docs/configuration-options-introduction/)

You can 

Finally, Lineitem has 4 fields which are generated as DECIMALs (quantity,
extendedprice, discount, tax) which DRILL has as a maximum of 38 point
precision which will spawn many man WARNINGs. These warnings will fill up logs
and also add a lot of time. However we need INFO so we cannot just suppress all
WARN logs. 

Answer is to alter table to cast these 4 columns from DECIMAL to DOUBLE. This
will speed up the queries and ensure all the 22 main TPCH and the extra queries
(23 to 38) all run as quickly as they can and all row group logs are written within one log file. 
[docs](https://drill.apache.org/docs/supported-data-types/)

Use ALTER TABLE in DuckDB [link](https://duckdb.org/docs/stable/sql/statements/alter_table.html#examples)

!quit exits drill. 

NULL is int so then trying to union with varchars gets messy and can cause
Number Format Errors


you can add queries to the set by having the tpcds/tpch drill logs completed
json file be updated usually via the process.py scripts in each repo
(`tpcds_drill_logs` or `drill_logs`))

