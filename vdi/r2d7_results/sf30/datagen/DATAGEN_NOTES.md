# TPC-DS SF30: raw text + Parquet (one file per table)

Generated for the R2D7 row-group access capture. Produced by the scripts in `/home/cc/value_of_data/spark-scale/tpcds_datagen/` (now `tpcds_datagen/` on `main`; the `spark-scale` worktree was removed 2026-10-08) (gen.sh, convert.py, verify.py, tpcds_schema.py, make_notes.py).

## Data generation (dsdgen)

- dsdgen: TPC-DS tools version 4.0.0, `/home/cc/DSGen-software-code-4.0.0/tools/dsdgen` (sha256 74b34d98d3e067b9…, tpcds.idx sha256 19c11f3bc9745b34…)
- RNG seed: 19620718 (passed explicitly; this is also dsdgen's default)
- Raw output: `/mnt/tpcds/tpcds_raw/sf30/<table>_<child>_<N>.dat` (kept). dsdgen run with cwd = tools dir.
- Tables whose dsdgen row count is < 1,000,000 (for sales tables: orders/tickets) are emitted only by child 1; larger tables are split into N contiguous row ranges. Concatenating children 1..N reproduces the serial output byte-for-byte (checked for all 24 tables at SF1, serial vs -parallel 4 and 8).
- gen log:
```
dsdgen: /home/cc/DSGen-software-code-4.0.0/tools/dsdgen (dsdgen Population Generator (Version 4.0.0))
cmd template: cd /home/cc/DSGen-software-code-4.0.0/tools && ./dsdgen -scale 30 -rngseed 19620718 -parallel 32 -child <i> -dir /mnt/tpcds/tpcds_raw/sf30 -force Y -quiet Y
start: 2026-09-26T20:42:49+00:00
end: 2026-09-26T20:45:53+00:00
gen_wallclock_s: 184
all 32 children rc=0
```

## Encoding

- Every raw chunk was decoded with a strict UTF-8 decoder before conversion: ALL VALID.
- Non-ASCII (valid UTF-8) characters found: {'customer': 3885} (customer.c_birth_country values such as `CÔTE D'IVOIRE`, `RÉUNION`). Spark reads with encoding=UTF-8, so these round-trip unchanged; no bytes were replaced or dropped.

## Parquet conversion

- Writer: Apache Spark 3.5.5 (pip pyspark==3.5.5), bundled parquet-mr version 1.13.1 (build db4183109d5b734ec5930d870cdae161e408ddba); JVM java.version=17.0.20.1 (openjdk version "17.0.20.1" 2026-08-18)
- Footer created_by: `parquet-mr version 1.13.1 (build db4183109d5b734ec5930d870cdae161e408ddba)`
- Spark: spark.master=local[16], spark.driver.memory=20g, spark.local.dir=/mnt/tpcds/spark-tmp, spark.speculation=false, spark.sql.adaptive.enabled=false, spark.sql.files.maxPartitionBytes=1099511627776, spark.sql.files.openCostInBytes=1099511627776, spark.sql.csv.parser.columnPruning.enabled=false, spark.sql.parquet.compression.codec=snappy
- Parquet writer: parquet.block.size=134217728 (128 MiB row groups; set both as spark.hadoop.parquet.block.size and as the write option), compression=snappy, parquet.enable.summary-metadata=false. Everything else at Spark 3.5.5 / parquet-mr 1.13.1 defaults (driver Hadoop conf, null = unset so the default applies: {"parquet.block.size": "134217728", "parquet.page.size": null, "parquet.dictionary.page.size": null, "parquet.enable.dictionary": null, "parquet.writer.version": null, "parquet.page.row.count.limit": null, "parquet.enable.summary-metadata": "false"}; Spark: {"spark.sql.parquet.writeLegacyFormat": null, "spark.sql.parquet.outputTimestampType": null, "spark.sql.parquet.fieldId.write.enabled": null}). Those defaults are: parquet.page.size=1 MiB, parquet.dictionary.page.size=1 MiB, dictionary enabled, writer version PARQUET_1_0, page.row.count.limit=20000, spark.sql.parquet.writeLegacyFormat=false (decimals with precision<=9 as INT32, <=18 as INT64).
- Observed in footers: codecs ['SNAPPY'], encodings ['BIT_PACKED', 'PLAIN', 'PLAIN_DICTIONARY', 'RLE']
- CSV read options: `{"sep": "|", "header": "false", "quote": "", "escape": "\\", "encoding": "UTF-8", "mode": "FAILFAST", "nullValue": "", "dateFormat": "yyyy-MM-dd", "multiLine": "false", "inferSchema": "false"}`; spark.sql.csv.parser.columnPruning.enabled=false so every field of every line is parsed; FAILFAST aborts on any unparseable value or wrong field count.
- Schema: explicit, from tools/tpcds.sql (integer->int32, decimal(p,s)->decimal(p,s), date->date32, char/varchar->string); column names exactly as in the DDL. The trailing `|` yields an extra empty field that is read into a placeholder column and dropped. Empty fields are NULL.
- Row order = dsdgen generation order: each chunk file is read as its own DataFrame, forced to exactly one input partition (spark.sql.files.maxPartitionBytes = openCostInBytes = 1 TiB; asserted at runtime), unioned in child order 1..N, coalesce(1), written. No repartition/shuffle/sort. The single part-*.parquet was moved to `<table>.parquet` and the Spark output directory removed.
- Convert wall-clock (all tables, up to 8 tables concurrently in one Spark app): 1084.1 s

## Verification

- raw line count (sum over chunks) == Parquet footer num_rows for every table; schema == DDL; no column 100% NULL except the known always-empty dsdgen columns c_login and cc_closed_date_sk (from row-group null_count statistics).
- Row content/order: rows re-rendered from Parquet compared byte-for-byte to raw lines (decimals compared at column scale, since dsdgen prints e.g. gmt_offset `-5` for decimal(5,2)). Mode: ['first/last 100 lines of each of 1 chunks', 'first/last 100 lines of each of 32 chunks'].
- Verification result: PASSED; checked with pyarrow 25.0.1.
- Spot-check NULL counts: store_sales.ss_sold_date_sk: 3,888,419 NULL of 86,406,277; store_sales.ss_net_paid: 3,886,043 NULL of 86,406,277; date_dim.d_date: 0 NULL of 73,049; catalog_sales.cs_sold_date_sk: 216,363 NULL of 43,204,059; inventory.inv_quantity_on_hand: 1,567,544 NULL of 31,321,566

## Per-table results

| table | raw rows | parquet rows | row groups | rows/RG min–max | parquet bytes | raw bytes | chunks | convert s |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| call_center | 6 | 6 | 1 | 6–6 | 10,554 | 1,920 | 1 | 0.2 |
| catalog_page | 11,718 | 11,718 | 1 | 11,718–11,718 | 695,460 | 1,631,792 | 1 | 0.3 |
| catalog_returns | 4,322,293 | 4,322,293 | 3 | 622,093–1,850,100 | 315,134,377 | 662,889,117 | 32 | 56.9 |
| catalog_sales | 43,204,059 | 43,204,059 | 23 | 1,436,212–1,913,748 | 3,190,128,186 | 9,084,936,152 | 32 | 725.7 |
| customer | 433,000 | 433,000 | 1 | 433,000–433,000 | 23,180,731 | 57,873,984 | 1 | 3.4 |
| customer_address | 216,000 | 216,000 | 1 | 216,000–216,000 | 4,310,117 | 23,922,925 | 1 | 1.7 |
| customer_demographics | 1,920,800 | 1,920,800 | 1 | 1,920,800–1,920,800 | 7,825,107 | 80,660,096 | 32 | 9.3 |
| date_dim | 73,049 | 73,049 | 1 | 73,049–73,049 | 1,868,849 | 10,317,438 | 1 | 1.0 |
| household_demographics | 7,200 | 7,200 | 1 | 7,200–7,200 | 31,096 | 151,653 | 1 | 0.2 |
| income_band | 20 | 20 | 1 | 20–20 | 1,255 | 328 | 1 | 0.1 |
| inventory | 31,321,566 | 31,321,566 | 2 | 5,951,466–25,370,100 | 165,866,455 | 641,109,477 | 32 | 60.8 |
| item | 40,000 | 40,000 | 1 | 40,000–40,000 | 3,903,558 | 11,274,582 | 1 | 1.0 |
| promotion | 411 | 411 | 1 | 411–411 | 27,551 | 51,052 | 1 | 0.2 |
| reason | 75 | 75 | 1 | 75–75 | 2,481 | 2,579 | 1 | 0.2 |
| ship_mode | 20 | 20 | 1 | 20–20 | 2,700 | 1,113 | 1 | 0.2 |
| store | 78 | 78 | 1 | 78–78 | 17,356 | 20,639 | 1 | 0.2 |
| store_returns | 8,636,578 | 8,636,578 | 4 | 1,746,278–2,300,100 | 506,868,560 | 1,016,678,739 | 32 | 91.6 |
| store_sales | 86,406,277 | 86,406,277 | 29 | 1,563,477–3,030,100 | 3,994,951,074 | 11,991,328,481 | 32 | 1079.4 |
| time_dim | 86,400 | 86,400 | 1 | 86,400–86,400 | 1,150,514 | 5,107,780 | 1 | 0.5 |
| warehouse | 6 | 6 | 1 | 6–6 | 4,605 | 719 | 1 | 0.2 |
| web_page | 468 | 468 | 1 | 468–468 | 12,625 | 45,115 | 1 | 0.3 |
| web_returns | 2,160,540 | 2,160,540 | 2 | 310,440–1,850,100 | 157,304,348 | 307,844,247 | 32 | 28.7 |
| web_sales | 21,598,604 | 21,598,604 | 11 | 866,448–2,088,626 | 1,454,184,473 | 4,540,183,053 | 32 | 365.5 |
| web_site | 26 | 26 | 1 | 26–26 | 12,040 | 7,481 | 1 | 0.2 |
| **total** | | | | | 9,827,494,072 | 28,436,040,462 | | |

## Sanity vs TPC-DS expectations

- store_sales = 86,406,277 rows = 2.8802 M x SF (expect ≈ 2.88 M x SF)
- date_dim = 73,049 (expect 73,049 at every SF); time_dim = 86,400 (expect 86,400); customer_demographics = 1,920,800 (expect 1,920,800); item = 40,000

## Notes

Generated with -parallel 32 (children run concurrently via xargs -P 32). Pipeline log: _pipeline.log; Spark log: _convert.log.
