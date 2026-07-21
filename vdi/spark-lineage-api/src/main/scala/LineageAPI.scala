import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.{FileSourceScanExec, QueryExecution, SparkPlan}
import org.apache.spark.sql.execution.datasources.parquet.RowGroupMetricsRegistry
import org.apache.spark.sql.util.QueryExecutionListener

import java.time.Instant
import java.sql.Timestamp
import java.io.{BufferedWriter, File, FileWriter}
import scala.collection.mutable.ListBuffer
import org.apache.log4j.Logger
import org.apache.spark.sql.catalyst.expressions.AttributeReference
import org.apache.spark.sql.execution.adaptive.{AdaptiveSparkPlanExec, BroadcastQueryStageExec, ShuffleQueryStageExec}

import java.util.concurrent.CountDownLatch
import java.util.regex.Pattern
import scala.language.postfixOps
import scala.util.Using



object LineageAPI {
  val logger: Logger = Logger.getLogger(this.getClass)
  // Assuming num queries running is hard coded for a Latch. This logic can be changed if application
  // is serving continuous requests using a different synchronization barrier system.
  // This is to ensure main thread waits until all listeners have completed before flushing logs and exiting
  val NUM_QUERIES_EXECUTING: Int = 1

  def listFiles(dir: String): Array[String] = {
    new File(dir).listFiles().map(_.getAbsolutePath)
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
    val headers = Seq("query", "dataset", "runtime")
    val outfile = "spark_internal_listener_rowgroup_results.csv"

    val spark = SparkSession.builder()
      .appName("LineageAPI")
      .master("local[*]")
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


    for (i <- 1 to 9) {
      val listenerLogFile = s"${usageTablePath}_${dataset}_run${i}"
      for (queryFilePath <- queryList) {
        // not returning cached query result
        spark.catalog.clearCache()
        val queryName = new File(queryFilePath).getName
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
          queryLatch.await()
          val runtime = endTime - startTime
          val data = Seq(queryName, dataset, runtime)
          appendToCsv(outfile, headers, data)
        } catch {
          case e: Exception =>
            println(s"Query failed: ${e.getMessage}")
            val data = Seq(queryName, dataset, -1)
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
    val dir = new File(path)

    if (sourceType == "iceberg") {
      if (!dir.isDirectory) {
        println(s"Iceberg sourcePath must be a directory of Parquet files. Found: $path")
        sys.exit(1)
      }
      val files = dir.listFiles().filter(_.getName.endsWith(".parquet"))
      files.foreach { file =>
        val tableName = file.getName.stripSuffix(".parquet")
        val icebergTable = s"$catalogName.default.$tableName"
        val df = spark.read.parquet(file.getAbsolutePath)
        df.writeTo(icebergTable).using("iceberg").createOrReplace()
      }
    } else if (dir.isDirectory) {
      val files = dir.listFiles().filter(f =>
        f.isFile && ((sourceType == "csv" && f.getName.endsWith(".csv")) ||
                     (sourceType == "parquet" && f.getName.endsWith(".parquet")))
      )
      files.foreach { file =>
        val viewName = file.getName.stripSuffix(s".$sourceType")
        val df = sourceType match {
          case "csv" => spark.read.option("header", "true").option("inferSchema", "true").csv(file.getAbsolutePath)
          case "parquet" => spark.read.parquet(file.getAbsolutePath)
        }
        df.createOrReplaceTempView(viewName)
      }
    } else {
      val viewName = new File(path).getName.stripSuffix(s".$sourceType")
      val df = sourceType match {
        case "csv" => spark.read.option("header", "true").option("inferSchema", "true").csv(path)
        case "parquet" => spark.read.parquet(path)
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

    private val regex_prefix = {
      val absPath = new File(dataPath).getAbsolutePath
      Pattern.quote(s"file://$absPath/")
    }

    private val regex_extension = """\.parquet"""

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

          // extract the (file, rgs) pairs from the accumulator
          val rowGroupsForQuery = RowGroupMetricsRegistry.get(execId).map(_.value).get
          rowGroupsForQuery.iterator.foreach { e =>
            val (filePath, rg_info) = e
            val tbl = filePath.split(regex_prefix)(1).split(regex_extension)(0)
            rg_info.foreach { info =>
              val (_, offset, size) = info
              logsBuffer.addOne(tbl, null, offset, size, dataTaskId, timestamp, 1.0)
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
      try {
        println(s"Query failed: ${exception.getMessage}")
        if (useRowGroups) {
          val execId = getExecIdFromQE(qe) match {
            case Some(value) => value
            case None => return
          }

          if (RowGroupMetricsRegistry.get(execId).isDefined)
            RowGroupMetricsRegistry.remove(execId)
        }
      } finally {
        queryLatch.countDown()
      }
    }
  }
}
