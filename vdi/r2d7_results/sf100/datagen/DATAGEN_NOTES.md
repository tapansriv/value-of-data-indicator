# TPC-DS SF100: raw text + Parquet (one file per table)

Generated for the R2D7 row-group access capture. Produced by the scripts in `/home/cc/value_of_data/spark-scale/tpcds_datagen/` (now `tpcds_datagen/` on `main`; the `spark-scale` worktree was removed 2026-10-08) (gen.sh, convert.py, verify.py, tpcds_schema.py, make_notes.py).

## Data generation (dsdgen)

- dsdgen: TPC-DS tools version 4.0.0, `/home/cc/DSGen-software-code-4.0.0/tools/dsdgen` (sha256 74b34d98d3e067b9…, tpcds.idx sha256 19c11f3bc9745b34…)
- RNG seed: 19620718 (passed explicitly; this is also dsdgen's default)
- Raw output: `/mnt/tpcds/tpcds_raw/sf100/<table>_<child>_<N>.dat` (kept). dsdgen run with cwd = tools dir.
- Tables whose dsdgen row count is < 1,000,000 (for sales tables: orders/tickets) are emitted only by child 1; larger tables are split into N contiguous row ranges. Concatenating children 1..N reproduces the serial output byte-for-byte (checked for all 24 tables at SF1, serial vs -parallel 4 and 8).
- gen log:
```
dsdgen: /home/cc/DSGen-software-code-4.0.0/tools/dsdgen (dsdgen Population Generator (Version 4.0.0))
cmd template: cd /home/cc/DSGen-software-code-4.0.0/tools && ./dsdgen -scale 100 -rngseed 19620718 -parallel 32 -child <i> -dir /mnt/tpcds/tpcds_raw/sf100 -force Y -quiet Y
start: 2026-09-26T22:06:03+00:00
end: 2026-09-26T22:19:46+00:00
gen_wallclock_s: 823
all 32 children rc=0
```

## Encoding

- Every raw chunk was decoded with a strict UTF-8 decoder before conversion: ALL VALID.
- Non-ASCII (valid UTF-8) characters found: {'customer': 18297} (customer.c_birth_country values such as `CÔTE D'IVOIRE`, `RÉUNION`). Spark reads with encoding=UTF-8, so these round-trip unchanged; no bytes were replaced or dropped.

## Parquet conversion

- Writer: Apache Spark 3.5.5 (pip pyspark==3.5.5), bundled parquet-mr version 1.13.1 (build db4183109d5b734ec5930d870cdae161e408ddba); JVM java.version=17.0.20.1 (openjdk version "17.0.20.1" 2026-08-18)
- Footer created_by: `parquet-mr version 1.13.1 (build db4183109d5b734ec5930d870cdae161e408ddba)`
- Spark: spark.master=local[16], spark.driver.memory=20g, spark.local.dir=/mnt/tpcds/spark-tmp, spark.speculation=false, spark.sql.adaptive.enabled=false, spark.sql.files.maxPartitionBytes=1099511627776, spark.sql.files.openCostInBytes=1099511627776, spark.sql.csv.parser.columnPruning.enabled=false, spark.sql.parquet.compression.codec=snappy
- Parquet writer: parquet.block.size=134217728 (128 MiB row groups; set both as spark.hadoop.parquet.block.size and as the write option), compression=snappy, parquet.enable.summary-metadata=false. Everything else at Spark 3.5.5 / parquet-mr 1.13.1 defaults (driver Hadoop conf, null = unset so the default applies: {"parquet.block.size": "134217728", "parquet.page.size": null, "parquet.dictionary.page.size": null, "parquet.enable.dictionary": null, "parquet.writer.version": null, "parquet.page.row.count.limit": null, "parquet.enable.summary-metadata": "false"}; Spark: {"spark.sql.parquet.writeLegacyFormat": null, "spark.sql.parquet.outputTimestampType": null, "spark.sql.parquet.fieldId.write.enabled": null}). Those defaults are: parquet.page.size=1 MiB, parquet.dictionary.page.size=1 MiB, dictionary enabled, writer version PARQUET_1_0, page.row.count.limit=20000, spark.sql.parquet.writeLegacyFormat=false (decimals with precision<=9 as INT32, <=18 as INT64).
- Observed in footers: codecs ['SNAPPY'], encodings ['BIT_PACKED', 'PLAIN', 'PLAIN_DICTIONARY', 'RLE']
- CSV read options: `{"sep": "|", "header": "false", "quote": "", "escape": "\\", "encoding": "UTF-8", "mode": "FAILFAST", "nullValue": "", "dateFormat": "yyyy-MM-dd", "multiLine": "false", "inferSchema": "false"}`; spark.sql.csv.parser.columnPruning.enabled=false so every field of every line is parsed; FAILFAST aborts on any unparseable value or wrong field count.
- Schema: explicit, from tools/tpcds.sql (integer->int32, decimal(p,s)->decimal(p,s), date->date32, char/varchar->string); column names exactly as in the DDL. The trailing `|` yields an extra empty field that is read into a placeholder column and dropped. Empty fields are NULL.
- Row order = dsdgen generation order: each chunk file is read as its own DataFrame, forced to exactly one input partition (spark.sql.files.maxPartitionBytes = openCostInBytes = 1 TiB; asserted at runtime), unioned in child order 1..N, coalesce(1), written. No repartition/shuffle/sort. The single part-*.parquet was moved to `<table>.parquet` and the Spark output directory removed.
- Convert wall-clock (all tables, up to 8 tables concurrently in one Spark app): 4211.9 s

## Verification

- raw line count (sum over chunks) == Parquet footer num_rows for every table; schema == DDL; no column 100% NULL except the known always-empty dsdgen columns c_login and cc_closed_date_sk (from row-group null_count statistics).
- Row content/order: rows re-rendered from Parquet compared byte-for-byte to raw lines (decimals compared at column scale, since dsdgen prints e.g. gmt_offset `-5` for decimal(5,2)). Mode: ['first/last 100 lines of each of 1 chunks', 'first/last 100 lines of each of 32 chunks'].
- Verification result: PASSED; checked with pyarrow 25.0.1.
- Spot-check NULL counts: store_sales.ss_sold_date_sk: 12,955,025 NULL of 287,997,024; store_sales.ss_net_paid: 12,954,554 NULL of 287,997,024; date_dim.d_date: 0 NULL of 73,049; catalog_sales.cs_sold_date_sk: 719,581 NULL of 143,997,065; inventory.inv_quantity_on_hand: 19,969,395 NULL of 399,330,000

## Per-table results

| table | raw rows | parquet rows | row groups | rows/RG min–max | parquet bytes | raw bytes | chunks | convert s |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| call_center | 30 | 30 | 1 | 30–30 | 14,316 | 9,356 | 1 | 0.3 |
| catalog_page | 20,400 | 20,400 | 1 | 20,400–20,400 | 1,205,578 | 2,857,922 | 1 | 5.2 |
| catalog_returns | 14,404,374 | 14,404,374 | 8 | 1,575,806–1,833,974 | 1,057,633,484 | 2,279,840,289 | 32 | 350.1 |
| catalog_sales | 143,997,065 | 143,997,065 | 77 | 535,433–1,908,748 | 10,759,552,445 | 31,016,462,258 | 32 | 3017.8 |
| customer | 2,000,000 | 2,000,000 | 1 | 2,000,000–2,000,000 | 106,612,706 | 269,534,238 | 32 | 54.8 |
| customer_address | 1,000,000 | 1,000,000 | 1 | 1,000,000–1,000,000 | 19,587,972 | 111,154,196 | 32 | 77.7 |
| customer_demographics | 1,920,800 | 1,920,800 | 1 | 1,920,800–1,920,800 | 7,825,107 | 80,660,096 | 32 | 69.8 |
| date_dim | 73,049 | 73,049 | 1 | 73,049–73,049 | 1,868,849 | 10,317,438 | 1 | 1.9 |
| household_demographics | 7,200 | 7,200 | 1 | 7,200–7,200 | 31,096 | 151,653 | 1 | 1.3 |
| income_band | 20 | 20 | 1 | 20–20 | 1,255 | 328 | 1 | 0.2 |
| inventory | 399,330,000 | 399,330,000 | 16 | 18,778,500–25,370,100 | 2,114,641,731 | 8,626,269,134 | 32 | 974.0 |
| item | 204,000 | 204,000 | 1 | 204,000–204,000 | 19,578,924 | 58,366,791 | 1 | 6.9 |
| promotion | 1,000 | 1,000 | 1 | 1,000–1,000 | 56,002 | 124,973 | 1 | 1.3 |
| reason | 75 | 75 | 1 | 75–75 | 2,481 | 2,579 | 1 | 0.5 |
| ship_mode | 20 | 20 | 1 | 20–20 | 2,700 | 1,113 | 1 | 0.6 |
| store | 402 | 402 | 1 | 402–402 | 44,539 | 106,820 | 1 | 0.5 |
| store_returns | 28,795,080 | 28,795,080 | 13 | 1,433,880–2,280,100 | 1,700,292,067 | 3,485,083,098 | 32 | 501.4 |
| store_sales | 287,997,024 | 287,997,024 | 96 | 557,524–3,030,100 | 13,397,882,953 | 40,959,624,908 | 32 | 4206.9 |
| time_dim | 86,400 | 86,400 | 1 | 86,400–86,400 | 1,150,514 | 5,107,780 | 1 | 0.5 |
| warehouse | 15 | 15 | 1 | 15–15 | 5,402 | 1,782 | 1 | 0.2 |
| web_page | 2,040 | 2,040 | 1 | 2,040–2,040 | 39,290 | 199,049 | 1 | 0.2 |
| web_returns | 7,197,670 | 7,197,670 | 4 | 1,647,370–1,850,100 | 525,192,438 | 1,053,832,196 | 32 | 82.1 |
| web_sales | 72,001,237 | 72,001,237 | 36 | 67,737–2,070,100 | 4,901,301,092 | 15,463,513,086 | 32 | 1343.9 |
| web_site | 24 | 24 | 1 | 24–24 | 11,912 | 6,874 | 1 | 0.2 |
| **total** | | | | | 34,614,534,853 | 103,423,227,957 | | |

## Sanity vs TPC-DS expectations

- store_sales = 287,997,024 rows = 2.8800 M x SF (expect ≈ 2.88 M x SF)
- date_dim = 73,049 (expect 73,049 at every SF); time_dim = 86,400 (expect 86,400); customer_demographics = 1,920,800 (expect 1,920,800); item = 204,000

## Notes

Generated with -parallel 32 (children run concurrently via xargs -P 32). Pipeline log: _pipeline.log; Spark log: _convert.log.
