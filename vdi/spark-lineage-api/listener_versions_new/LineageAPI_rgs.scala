import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.{FileSourceScanExec, QueryExecution, SparkPlan}
import org.apache.spark.sql.execution.datasources.parquet.RowGroupMetricsRegistry
import org.apache.spark.sql.util.QueryExecutionListener

import org.apache.hadoop.fs.Path
import java.time.Instant
import java.sql.Timestamp
import java.io.{BufferedWriter, File, FileWriter}
import scala.collection.mutable.ListBuffer
import org.apache.log4j.Logger
import org.apache.spark.sql.catalyst.expressions.AttributeReference
import org.apache.spark.sql.execution.adaptive.{AdaptiveSparkPlanExec, BroadcastQueryStageExec, ShuffleQueryStageExec}

import java.util.concurrent.{CountDownLatch, TimeUnit}
import scala.language.postfixOps
import scala.util.Using



object LineageAPI {
  val logger: Logger = Logger.getLogger(this.getClass)
  // Assuming num queries running is hard coded for a Latch. This logic can be changed if application
  // is serving continuous requests using a different synchronization barrier system.
  // This is to ensure main thread waits until all listeners have completed before flushing logs and exiting
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
    val usageTablePath = args(3)
    val catalogName = args(4)
    val useRowGroups: Boolean = true

    val scriptExecId = java.util.UUID.randomUUID().toString
    val isTpch: Boolean = sourcePath.contains("tpch")
    val dataset = if (isTpch) "tpch" else "tpcds"
    val queryList = listFiles(queryDir)
    val headers = Seq("query", "dataset", "runtime", "listener_timeout")
    val outfile = "spark_internal_listener_rowgroup_results.csv"
    val queryStartedFile = "spark_rowgroup_queries_started.csv"


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

    // Load source data
    loadData(spark, sourceType, sourcePath, catalogName)
    logger.info("Data loaded into spark instance")
    if (sourceType == "iceberg") spark.sql(s"USE $catalogName.default")
    implicit val sparkImplicit: SparkSession = spark


