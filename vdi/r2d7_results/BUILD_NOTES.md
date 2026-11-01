# Build notes: instrumented Spark stack (R2D7 scale-factor run)

Built 2026-09-26 on Chameleon node (Ubuntu 24.04, 40 cores, 62 GB RAM), user cc.
Everything below was verified on this machine; outputs are quoted verbatim.

**SPARK_HOME to use: `/home/cc/value_of_data/spark`** (source-tree build; jars in
`assembly/target/scala-2.13/jars/`). No `make-distribution.sh` tarball was built
(only needed for multi-node deployment).

## Toolchain
- Java: OpenJDK 17.0.20.1 (build 17.0.20.1+1-1-24.04-Ubuntu), JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
- Maven (system): 3.8.7, used for parquet-java and the listener check
- Maven (Spark): `build/mvn` downloaded Maven 3.9.6 and Scala 2.13.8 into `spark/build/` (untracked/ignored; `git status` still shows only the 2 intended modified files)

## 1. Thrift 0.16.0 (compiler only)
- Source: https://archive.apache.org/dist/thrift/0.16.0/thrift-0.16.0.tar.gz
  sha256 `f460b5c1ca30d8918ff95ea3eb6291b3951cf518553566088f3f2be8981f6209`
- Built in `~/build/thrift-0.16.0`:
  `./configure --disable-libs --disable-tests --disable-tutorial --without-{cpp,python,py3,java,nodejs,go,rs,php,ruby,perl,c_glib,qt5,erlang,haskell,lua,dart,swift,netstd,d,nodets,kotlin}`
  then `make -j16` (~29 s) and `sudo make install`. No extra apt packages were needed.
- `thrift --version` -> `Thrift version 0.16.0` (`/usr/local/bin/thrift`)

## 2. parquet-java fork
- Repo `/home/cc/value_of_data/parquet-java`, branch `vod_rg`, HEAD `5d67eec21a2ac522003ff2827dddbeab91ec4cdc`, clean working tree
- Diff vs release commit `db418310` (1.13.1-rc0): only `RowGroupFilter.java` (+ README_rg)
- Command: `MAVEN_OPTS="--add-opens java.base/java.lang=ALL-UNNAMED -Xmx4g" mvn -B clean install -pl parquet-hadoop -DskipTests`
  (1m39s. Sibling modules parquet-column/common/encoding/format-structures/jackson 1.13.1 were
  resolved from Maven Central; they are unmodified in the fork. The log has "[ERROR] An error occurred
  attempting to read POM" lines from the CycloneDX SBOM plugin, an ISO-8859-1 POM encoding
  issue in a third-party POM. They are harmless: BUILD SUCCESS.)
- Installed jar: `~/.m2/repository/org/apache/parquet/parquet-hadoop/1.13.1/parquet-hadoop-1.13.1.jar`
  sha256 `50dcc11fabc25c825bd90fbcbfd6e1f21099d88220ae49999a921f569ebc2b4e`
- javap:
  ```
  public static org.apache.parquet.filter2.compat.RowGroupFilter$RowGroupFilterResult getLastResult();
  public static void clearResult();
  ```

## 3. Spark fork
- Repo `/home/cc/value_of_data/spark`, branch `rowgroup-dev`, HEAD `f0c593da74ac8d00834eecce26ce3845f9b64269`
- Uncommitted changes (deliberate, included in the build, not reverted):
  - `sql/core/src/main/scala/org/apache/spark/sql/execution/datasources/parquet/ParquetFileFormat.scala`
    (`RowGroupFilter.clearResult()` before initialize; `RowGroupMetricsRegistry.getOrCreate`; unfiltered scans record footer blocks instead of `(-1,0,-1)`)
  - `sql/core/src/main/scala/org/apache/spark/sql/execution/datasources/parquet/RowGroupMetricsRegistry.scala`
    (`getOrCreate` shared per-execution accumulator; synchronized `keys`)
  - `git diff | sha256sum` = `4821883f616fbb5c04ce5dccf73fbe78223ecee59638a76954c9742af95a7a13` (same before and after build)
  - Copy of the diff: `~/build/spark_uncommitted.diff`
- Scala version switch: **already done in committed poms** (`<scala.binary.version>2.13</scala.binary.version>`,
  `<scala.version>2.13.8</scala.version>`, no `_2.12` artifactIds left). `dev/change-scala-version.sh` was NOT run; no files changed.
- pom: `hadoop.version` 3.3.4, `parquet.version` 1.13.1
- Command (in tmux `sparkbuild`, script `~/build/spark_build.sh`):
  ```
  export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
  export MAVEN_OPTS="-Xss128m -Xmx8g -XX:ReservedCodeCacheSize=1g"
  ./build/mvn -B -DskipTests -Pscala-2.13 clean install
  ```
  No other profiles (default = hadoop-3; no -Phive / -Pyarn). Start 20:28:39Z, end 21:10:41Z; Maven "Total time: 41:49 min", BUILD SUCCESS.
  Log: `~/build/spark-build.log`
