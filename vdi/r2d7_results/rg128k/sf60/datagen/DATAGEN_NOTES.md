# TPC-DS SF60: raw text + Parquet (one file per table)

Generated for the R2D7 row-group access capture. Produced by the scripts in `/home/cc/value_of_data/value-of-data-metric/tpcds_datagen/` (gen.sh, convert.py, verify.py, tpcds_schema.py, make_notes.py).

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
- Row groups: exactly 128,000 rows each except each file's last (asserted by verify.py). parquet-mr 1.13.1 has no row-count limit, so the writer is set to parquet.block.size=1, parquet.page.size.row.check.min=128000, parquet.page.size.row.check.max=128000, parquet.writer.max-padding=0 (set both as spark.hadoop.* and as write options): with a 1-byte block size the size check, which runs every page.size.row.check.{min,max} records, always flushes. Side effect: the same min/max gate the page-size check, so pages are cut at page.row.count.limit (20,000 rows) rather than ~1 MiB.
- Parquet writer: Other writer settings: compression=snappy, parquet.enable.summary-metadata=false. Everything else at Spark 3.5.5 / parquet-mr 1.13.1 defaults (driver Hadoop conf, null = unset so the default applies: {"parquet.block.size": "1", "parquet.page.size": null, "parquet.dictionary.page.size": null, "parquet.enable.dictionary": null, "parquet.writer.version": null, "parquet.page.row.count.limit": null, "parquet.enable.summary-metadata": "false", "parquet.page.size.row.check.min": "128000", "parquet.page.size.row.check.max": "128000", "parquet.writer.max-padding": "0"}; Spark: {"spark.sql.parquet.writeLegacyFormat": null, "spark.sql.parquet.outputTimestampType": null, "spark.sql.parquet.fieldId.write.enabled": null}). Those defaults are: parquet.page.size=1 MiB, parquet.dictionary.page.size=1 MiB, dictionary enabled, writer version PARQUET_1_0, page.row.count.limit=20000, spark.sql.parquet.writeLegacyFormat=false (decimals with precision<=9 as INT32, <=18 as INT64).
- Observed in footers: codecs ['SNAPPY'], encodings ['BIT_PACKED', 'PLAIN', 'PLAIN_DICTIONARY', 'RLE']
- CSV read options: `{"sep": "|", "header": "false", "quote": "", "escape": "\\", "encoding": "UTF-8", "mode": "FAILFAST", "nullValue": "", "dateFormat": "yyyy-MM-dd", "multiLine": "false", "inferSchema": "false"}`; spark.sql.csv.parser.columnPruning.enabled=false so every field of every line is parsed; FAILFAST aborts on any unparseable value or wrong field count.
- Schema: explicit, from tools/tpcds.sql (integer->int32, decimal(p,s)->decimal(p,s), date->date32, char/varchar->string); column names exactly as in the DDL. The trailing `|` yields an extra empty field that is read into a placeholder column and dropped. Empty fields are NULL.
- Row order = dsdgen generation order: each chunk file is read as its own DataFrame, forced to exactly one input partition (spark.sql.files.maxPartitionBytes = openCostInBytes = 1 TiB; asserted at runtime), unioned in child order 1..N, coalesce(1), written. No repartition/shuffle/sort. The single part-*.parquet was moved to `<table>.parquet` and the Spark output directory removed.
- Convert wall-clock (all tables, up to 8 tables concurrently in one Spark app): 2578.3 s

## Verification

- raw line count (sum over chunks) == Parquet footer num_rows for every table; schema == DDL; no column 100% NULL except the known always-empty dsdgen columns c_login and cc_closed_date_sk (from row-group null_count statistics).
- Row content/order: rows re-rendered from Parquet compared byte-for-byte to raw lines (decimals compared at column scale, since dsdgen prints e.g. gmt_offset `-5` for decimal(5,2)). Mode: ['first/last 100 lines of each of 1 chunks', 'first/last 100 lines of each of 32 chunks'].
- Verification result: PASSED; checked with pyarrow 25.0.1.
- Spot-check NULL counts: store_sales.ss_sold_date_sk: 7,772,817 NULL of 172,800,711; store_sales.ss_net_paid: 7,770,087 NULL of 172,800,711; date_dim.d_date: 0 NULL of 73,049; catalog_sales.cs_sold_date_sk: 432,220 NULL of 86,401,774; inventory.inv_quantity_on_hand: 3,382,373 NULL of 67,600,827

