import duckdb
import os
import sys

dir_ = sys.argv[1]
outfile_basename = sys.argv[2]

REGISTER = os.path.join(dir_, "spark_internal_listener_register_results.csv")
BARE =     os.path.join(dir_, "spark_internal_listener_bare_results.csv")
RG =       os.path.join(dir_, "spark_internal_listener_rowgroup_results.csv")
FULL =     os.path.join(dir_, "spark_internal_listener_cols_results.csv")
VANILLA =  os.path.join(dir_, "spark_internal_listener_vanilla_results.csv")
NOWRITE =  os.path.join(dir_, "spark_internal_listener_nowrite_results.csv")
OUTFILE = os.path.join(dir_, outfile_basename)



query = f"""
WITH reg AS (
    SELECT query, dataset, AVG(runtime) AS register_mean
    FROM read_csv_auto('{REGISTER}')
    GROUP BY query, dataset
),
bare AS (
    SELECT query, dataset, AVG(runtime) AS bare_mean
    FROM read_csv_auto('{BARE}')
    GROUP BY query, dataset
),
rg AS (
    SELECT query, dataset, AVG(runtime) AS rowgroup_mean
    FROM read_csv_auto('{RG}')
    GROUP BY query, dataset
),
full_tbl AS (
    SELECT query, dataset, AVG(runtime) AS full_mean
    FROM read_csv_auto('{FULL}')
    GROUP BY query, dataset
),
van AS (
    SELECT query, dataset, AVG(runtime) AS vanilla_mean
    FROM read_csv_auto('{VANILLA}')
    GROUP BY query, dataset
),
nw AS (
    SELECT query, dataset, AVG(runtime) AS nowrite_mean
    FROM read_csv_auto('{NOWRITE}')
    GROUP BY query, dataset
)

SELECT 
    reg.query,
    reg.dataset,
    reg.register_mean,
    bare.bare_mean,
    rg.rowgroup_mean,
    full_tbl.full_mean,
    van.vanilla_mean,
    nw.nowrite_mean
FROM reg
JOIN bare USING (query, dataset)
JOIN rg   USING (query, dataset)
JOIN full_tbl USING (query, dataset)
JOIN van  USING (query, dataset)
JOIN nw   USING (query, dataset)
"""

# print(query)  # optional: check the SQL string

duckdb.sql(f"""
           COPY ({query})
           TO '{OUTFILE}' (HEADER, FORMAT CSV);
           """
           )
