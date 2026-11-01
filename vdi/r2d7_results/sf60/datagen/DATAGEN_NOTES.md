# TPC-DS SF60: raw text + Parquet (one file per table)

Generated for the R2D7 row-group access capture. Produced by the scripts in `/home/cc/value_of_data/spark-scale/tpcds_datagen/` (now `tpcds_datagen/` on `main`; the `spark-scale` worktree was removed 2026-10-08) (gen.sh, convert.py, verify.py, tpcds_schema.py, make_notes.py).

## Data generation (dsdgen)

- dsdgen: TPC-DS tools version 4.0.0, `/home/cc/DSGen-software-code-4.0.0/tools/dsdgen` (sha256 74b34d98d3e067b9…, tpcds.idx sha256 19c11f3bc9745b34…)
- RNG seed: 19620718 (passed explicitly; this is also dsdgen's default)
- Raw output: `/mnt/tpcds/tpcds_raw/sf60/<table>_<child>_<N>.dat` (kept). dsdgen run with cwd = tools dir.
- Tables whose dsdgen row count is < 1,000,000 (for sales tables: orders/tickets) are emitted only by child 1; larger tables are split into N contiguous row ranges. Concatenating children 1..N reproduces the serial output byte-for-byte (checked for all 24 tables at SF1, serial vs -parallel 4 and 8).
- gen log:
```
dsdgen: /home/cc/DSGen-software-code-4.0.0/tools/dsdgen (dsdgen Population Generator (Version 4.0.0))
cmd template: cd /home/cc/DSGen-software-code-4.0.0/tools && ./dsdgen -scale 60 -rngseed 19620718 -parallel 32 -child <i> -dir /mnt/tpcds/tpcds_raw/sf60 -force Y -quiet Y
start: 2026-09-26T21:04:14+00:00
end: 2026-09-26T21:11:29+00:00
gen_wallclock_s: 435
all 32 children rc=0
```

## Encoding

- Every raw chunk was decoded with a strict UTF-8 decoder before conversion: ALL VALID.
- Non-ASCII (valid UTF-8) characters found: {'customer': 8476} (customer.c_birth_country values such as `CÔTE D'IVOIRE`, `RÉUNION`). Spark reads with encoding=UTF-8, so these round-trip unchanged; no bytes were replaced or dropped.

## Parquet conversion

- Writer: Apache Spark 3.5.5 (pip pyspark==3.5.5), bundled parquet-mr version 1.13.1 (build db4183109d5b734ec5930d870cdae161e408ddba); JVM java.version=17.0.20.1 (openjdk version "17.0.20.1" 2026-08-18)
- Footer created_by: `parquet-mr version 1.13.1 (build db4183109d5b734ec5930d870cdae161e408ddba)`
- Spark: spark.master=local[16], spark.driver.memory=20g, spark.local.dir=/mnt/tpcds/spark-tmp, spark.speculation=false, spark.sql.adaptive.enabled=false, spark.sql.files.maxPartitionBytes=1099511627776, spark.sql.files.openCostInBytes=1099511627776, spark.sql.csv.parser.columnPruning.enabled=false, spark.sql.parquet.compression.codec=snappy
- Parquet writer: parquet.block.size=134217728 (128 MiB row groups; set both as spark.hadoop.parquet.block.size and as the write option), compression=snappy, parquet.enable.summary-metadata=false. Everything else at Spark 3.5.5 / parquet-mr 1.13.1 defaults (driver Hadoop conf, null = unset so the default applies: {"parquet.block.size": "134217728", "parquet.page.size": null, "parquet.dictionary.page.size": null, "parquet.enable.dictionary": null, "parquet.writer.version": null, "parquet.page.row.count.limit": null, "parquet.enable.summary-metadata": "false"}; Spark: {"spark.sql.parquet.writeLegacyFormat": null, "spark.sql.parquet.outputTimestampType": null, "spark.sql.parquet.fieldId.write.enabled": null}). Those defaults are: parquet.page.size=1 MiB, parquet.dictionary.page.size=1 MiB, dictionary enabled, writer version PARQUET_1_0, page.row.count.limit=20000, spark.sql.parquet.writeLegacyFormat=false (decimals with precision<=9 as INT32, <=18 as INT64).
- Observed in footers: codecs ['SNAPPY'], encodings ['BIT_PACKED', 'PLAIN', 'PLAIN_DICTIONARY', 'RLE']
- CSV read options: `{"sep": "|", "header": "false", "quote": "", "escape": "\\", "encoding": "UTF-8", "mode": "FAILFAST", "nullValue": "", "dateFormat": "yyyy-MM-dd", "multiLine": "false", "inferSchema": "false"}`; spark.sql.csv.parser.columnPruning.enabled=false so every field of every line is parsed; FAILFAST aborts on any unparseable value or wrong field count.
- Schema: explicit, from tools/tpcds.sql (integer->int32, decimal(p,s)->decimal(p,s), date->date32, char/varchar->string); column names exactly as in the DDL. The trailing `|` yields an extra empty field that is read into a placeholder column and dropped. Empty fields are NULL.
- Row order = dsdgen generation order: each chunk file is read as its own DataFrame, forced to exactly one input partition (spark.sql.files.maxPartitionBytes = openCostInBytes = 1 TiB; asserted at runtime), unioned in child order 1..N, coalesce(1), written. No repartition/shuffle/sort. The single part-*.parquet was moved to `<table>.parquet` and the Spark output directory removed.
- Convert wall-clock (all tables, up to 8 tables concurrently in one Spark app): 2467.2 s

## Verification

- raw line count (sum over chunks) == Parquet footer num_rows for every table; schema == DDL; no column 100% NULL except the known always-empty dsdgen columns c_login and cc_closed_date_sk (from row-group null_count statistics).
- Row content/order: rows re-rendered from Parquet compared byte-for-byte to raw lines (decimals compared at column scale, since dsdgen prints e.g. gmt_offset `-5` for decimal(5,2)). Mode: ['first/last 100 lines of each of 1 chunks', 'first/last 100 lines of each of 32 chunks'].
- Verification result: PASSED; checked with pyarrow 25.0.1.
- Spot-check NULL counts: store_sales.ss_sold_date_sk: 7,772,817 NULL of 172,800,711; store_sales.ss_net_paid: 7,770,087 NULL of 172,800,711; date_dim.d_date: 0 NULL of 73,049; catalog_sales.cs_sold_date_sk: 432,220 NULL of 86,401,774; inventory.inv_quantity_on_hand: 3,382,373 NULL of 67,600,827

## Per-table results

| table | raw rows | parquet rows | row groups | rows/RG min–max | parquet bytes | raw bytes | chunks | convert s |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| call_center | 8 | 8 | 1 | 8–8 | 11,040 | 2,535 | 1 | 0.2 |
| catalog_page | 11,718 | 11,718 | 1 | 11,718–11,718 | 695,460 | 1,631,792 | 1 | 0.2 |
| catalog_returns | 8,640,070 | 8,640,070 | 5 | 1,239,670–1,850,100 | 630,772,805 | 1,334,191,168 | 32 | 112.9 |
| catalog_sales | 86,401,774 | 86,401,774 | 46 | 1,184,320–1,913,748 | 6,429,328,814 | 18,267,157,820 | 32 | 1745.5 |
| customer | 933,000 | 933,000 | 1 | 933,000–933,000 | 49,806,373 | 125,093,465 | 1 | 9.8 |
| customer_address | 466,000 | 466,000 | 1 | 466,000–466,000 | 9,184,518 | 51,743,196 | 1 | 3.8 |
| customer_demographics | 1,920,800 | 1,920,800 | 1 | 1,920,800–1,920,800 | 7,825,107 | 80,660,096 | 32 | 9.2 |
| date_dim | 73,049 | 73,049 | 1 | 73,049–73,049 | 1,868,849 | 10,317,438 | 1 | 1.0 |
| household_demographics | 7,200 | 7,200 | 1 | 7,200–7,200 | 31,096 | 151,653 | 1 | 0.2 |
| income_band | 20 | 20 | 1 | 20–20 | 1,255 | 328 | 1 | 0.2 |
| inventory | 67,600,827 | 67,600,827 | 3 | 16,860,627–25,370,100 | 357,979,093 | 1,392,326,823 | 32 | 157.5 |
| item | 74,000 | 74,000 | 1 | 74,000–74,000 | 7,173,305 | 20,899,750 | 1 | 1.6 |
| promotion | 577 | 577 | 1 | 577–577 | 35,862 | 71,899 | 1 | 0.2 |
| reason | 75 | 75 | 1 | 75–75 | 2,481 | 2,579 | 1 | 0.2 |
| ship_mode | 20 | 20 | 1 | 20–20 | 2,700 | 1,113 | 1 | 0.2 |
| store | 178 | 178 | 1 | 178–178 | 25,993 | 47,207 | 1 | 0.2 |
| store_returns | 17,271,432 | 17,271,432 | 8 | 1,240,732–2,290,100 | 1,017,398,801 | 2,057,489,854 | 32 | 221.7 |
| store_sales | 172,800,711 | 172,800,711 | 58 | 285,011–3,030,100 | 8,027,535,249 | 24,235,295,202 | 32 | 2462.7 |
| time_dim | 86,400 | 86,400 | 1 | 86,400–86,400 | 1,150,514 | 5,107,780 | 1 | 0.5 |
| warehouse | 7 | 7 | 1 | 7–7 | 4,761 | 834 | 1 | 0.2 |
| web_page | 1,082 | 1,082 | 1 | 1,082–1,082 | 23,097 | 104,893 | 1 | 0.2 |
| web_returns | 4,319,540 | 4,319,540 | 3 | 619,340–1,850,100 | 315,308,038 | 621,589,524 | 32 | 63.5 |
| web_sales | 43,198,797 | 43,198,797 | 21 | 1,823,702–2,088,626 | 2,931,164,098 | 9,143,390,767 | 32 | 867.5 |
| web_site | 20 | 20 | 1 | 20–20 | 11,396 | 5,685 | 1 | 0.3 |
| **total** | | | | | 19,787,340,705 | 57,347,283,401 | | |

## Sanity vs TPC-DS expectations

- store_sales = 172,800,711 rows = 2.8800 M x SF (expect ≈ 2.88 M x SF)
- date_dim = 73,049 (expect 73,049 at every SF); time_dim = 86,400 (expect 86,400); customer_demographics = 1,920,800 (expect 1,920,800); item = 74,000

## Notes

Generated with -parallel 32 (children run concurrently via xargs -P 32). Pipeline log: _pipeline.log; Spark log: _convert.log.

Convert attempt 1 (started 2026-09-26T21:17:33Z) was killed externally at 21:21:52Z: a concurrent Spark build agent ran `pkill -f 'spark-shell|SparkSubmit'` during its cleanup, which matched this pyspark JVM (Py4JNetworkError / 'SparkContext was shut down'; no OOM in dmesg). Its log is kept as _convert_attempt1_failed.log. Raw data and _raw_check.json from the single dsdgen run were reused (SKIP_GEN=1); _tmp_* dirs were removed and ALL 24 tables were re-converted from scratch in attempt 2 (started 21:23:07Z; every <table>.parquet has an mtime after that), including catalog_returns, inventory and web_returns that attempt 1 had already written. The verification above (raw rows == footer rows etc. for all 24 tables) ran on the attempt-2 files. No _tmp_* dirs remain. The convert wall-clock above is attempt 2 only; raw check (utf-8 + line count) took 363 s.