- Verification:
  - (a) `bin/spark-submit --version`: `version 3.5.5`, `Using Scala version 2.13.8, OpenJDK 64-Bit Server VM, 17.0.20.1`,
    `Branch rowgroup-dev`, `Revision f0c593da74ac8d00834eecce26ce3845f9b64269`
  - (b) Runtime parquet-hadoop `assembly/target/scala-2.13/jars/parquet-hadoop-1.13.1.jar` is byte-identical (cmp) to the fork
    jar in ~/.m2 (sha256 `50dcc11f...2b4e`); javap shows `getLastResult()` and `clearResult()`
  - (c) `assembly/target/scala-2.13/jars/spark-sql_2.13-3.5.5.jar` (sha256 `8b71ba1f604aa8a9aa9a1f67d04425cda9e63939198d0dcede12bec8b81f0256`,
    identical to the ~/.m2 copy):
    ```
    public static org.apache.spark.sql.execution.datasources.parquet.RowGroupAccumulator getOrCreate(java.lang.String, org.apache.spark.SparkContext);
    ```
    and `javap -c -p ParquetFileFormat.class` shows the calls:
    ```
    invokevirtual RowGroupMetricsRegistry$.getOrCreate:(Ljava/lang/String;Lorg/apache/spark/SparkContext;)...
    invokestatic  org/apache/parquet/filter2/compat/RowGroupFilter.clearResult:()V
    invokestatic  org/apache/parquet/filter2/compat/RowGroupFilter.getLastResult:()...
    ```

## 4. Listener compile check
- Worktree `/home/cc/value_of_data/spark-scale`, HEAD `e07871a2f95eca9ce7fc9a21acca8d7152305407` (uncommitted A1-A3 changes present)
  - `git diff -- spark-lineage-api | sha256sum` = `d804ef0534b1023207dd19eca2c0c199d4ad9482fcd3e8ac91cef6ac13ad65fd`
  - `listener_versions_new/LineageAPI_rgs.scala` file sha256 `a8d5c69d76d9547de249a33b96cd6d76964a16c0aa7fa813dcd2f2f169581da6`
- pom.xml properties: `spark.version` 3.5.5 (matches); `scala.version` **2.13.16, which does not match** Spark's 2.13.8.
  Not edited. It compiles, but the listener is compiled against a newer scala-library than the one Spark ships at runtime.
  Scala 2.13 is backward- but not forward-binary-compatible. This is only a problem if the listener calls a
  library API added after 2.13.8. To be safe, set `scala.version` to 2.13.8 when the capture jar is built.
- Throwaway project `~/build/listener-check` (pom.xml copy + LineageAPI_rgs.scala as src/main/scala/LineageAPI.scala):
  `mvn -B -q package` (26 s) -> **SUCCESS**, `target/spark-rowgroup-listener-1.0.0.jar` (7 classes; only deprecation warnings).
  `spark-sql_2.13:3.5.5` was resolved from the locally installed fork (~/.m2 `_remote.repositories` has empty repo id, 0 downloads).
  The source imports and calls `RowGroupMetricsRegistry.get/remove`, so it compiles against the fork's API.
  compile.sh was NOT run; no tracked files were touched.

## 5. Smoke test (SF1)
```
bin/spark-shell --master 'local[*]' --driver-memory 16g --conf spark.speculation=false \
  --conf spark.local.dir=/mnt/tpcds/spark-tmp --conf spark.ui.enabled=false < ~/build/smoke.scala
```
(The Scala 2.13 REPL did not execute `-i script` in non-tty mode, so the script is piped on stdin instead.)
Output (`~/build/smoke.log`):
```
SMOKE store_sales rows = 2880404
SMOKE join+filter count = 270656  (1.7 s)      # store_sales JOIN date_dim ON ss_sold_date_sk=d_date_sk WHERE d_year=2000 AND ss_quantity>50
SMOKE registry keys = [2, 3]
SMOKE exec 2: store_sales.parquet -> 1 rg
SMOKE exec 3: date_dim.parquet -> 1 rg, store_sales.parquet -> 1 rg
SMOKE speculation = false, version = 3.5.5, scala = version 2.13.8
```
The row count matches `_verify.json` (2880404; 1 row group each for store_sales and date_dim at SF1).
Exec 3 (the join) holds both scanned files in one accumulator, which is what the `getOrCreate` fix is meant to produce.
This is a one-query sanity check, not a validation of capture correctness.

## Update 2026-10-06: Spark fork `rowgroup-dev` now carries the R2D16 version of the fix

This R2D7 build used the `getOrCreate` fix (later committed as `1fb30a5`). R2D16 fixed the
same two bugs independently (`2d7540e`..`4ba4a96`), plus a third: the accumulator was
registered with a name, which attaches the full row-group map to every task-end event
(O(tasks²) driver memory and event-log volume; out-of-memory errors at TPC-H SF1000).
`tapansriv/spark` `rowgroup-dev` is now `7de9151`: an `-s ours` merge whose code is
identical to `4ba4a96`. `1fb30a5` remains in history, so **this R2D7 build stays
reproducible at `1fb30a5`**.

**API change for anything rebuilt from the new tip:** `RowGroupMetricsRegistry` keeps one
accumulator *per scan*. Read all of them with `getAll(execId)`; `get(execId)` returns only
the last scan's, so a listener using `get` would silently drop all but one table of every
join. The listener on `main` (`spark-lineage-api/listener_versions_new/LineageAPI_rgs.scala`,
merged from `spark-scale`) uses `getAll` and dedups row groups per query. Also pair the new
Spark tip with parquet-java `vod_rg` `6519501`. Details: `REVISION_SCALEUP_RUNLOG.md`
(issues 3–5).
