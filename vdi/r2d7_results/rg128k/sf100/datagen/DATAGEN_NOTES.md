# TPC-DS SF100: raw text + Parquet (one file per table)

Generated for the R2D7 row-group access capture. Produced by the scripts in `/home/cc/value_of_data/value-of-data-metric/tpcds_datagen/` (gen.sh, convert.py, verify.py, tpcds_schema.py, make_notes.py).

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
- Row groups: exactly 128,000 rows each except each file's last (asserted by verify.py). parquet-mr 1.13.1 has no row-count limit, so the writer is set to parquet.block.size=1, parquet.page.size.row.check.min=128000, parquet.page.size.row.check.max=128000, parquet.writer.max-padding=0 (set both as spark.hadoop.* and as write options): with a 1-byte block size the size check, which runs every page.size.row.check.{min,max} records, always flushes. Side effect: the same min/max gate the page-size check, so pages are cut at page.row.count.limit (20,000 rows) rather than ~1 MiB.
- Parquet writer: Other writer settings: compression=snappy, parquet.enable.summary-metadata=false. Everything else at Spark 3.5.5 / parquet-mr 1.13.1 defaults (driver Hadoop conf, null = unset so the default applies: {"parquet.block.size": "1", "parquet.page.size": null, "parquet.dictionary.page.size": null, "parquet.enable.dictionary": null, "parquet.writer.version": null, "parquet.page.row.count.limit": null, "parquet.enable.summary-metadata": "false", "parquet.page.size.row.check.min": "128000", "parquet.page.size.row.check.max": "128000", "parquet.writer.max-padding": "0"}; Spark: {"spark.sql.parquet.writeLegacyFormat": null, "spark.sql.parquet.outputTimestampType": null, "spark.sql.parquet.fieldId.write.enabled": null}). Those defaults are: parquet.page.size=1 MiB, parquet.dictionary.page.size=1 MiB, dictionary enabled, writer version PARQUET_1_0, page.row.count.limit=20000, spark.sql.parquet.writeLegacyFormat=false (decimals with precision<=9 as INT32, <=18 as INT64).
- Observed in footers: codecs ['SNAPPY'], encodings ['BIT_PACKED', 'PLAIN', 'PLAIN_DICTIONARY', 'RLE']
- CSV read options: `{"sep": "|", "header": "false", "quote": "", "escape": "\\", "encoding": "UTF-8", "mode": "FAILFAST", "nullValue": "", "dateFormat": "yyyy-MM-dd", "multiLine": "false", "inferSchema": "false"}`; spark.sql.csv.parser.columnPruning.enabled=false so every field of every line is parsed; FAILFAST aborts on any unparseable value or wrong field count.
- Schema: explicit, from tools/tpcds.sql (integer->int32, decimal(p,s)->decimal(p,s), date->date32, char/varchar->string); column names exactly as in the DDL. The trailing `|` yields an extra empty field that is read into a placeholder column and dropped. Empty fields are NULL.
- Row order = dsdgen generation order: each chunk file is read as its own DataFrame, forced to exactly one input partition (spark.sql.files.maxPartitionBytes = openCostInBytes = 1 TiB; asserted at runtime), unioned in child order 1..N, coalesce(1), written. No repartition/shuffle/sort. The single part-*.parquet was moved to `<table>.parquet` and the Spark output directory removed.
- Convert wall-clock (all tables, up to 8 tables concurrently in one Spark app): 4303.2 s

## Verification

- raw line count (sum over chunks) == Parquet footer num_rows for every table; schema == DDL; no column 100% NULL except the known always-empty dsdgen columns c_login and cc_closed_date_sk (from row-group null_count statistics).
- Row content/order: rows re-rendered from Parquet compared byte-for-byte to raw lines (decimals compared at column scale, since dsdgen prints e.g. gmt_offset `-5` for decimal(5,2)). Mode: ['first/last 100 lines of each of 1 chunks', 'first/last 100 lines of each of 32 chunks'].
- Verification result: PASSED; checked with pyarrow 25.0.1.
- Spot-check NULL counts: store_sales.ss_sold_date_sk: 12,955,025 NULL of 287,997,024; store_sales.ss_net_paid: 12,954,554 NULL of 287,997,024; date_dim.d_date: 0 NULL of 73,049; catalog_sales.cs_sold_date_sk: 719,581 NULL of 143,997,065; inventory.inv_quantity_on_hand: 19,969,395 NULL of 399,330,000

