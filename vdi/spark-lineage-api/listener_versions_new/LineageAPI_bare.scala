import org.apache.spark.sql.{DataFrame, SaveMode, SparkSession}
import org.apache.spark.sql.execution.QueryExecution
import org.apache.spark.sql.util.QueryExecutionListener
import org.apache.spark.sql.catalyst.expressions.AttributeReference
import org.apache.hadoop.fs.Path
import java.time.Instant
import java.io.{BufferedWriter, File, FileWriter}
import java.util.concurrent.{CountDownLatch, TimeUnit}

import scala.util.Using

object LineageAPI {

  // One query in flight at a time, as in the rowgroup variant.
  val NUM_QUERIES_EXECUTING: Int = 1
  // The only event a collector may act on is its own query's: show() reaches the listener
  // as action "head" (Dataset.show -> take -> head). The usage-log write inside onSuccess is
  // itself a Spark job and fires its own event ("command"); acted on, it released the NEXT
  // query's latch early and, for the last query, lost its rows to a stopped context
  // (found in Phase E: the second query of a run logged no row groups).
  val QUERY_ACTION: String = "head"
  // Upper bound on the post-query wait for the listener (not on the query itself, which
  // has already returned). 30 min pending a measured listener time from Phase E.
  val LISTENER_TIMEOUT_MIN: Long = 30

  // Case class to capture usage log entries
  case class UsageLog(
    tableName: String,
    columnName: String,
    rowGroupId: Option[Int],
    dataTaskId: String,
    timestamp: Instant,
    utility: Double
  )

  def listFiles(dir: String): Array[String] = {
    // Sorted and .sql-only so query order is deterministic (listFiles has no defined order)
    new File(dir).listFiles().map(_.getAbsolutePath).filter(_.endsWith(".sql")).sorted
  }

  private def appendToCsv(filePath: String, headers: Seq[String], row: Seq[Any]): Unit = {
    val file = new File(filePath)
    val writeHeaders = !file.exists() || file.length() == 0

    Using.resource(new BufferedWriter(new FileWriter(file, true))) { bw =>
      if (writeHeaders) {
        bw.write(headers.mkString(","))
        bw.newLine()
      }
      bw.write(row.mkString(","))
      bw.newLine()
    }
  }


  def main(args: Array[String]): Unit = {
    if (args.length < 5) {
      println("Usage: LineageAPI <sourceType> <sourcePath> <queryFile> <usageTable> <catalogName>")
      sys.exit(1)
    }

    val sourceType = args(0).toLowerCase
    val sourcePath = args(1)
    val queryDir = args(2)
    val catalogName = args(4)

    // Generate a unique ID per script run to differentiate executions
    val scriptExecId = java.util.UUID.randomUUID().toString
    val isTpch: Boolean = sourcePath.contains("tpch")
    val dataset = if (isTpch) "tpch" else "tpcds"
    val queryList = listFiles(queryDir)
    val headers = Seq("query", "dataset", "runtime", "listener_timeout")
    val outfile = "spark_internal_listener_bare_results.csv"
    val queryStartedFile = "spark_bare_queries_started.csv"

    val spark = SparkSession.builder()
      .appName("LineageAPI")
      // Master intentionally unset: governed by --master on spark-submit, so the
      // same jar runs single-node (spark-submit defaults to local[*]) or against a
      // standalone cluster. Setting it here silently overrides --master.
      .config(s"spark.sql.catalog.$catalogName", "org.apache.iceberg.spark.SparkCatalog")
      .config(s"spark.sql.catalog.$catalogName.type", "hadoop")
      .config(s"spark.sql.catalog.$catalogName.warehouse", "file:///tmp/iceberg/warehouse")
      // don't reuse computation
      .config("spark.sql.execution.reuseExchange", "false")
      .config("spark.sql.execution.reuseSubquery", "false")
      .getOrCreate()

    // Create usage table if it doesn't exist
    import spark.implicits._

    // Load source data into Spark
    loadData(spark, sourceType, sourcePath, catalogName)
    if (sourceType == "iceberg") spark.sql(s"USE $catalogName.default")

    // Only create the table if the storage path doesn't exist
    // The path comes from args(3), as in the rowgroup variant. It used to be
    // hardcoded to /tmp/iceberg/warehouse/usage_logs, which on a multi-node
    // cluster makes each executor write its task output to its own node's /tmp,
    // where the driver's job commit can't find it. Pass a shared path
    // (s3a:// or hdfs://) for cluster runs.
    // Done once, before the loop: inside the timed window it added a storage
    // round trip to every query that vanilla and rowgroup do not pay.
    val usageTablePath = args(3)

    val usagePath = new org.apache.hadoop.fs.Path(usageTablePath)
    val fs = usagePath.getFileSystem(spark.sparkContext.hadoopConfiguration)
    val exists = fs.exists(usagePath)

    if (!exists) {
      val emptyDF = Seq.empty[UsageLog].toDF()
      emptyDF.write.format("parquet").save(usageTablePath)
    }

    for (i <- 1 to 1) {
      for (queryFilePath <- queryList) {
        // not returning cached query result
        spark.catalog.clearCache()
        val queryName = new File(queryFilePath).getName

        // Log the query name to queryStartedFile
        appendToCsv(queryStartedFile, Seq("query"), Seq(queryName))
        val startTime = System.currentTimeMillis()

        // Register listener for capturing usage metadata
        val queryLatch = new CountDownLatch(NUM_QUERIES_EXECUTING)
        val usageCollector = new UsageCollector(spark, usageTablePath, scriptExecId, queryLatch)
        spark.listenerManager.register(usageCollector)

        // Ensuring io Source is closed
        val query = Using(scala.io.Source.fromFile(queryFilePath)) {
          _.mkString
        }.get

        try {
          val resultDF = spark.sql(query)
          resultDF.show()
          val endTime = System.currentTimeMillis()

          // Wait for the listener before the next query, as in the rowgroup variant.
          // Outside the timed window: runtime is what the user waits for. Without the
          // wait, unregister below can drop the listener before its event is delivered,
          // and its work can overlap the next query's timing.
          // Bounded wait, flag-and-continue: a dropped listener event must not hang the
          // run. On timeout the row is flagged and the run moves on; treat this query and
          // the next one as suspect for this rep.
          val listenerTimedOut = !queryLatch.await(LISTENER_TIMEOUT_MIN, TimeUnit.MINUTES)
          if (listenerTimedOut)
            println(s"WARNING: listener did not finish within $LISTENER_TIMEOUT_MIN min for $queryName; continuing")
          val runtime = endTime - startTime
          val data = Seq(queryName, dataset, runtime, listenerTimedOut)
          appendToCsv(outfile, headers, data)
        } catch {
          case e: Exception =>
            println(s"Query failed: ${e.getMessage}")
            val data = Seq(queryName, dataset, -1, false)
            appendToCsv(outfile, headers, data)
        } finally {
          spark.listenerManager.unregister(usageCollector)
        }

      }
    }
    spark.stop()
  }