## Per-table results

| table | raw rows | parquet rows | row groups | rows/RG min–max | parquet bytes | raw bytes | chunks | convert s |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| call_center | 8 | 8 | 1 | 8–8 | 11,040 | 2,535 | 1 | 0.2 |
| catalog_page | 11,718 | 11,718 | 1 | 11,718–11,718 | 695,460 | 1,631,792 | 1 | 1.6 |
| catalog_returns | 8,640,070 | 8,640,070 | 68 | 64,070–128,000 | 627,325,979 | 1,334,191,168 | 32 | 167.1 |
| catalog_sales | 86,401,774 | 86,401,774 | 676 | 1,774–128,000 | 6,221,967,866 | 18,267,157,820 | 32 | 1865.7 |
| customer | 933,000 | 933,000 | 8 | 37,000–128,000 | 50,532,313 | 125,093,465 | 1 | 13.5 |
| customer_address | 466,000 | 466,000 | 4 | 82,000–128,000 | 9,432,431 | 51,743,196 | 1 | 5.9 |
| customer_demographics | 1,920,800 | 1,920,800 | 16 | 800–128,000 | 7,789,031 | 80,660,096 | 32 | 13.7 |
| date_dim | 73,049 | 73,049 | 1 | 73,049–73,049 | 1,844,190 | 10,317,438 | 1 | 2.0 |
| household_demographics | 7,200 | 7,200 | 1 | 7,200–7,200 | 31,096 | 151,653 | 1 | 0.3 |
| income_band | 20 | 20 | 1 | 20–20 | 1,255 | 328 | 1 | 0.3 |
| inventory | 67,600,827 | 67,600,827 | 529 | 16,827–128,000 | 302,432,231 | 1,392,326,823 | 32 | 162.8 |
| item | 74,000 | 74,000 | 1 | 74,000–74,000 | 7,136,340 | 20,899,750 | 1 | 2.9 |
| promotion | 577 | 577 | 1 | 577–577 | 35,862 | 71,899 | 1 | 0.6 |
| reason | 75 | 75 | 1 | 75–75 | 2,481 | 2,579 | 1 | 0.4 |
| ship_mode | 20 | 20 | 1 | 20–20 | 2,700 | 1,113 | 1 | 0.4 |
| store | 178 | 178 | 1 | 178–178 | 25,993 | 47,207 | 1 | 1.3 |
| store_returns | 17,271,432 | 17,271,432 | 135 | 119,432–128,000 | 998,683,849 | 2,057,489,854 | 32 | 281.2 |
| store_sales | 172,800,711 | 172,800,711 | 1351 | 711–128,000 | 8,076,673,469 | 24,235,295,202 | 32 | 2573.8 |
| time_dim | 86,400 | 86,400 | 1 | 86,400–86,400 | 1,128,498 | 5,107,780 | 1 | 1.4 |
| warehouse | 7 | 7 | 1 | 7–7 | 4,761 | 834 | 1 | 0.5 |
| web_page | 1,082 | 1,082 | 1 | 1,082–1,082 | 23,097 | 104,893 | 1 | 0.3 |
| web_returns | 4,319,540 | 4,319,540 | 34 | 95,540–128,000 | 317,715,997 | 621,589,524 | 32 | 94.5 |
| web_sales | 43,198,797 | 43,198,797 | 338 | 62,797–128,000 | 2,944,805,155 | 9,143,390,767 | 32 | 964.0 |
| web_site | 20 | 20 | 1 | 20–20 | 11,396 | 5,685 | 1 | 0.3 |
| **total** | | | | | 19,568,312,490 | 57,347,283,401 | | |

## Sanity vs TPC-DS expectations

- store_sales = 172,800,711 rows = 2.8800 M x SF (expect ≈ 2.88 M x SF)
- date_dim = 73,049 (expect 73,049 at every SF); time_dim = 86,400 (expect 86,400); customer_demographics = 1,920,800 (expect 1,920,800); item = 74,000

## Notes

Generated with -parallel 32 (children run concurrently via xargs -P 32). Pipeline log: _pipeline.log; Spark log: _convert.log.