## Per-table results

| table | raw rows | parquet rows | row groups | rows/RG min–max | parquet bytes | raw bytes | chunks | convert s |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| call_center | 30 | 30 | 1 | 30–30 | 14,316 | 9,356 | 1 | 0.3 |
| catalog_page | 20,400 | 20,400 | 1 | 20,400–20,400 | 1,206,089 | 2,857,922 | 1 | 3.6 |
| catalog_returns | 14,404,374 | 14,404,374 | 113 | 68,374–128,000 | 1,065,187,525 | 2,279,840,289 | 32 | 320.0 |
| catalog_sales | 143,997,065 | 143,997,065 | 1125 | 125,065–128,000 | 10,545,009,114 | 31,016,462,258 | 32 | 3194.2 |
| customer | 2,000,000 | 2,000,000 | 16 | 80,000–128,000 | 108,179,893 | 269,534,238 | 32 | 36.6 |
| customer_address | 1,000,000 | 1,000,000 | 8 | 104,000–128,000 | 20,186,553 | 111,154,196 | 32 | 49.9 |
| customer_demographics | 1,920,800 | 1,920,800 | 16 | 800–128,000 | 7,789,031 | 80,660,096 | 32 | 14.3 |
| date_dim | 73,049 | 73,049 | 1 | 73,049–73,049 | 1,844,190 | 10,317,438 | 1 | 1.2 |
| household_demographics | 7,200 | 7,200 | 1 | 7,200–7,200 | 31,096 | 151,653 | 1 | 0.8 |
| income_band | 20 | 20 | 1 | 20–20 | 1,255 | 328 | 1 | 0.3 |
| inventory | 399,330,000 | 399,330,000 | 3120 | 98,000–128,000 | 2,121,690,816 | 8,626,269,134 | 32 | 876.6 |
| item | 204,000 | 204,000 | 2 | 76,000–128,000 | 19,538,785 | 58,366,791 | 1 | 4.0 |
| promotion | 1,000 | 1,000 | 1 | 1,000–1,000 | 56,002 | 124,973 | 1 | 0.4 |
| reason | 75 | 75 | 1 | 75–75 | 2,481 | 2,579 | 1 | 1.2 |
| ship_mode | 20 | 20 | 1 | 20–20 | 2,700 | 1,113 | 1 | 0.6 |
| store | 402 | 402 | 1 | 402–402 | 44,539 | 106,820 | 1 | 0.2 |
| store_returns | 28,795,080 | 28,795,080 | 225 | 123,080–128,000 | 1,675,929,038 | 3,485,083,098 | 32 | 468.6 |
| store_sales | 287,997,024 | 287,997,024 | 2250 | 125,024–128,000 | 13,533,452,270 | 40,959,624,908 | 32 | 4299.2 |
| time_dim | 86,400 | 86,400 | 1 | 86,400–86,400 | 1,128,498 | 5,107,780 | 1 | 3.3 |
| warehouse | 15 | 15 | 1 | 15–15 | 5,402 | 1,782 | 1 | 0.4 |
| web_page | 2,040 | 2,040 | 1 | 2,040–2,040 | 39,290 | 199,049 | 1 | 1.4 |
| web_returns | 7,197,670 | 7,197,670 | 57 | 29,670–128,000 | 531,216,234 | 1,053,832,196 | 32 | 168.9 |
| web_sales | 72,001,237 | 72,001,237 | 563 | 65,237–128,000 | 4,937,034,394 | 15,463,513,086 | 32 | 1646.2 |
| web_site | 24 | 24 | 1 | 24–24 | 11,912 | 6,874 | 1 | 0.3 |
| **total** | | | | | 34,569,601,423 | 103,423,227,957 | | |

## Sanity vs TPC-DS expectations

- store_sales = 287,997,024 rows = 2.8800 M x SF (expect ≈ 2.88 M x SF)
- date_dim = 73,049 (expect 73,049 at every SF); time_dim = 86,400 (expect 86,400); customer_demographics = 1,920,800 (expect 1,920,800); item = 204,000

## Notes

Generated with -parallel 32 (children run concurrently via xargs -P 32). Pipeline log: _pipeline.log; Spark log: _convert.log.
