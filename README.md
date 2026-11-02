Repo for the Value of Data Indicator (VDI).

- `spark/`, `parquet-java/` — submodules pinning the forked Spark 3.5.5 (`rowgroup-dev`) and parquet-java 1.13.1 (`vod_rg`) with row-group read instrumentation. The Spark VDI implementation lives in the Spark fork; build notes are in each fork's `README_rg*`.
- `vdi/` — the VDI computation (`oracle/`, `model/`), the Spark lineage listener (`spark-lineage-api/`, including the EC2 scale-up benchmarking), and the sorting (`clustering/`) and preparation (`cleaning_budget/`) evaluation scenarios, plus the TPC-H / TPC-DS and Redbench IMDb (`redbench_imdb/`) workloads.
- `placement/` — the data placement evaluation scenario, run both on DuckDB and on Spark (`run_spark.py`, `aws/`).

Account-specific AWS settings are never stored here; see `vdi/spark-lineage-api/aws/SECRETS.md`.