  // Load data from given path and register views or tables
  def loadData(spark: SparkSession, sourceType: String, path: String, catalogName: String): Unit = {
    // Data is enumerated through the Hadoop FileSystem API rather than java.io.File so
    // that the same code works against hdfs:// and s3a:// as well as local paths.
    // java.io.File cannot see a distributed filesystem: listFiles() returns null for an
    // hdfs:// path, which would register no tables at all and leave every query failing
    // with an unrelated "table not found".
    val root = new Path(path)
    val fs = root.getFileSystem(spark.sparkContext.hadoopConfiguration)

    if (!fs.exists(root)) {
      println(s"sourcePath does not exist: $path")
      sys.exit(1)
    }
    val isDir = fs.getFileStatus(root).isDirectory

    // Paths from listStatus are fully qualified (scheme://authority/path), so executors
    // resolve exactly what the driver enumerated instead of relying on fs.defaultFS.
    // Sorted for deterministic registration order across runs.
    def childrenWithSuffix(suffix: String): Array[Path] =
      fs.listStatus(root)
        .filter(st => st.isFile && st.getPath.getName.endsWith(suffix))
        .map(_.getPath)
        .sortBy(_.toString)

    if (sourceType == "iceberg") {
      if (!isDir) {
        println(s"Iceberg sourcePath must be a directory of Parquet files. Found: $path")
        sys.exit(1)
      }
      childrenWithSuffix(".parquet").foreach { p =>
        val tableName = p.getName.stripSuffix(".parquet")
        val icebergTable = s"$catalogName.default.$tableName"
        val df = spark.read.parquet(p.toString)
        df.writeTo(icebergTable).using("iceberg").createOrReplace()
      }
    } else if (isDir) {
      childrenWithSuffix(s".$sourceType").foreach { p =>
        val viewName = p.getName.stripSuffix(s".$sourceType")
        val df = sourceType match {
          case "csv" => spark.read.option("header", "true").option("inferSchema", "true").csv(p.toString)
          case "parquet" => spark.read.parquet(p.toString)
        }
        df.createOrReplaceTempView(viewName)
      }
    } else {
      val viewName = root.getName.stripSuffix(s".$sourceType")
      val df = sourceType match {
        case "csv" => spark.read.option("header", "true").option("inferSchema", "true").csv(root.toString)
        case "parquet" => spark.read.parquet(root.toString)
      }
      df.createOrReplaceTempView(viewName)
    }
  }

  // Listener that logs table/column usage after each query
  class UsageCollector(spark: SparkSession, usageTablePath: String, scriptExecId: String,
                       queryLatch: CountDownLatch)
    extends QueryExecutionListener {

    override def onSuccess(funcName: String, qe: QueryExecution, durationNs: Long): Unit = {
      if (funcName != QUERY_ACTION) return
      try {
        val _ = qe.analyzed
      } finally {
        queryLatch.countDown()
      }
    }

    override def onFailure(funcName: String, qe: QueryExecution, exception: Exception): Unit = {
      if (funcName != QUERY_ACTION) return
      try {
        println(s"Query failed: ${exception.getMessage}")
      } finally {
        queryLatch.countDown()
      }
    }
  }
}
