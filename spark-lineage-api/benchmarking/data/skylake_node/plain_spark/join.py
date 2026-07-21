import duckdb

qry = '''
COPY (
    SELECT
        b.query,
        b.dataset,
        b.run_number,
        b.listener_bare_time,
        f.listener_time_sec,
        n.listener_nowrite_time,
        r.listener_register_time   AS listener_register_time,
        v.vanilla_time_sec
    FROM read_csv_auto('listener_bare_results_r1to9.csv') b
    JOIN read_csv_auto('listener_full_results_r1to9.csv') f
      USING (query, dataset, run_number)
    JOIN read_csv_auto('listener_nowrite_results_r1to9.csv') n
      USING (query, dataset, run_number)
    JOIN read_csv_auto('listener_register_results_r1to9.csv') r
      USING (query, dataset, run_number)
    JOIN read_csv_auto('vanilla_results_r1to9.csv') v
      USING (query, dataset, run_number)
    ORDER BY 
        b.dataset DESC,
        b.run_number,
        b.query
) to 'final_results_plain_spark.csv' (FORMAT CSV, HEADER TRUE)
'''

duckdb.sql(qry)