    for (i <- 1 to 1) {
      val listenerLogFile = s"${usageTablePath}_${dataset}_run${i}"
      for (queryFilePath <- queryList) {
        // not returning cached query result
        spark.catalog.clearCache()
        val queryName = new File(queryFilePath).getName

        // Log the query name to queryStartedFile
        appendToCsv(queryStartedFile, Seq("query"), Seq(queryName))

        val startTime = System.currentTimeMillis()

        // Create and register the listener
        val queryLatch = new CountDownLatch(NUM_QUERIES_EXECUTING) // using hard coded value to initialize latch
        val usageCollector = new UsageCollector(scriptExecId, useRowGroups, queryLatch, sourcePath, usageTablePath)
        spark.listenerManager.register(usageCollector)

        // Ensuring io Source is closed
        val query = Using(scala.io.Source.fromFile(queryFilePath)) {
          _.mkString
        }.get

        try {
          val resultDF = spark.sql(query)
          val qId = resultDF.queryExecution.id
          appendToCsv(s"queryIdMap_${i}.csv", Seq("queryName", "queryID"), Seq(queryName, qId))
          resultDF.show()
          val endTime = System.currentTimeMillis()

          // Wait until query listener is completed before stopping the spark instance
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

  // Load data and register as views or tables
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


  // Listener that collects usage info
  class UsageCollector(scriptExecId: String,
                       useRowGroups: Boolean,
                       queryLatch: CountDownLatch,
                       dataPath: String,
                       usageTablePath: String)
                      (implicit spark: SparkSession) extends QueryExecutionListener {

    // The table name is the file's basename minus the .parquet extension: loadData
    // registers exactly one temp view per file under that same name, so the two must
    // agree. Deriving it from the basename is correct under any URI scheme.
    //
    // The previous version split the path on a literal "file://" + absolute-path prefix.
    // Under hdfs:// (or any other scheme, or a differently-slashed file: URI) the split
    // finds no match and the following (1) throws ArrayIndexOutOfBoundsException, which
    // onSuccess's caller reports as a generic query failure -- silent loss of all
    // row-group lineage rather than a visible error.
    private def tableNameOf(filePath: String): String =
      new Path(filePath).getName.stripSuffix(".parquet")

    type LogType = (String, // table name
                    String, // column name
                    Long, // row offset for start of row group
                    Long, // number of rows in row group
                    String, // data task id
                    Timestamp, // timestamp of query
                    Double) // utility

    /** Recursively dump plan tree */
    private def dump(plan: SparkPlan, depth: Int = 0): Unit = {
      val indent = "  " * depth
      println(s"$indent- ${plan.nodeName} (${plan.getClass.getName})")
      plan.children.foreach(child => dump(child, depth + 1))
    }

    /** Recursively collect FileSourceScanExec even inside QueryStages */
    private def collectFileScans(plan: SparkPlan): Seq[FileSourceScanExec] = plan match {
      case f: FileSourceScanExec => Seq(f)
      case s: ShuffleQueryStageExec => collectFileScans(s.plan)
      case b: BroadcastQueryStageExec => collectFileScans(b.plan)
      case _ => plan.children.flatMap(collectFileScans)
    }

    /** Parse execution ID from the QE. Validate that all nodes within the QE have same execID */
    private def getExecIdFromQE(qe: QueryExecution): Option[String] = {
      val scans = collectFileScans(qe.executedPlan match {
        case a: AdaptiveSparkPlanExec => a.executedPlan
        case other => other
      })
      val execIds = scans.collect { scan => scan.execId }
      // TODO: if no file scans performed during query execution, nothing to log, but thus that value goes nowhere
      if (execIds.isEmpty)
        return None

      // Get execution ID from the file scans. Ensure that all file scans being looked at are from the same execution
      // Should always be true, but assertion for safety if multiple query executions in spark session
      val execId = execIds.head
      assert(execIds.tail.forall(execId == _))
      Some(execId)
    }

    override def onSuccess(funcName: String, qe: QueryExecution, durationNs: Long): Unit = {
      if (funcName != QUERY_ACTION) return
      // metadata to add to time-series
      val logsBuffer = ListBuffer[(String, String, Long, Long, String, Timestamp, Double)]()

      val dataTaskId = s"${qe.id}_$scriptExecId"
      val timestamp = Timestamp.from(Instant.now())

      try {
        if (useRowGroups) {
          val execId = getExecIdFromQE(qe) match {
            case Some(value) => value
            case None => return
          }

          // extract the (file, rgs) pairs from every scan's accumulator: one per Parquet
          // scan, so a join has several (RowGroupMetricsRegistry.getAll; get() returned only
          // the last scan's). A table scanned twice in one query (Q2, Q21) is logged once per
          // row group.
          val seen = scala.collection.mutable.HashSet.empty[(String, Long, Long)]
          RowGroupMetricsRegistry.getAll(execId).foreach { acc =>
            acc.value.iterator.foreach { e =>
              val (filePath, rg_info) = e
              val tbl = tableNameOf(filePath)
              rg_info.foreach { info =>
                val (_, offset, size) = info
                if (seen.add((filePath, offset, size)))
                  logsBuffer.addOne(tbl, null, offset, size, dataTaskId, timestamp, 1.0)
              }
            }
          }
          // logger.info(rowGroupsForQuery)
          // cleanup accumulator registry
          RowGroupMetricsRegistry.remove(execId)
        } else {
          val allAttrs = qe.analyzed.collect {
            case plan =>
              plan.expressions.flatMap(_.collect {
                case attr: AttributeReference => attr
              })
          }.flatten

          val inputColumnsByTable = allAttrs
            .filter(_.qualifier.nonEmpty)
            .map(attr => attr.qualifier.last -> attr.name)
            .filterNot { case (_, col) => col.matches("^_\\d+$") }
            .groupBy(_._1)
            .view.mapValues(_.map(_._2).toSet)
            .toMap

          inputColumnsByTable.foreach { case (table, cols) =>
            cols.foreach { col =>
              logsBuffer += ((table, col, -1, -1, dataTaskId, timestamp, 1.0))
            }
          }
        }
        import spark.implicits._
        if (logsBuffer.nonEmpty) {
          val usageDF = logsBuffer.toSeq.toDF(
            "tableName", "columnName", "rowGroupOffset", "rowGroupSize", "dataTaskId", "timestamp", "utility"
          )
          usageDF.write.mode("append").parquet(usageTablePath)
          logger.info(s"Appended ${logsBuffer.size} usage rows to $usageTablePath")
        }
      } finally {
        queryLatch.countDown()
      }
    }

    override def onFailure(funcName: String, qe: QueryExecution, exception: Exception): Unit = {
      if (funcName != QUERY_ACTION) return
      try {
        println(s"Query failed: ${exception.getMessage}")
        if (useRowGroups) {
          val execId = getExecIdFromQE(qe) match {
            case Some(value) => value
            case None => return
          }

          RowGroupMetricsRegistry.remove(execId)
        }
      } finally {
        queryLatch.countDown()
      }
    }
  }
}
