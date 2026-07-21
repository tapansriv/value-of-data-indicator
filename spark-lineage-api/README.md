# Spark Query Lineage Logger

This project implements a Spark `QueryExecutionListener` that logs column-level data usage during SQL query execution. It supports inputs in CSV, Parquet, and Iceberg format and writes metadata logs to an **Iceberg table**, enabling downstream analysis of data access patterns.

---

## Features

- Unified lineage tracker for CSV, Parquet, and Iceberg sources
- Tracks:
  - Table and column used
  - Execution timestamp
  - Data task ID (uniquely combines Spark query ID + script run UUID)
  - Optional row group ID (currently unused)
  - Utility score (currently dummy value = 1.0)
- Logs are written directly to an Iceberg table using `writeTo(...).append()`
- Easy to query logs from Spark SQL or shell

---

## Requirements

- macOS (developed and tested on macOS)
- Java 8+
- Scala 2.13.x
- Apache Spark 3.5.5
- Apache Iceberg 1.8.1
- sbt (build tool)

---

## Setup

### 1. Clone and Build

```bash
git clone <repo-url>
cd spark-lineage-api
sbt clean assembly
```
This generates a fat JAR in target/scala-2.13

### 2. Running the API

#### Syntax

```bash
spark-submit \
  --class LineageAPI \
  target/scala-2.13/spark-query-api-assembly-0.1.jar \
  <sourceType> <sourcePath> <queryFile> <usageTable> <catalogName>
```

#### Example

```bash
spark-submit \
  --class LineageAPI \
  target/scala-2.13/spark-query-api-assembly-0.1.jar \
  iceberg \
  tpch/parquet \
  tpch/queries/6.sql \
  my_catalog.default.usage_metadata \
  my_catalog

```
Optionally add a --driver-memory argument to specify memory (default is 1g)

```bash
spark-submit --driver-memory 50g \
  --class LineageAPI \
  target/scala-2.13/spark-query-api-assembly-0.1.jar \
  iceberg \
  tpch/parquet \
  tpch/queries/6.sql \
  my_catalog.default.usage_metadata \
  my_catalog

```


sourceType: one of csv, parquet, or iceberg

sourcePath: path to input directory or file

queryFile: SQL query file path (e.g., tpch/queries/6.sql)

usageTable: Iceberg table to log metadata (e.g., my_catalog.default.usage_metadata)

catalogName: Iceberg catalog name (e.g., my_catalog)

#### Iceberg warehouse path

By default, Iceberg tables (including the usage log table) are stored in:

```perl 
file:///tmp/iceberg/warehouse
```
This is configured via:

```scala 
.config("spark.sql.catalog.my_catalog.warehouse", "file:///tmp/iceberg/warehouse")
```

You do not need to manually create this directory — Iceberg will initialize it automatically. To customize this path, update the above line in LineageAPI.scala.

### 3. Querying the usage logs

Launch a spark shell with iceberg support:

```bash
spark-shell \
  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.13:1.8.1 \
  --conf spark.sql.catalog.my_catalog=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.my_catalog.type=hadoop \
  --conf spark.sql.catalog.my_catalog.warehouse=file:///tmp/iceberg/warehouse
```

Then run:
```scala
spark.sql("USE my_catalog.default")
spark.sql("SELECT * FROM usage_metadata ORDER BY timestamp DESC").show(false)
```

#### Data schema logged (per query):

| Field        | Type      | Description                                                       |
|--------------|-----------|-------------------------------------------------------------------|
| `tableName`  | STRING    | Name of the table being accessed                                 |
| `columnName` | STRING    | Name of the column that was referenced                           |
| `rowGroupId` | INT       | Row group ordinal (currently always NULL)                        |
| `dataTaskId` | STRING    | Unique ID: `{SparkQueryId}_{ScriptRunUUID}`                      |
| `timestamp`  | TIMESTAMP | Time when the query executed                                     |
| `utility`    | DOUBLE    | Placeholder utility score (currently set to 1.0 for all entries) |
