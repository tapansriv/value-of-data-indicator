# TPC-DS SF1: raw text + Parquet (one file per table)

Generated for the R2D7 row-group access capture. Produced by the scripts in `/home/cc/value_of_data/value-of-data-metric/tpcds_datagen/` (gen.sh, convert.py, verify.py, tpcds_schema.py, make_notes.py).

## Data generation (dsdgen)

- dsdgen: TPC-DS tools version 4.0.0, `/home/cc/DSGen-software-code-4.0.0/tools/dsdgen` (sha256 74b34d98d3e067b9…, tpcds.idx sha256 19c11f3bc9745b34…)
- RNG seed: 19620718 (passed explicitly; this is also dsdgen's default)
- Raw output: `/mnt/tpcds/tpcds_raw/sf1/<table>_<child>_<N>.dat` (kept). dsdgen run with cwd = tools dir.
- Tables whose dsdgen row count is < 1,000,000 (for sales tables: orders/tickets) are emitted only by child 1; larger tables are split into N contiguous row ranges. Concatenating children 1..N reproduces the serial output byte-for-byte (checked for all 24 tables at SF1, serial vs -parallel 4 and 8).
- gen log:
```
dsdgen: /home/cc/DSGen-software-code-4.0.0/tools/dsdgen (dsdgen Population Generator (Version 4.0.0))
cmd template: cd /home/cc/DSGen-software-code-4.0.0/tools && ./dsdgen -scale 1 -rngseed 19620718 -parallel 8 -child <i> -dir /mnt/tpcds/tpcds_raw/sf1 -force Y -quiet Y
start: 2026-09-26T20:33:23+00:00
end: 2026-09-26T20:34:56+00:00
gen_wallclock_s: 93
all 8 children rc=0
```

## Encoding

- Every raw chunk was decoded with a strict UTF-8 decoder before conversion: ALL VALID.
- Non-ASCII (valid UTF-8) characters found: {'customer': 910} (customer.c_birth_country values such as `CÔTE D'IVOIRE`, `RÉUNION`). Spark reads with encoding=UTF-8, so these round-trip unchanged; no bytes were replaced or dropped.

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
- Convert wall-clock (all tables, up to 8 tables concurrently in one Spark app): 47.2 s

## Verification

- raw line count (sum over chunks) == Parquet footer num_rows for every table; schema == DDL; no column 100% NULL except the known always-empty dsdgen columns c_login and cc_closed_date_sk (from row-group null_count statistics).
- Row content/order: rows re-rendered from Parquet compared byte-for-byte to raw lines (decimals compared at column scale, since dsdgen prints e.g. gmt_offset `-5` for decimal(5,2)). Mode: ['first/last 100 lines of each of 1 chunks', 'first/last 100 lines of each of 8 chunks'].
- Verification result: PASSED; checked with pyarrow 25.0.1.
- Spot-check NULL counts: store_sales.ss_sold_date_sk: 130,093 NULL of 2,880,404; store_sales.ss_net_paid: 129,397 NULL of 2,880,404; date_dim.d_date: 0 NULL of 73,049; catalog_sales.cs_sold_date_sk: 7,180 NULL of 1,441,548; inventory.inv_quantity_on_hand: 586,913 NULL of 11,745,000

## Per-table results

| table | raw rows | parquet rows | row groups | rows/RG min–max | parquet bytes | raw bytes | chunks | convert s |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| call_center | 6 | 6 | 1 | 6–6 | 10,573 | 1,891 | 1 | 0.2 |
| catalog_page | 11,718 | 11,718 | 1 | 11,718–11,718 | 695,460 | 1,631,792 | 1 | 0.6 |
| catalog_returns | 144,067 | 144,067 | 2 | 16,067–128,000 | 10,592,843 | 21,397,635 | 1 | 4.6 |
| catalog_sales | 1,441,548 | 1,441,548 | 12 | 33,548–128,000 | 102,529,042 | 295,910,384 | 1 | 34.6 |
| customer | 100,000 | 100,000 | 1 | 100,000–100,000 | 5,410,120 | 13,210,282 | 1 | 3.4 |
| customer_address | 50,000 | 50,000 | 1 | 50,000–50,000 | 1,057,698 | 5,502,165 | 1 | 0.8 |
| customer_demographics | 1,920,800 | 1,920,800 | 16 | 800–128,000 | 7,789,031 | 80,660,096 | 8 | 9.1 |
| date_dim | 73,049 | 73,049 | 1 | 73,049–73,049 | 1,844,190 | 10,317,438 | 1 | 1.6 |
| household_demographics | 7,200 | 7,200 | 1 | 7,200–7,200 | 31,096 | 151,653 | 1 | 0.2 |
| income_band | 20 | 20 | 1 | 20–20 | 1,255 | 328 | 1 | 0.2 |
| inventory | 11,745,000 | 11,745,000 | 92 | 97,000–128,000 | 39,355,223 | 236,420,139 | 8 | 23.2 |
| item | 18,000 | 18,000 | 1 | 18,000–18,000 | 1,773,095 | 5,051,899 | 1 | 0.6 |
| promotion | 300 | 300 | 1 | 300–300 | 22,059 | 37,233 | 1 | 0.2 |
| reason | 75 | 75 | 1 | 75–75 | 2,481 | 2,579 | 1 | 0.2 |
| ship_mode | 20 | 20 | 1 | 20–20 | 2,700 | 1,113 | 1 | 0.2 |
| store | 12 | 12 | 1 | 12–12 | 10,348 | 3,155 | 1 | 0.2 |
| store_returns | 287,514 | 287,514 | 3 | 31,514–128,000 | 16,131,779 | 32,748,011 | 1 | 6.3 |
| store_sales | 2,880,404 | 2,880,404 | 23 | 64,404–128,000 | 130,243,404 | 388,445,409 | 1 | 44.7 |
| time_dim | 86,400 | 86,400 | 1 | 86,400–86,400 | 1,128,498 | 5,107,780 | 1 | 0.7 |
| warehouse | 5 | 5 | 1 | 5–5 | 4,525 | 585 | 1 | 0.2 |
| web_page | 60 | 60 | 1 | 60–60 | 5,762 | 5,776 | 1 | 0.3 |
| web_returns | 71,763 | 71,763 | 1 | 71,763–71,763 | 5,277,921 | 9,815,735 | 1 | 1.5 |
| web_sales | 719,384 | 719,384 | 6 | 79,384–128,000 | 47,573,477 | 146,877,674 | 1 | 18.8 |
| web_site | 30 | 30 | 1 | 30–30 | 12,286 | 8,771 | 1 | 0.3 |
| **total** | | | | | 371,504,866 | 1,253,309,523 | | |

## Sanity vs TPC-DS expectations

- store_sales = 2,880,404 rows = 2.8804 M x SF (expect ≈ 2.88 M x SF)
- date_dim = 73,049 (expect 73,049 at every SF); time_dim = 86,400 (expect 86,400); customer_demographics = 1,920,800 (expect 1,920,800); item = 18,000

## Notes

Generated with -parallel 8 (children run concurrently via xargs -P 8). Pipeline log: _pipeline.log; Spark log: _convert.log.
