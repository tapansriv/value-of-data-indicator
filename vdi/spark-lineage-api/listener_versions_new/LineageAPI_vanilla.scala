import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.{FileSourceScanExec, QueryExecution, SparkPlan}
import org.apache.spark.sql.util.QueryExecutionListener

import org.apache.hadoop.fs.Path
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

    val scriptExecId = java.util.UUID.randomUUID().toString
    val isTpch: Boolean = sourcePath.contains("tpch")
    val dataset = if (isTpch) "tpch" else "tpcds"
    val queryList = listFiles(queryDir)
    val headers = Seq("query", "dataset", "runtime", "listener_timeout")
    val outfile = "spark_internal_listener_vanilla_results.csv"
    val queryStartedFile = "spark_vanilla_queries_started.csv"

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
      for (queryFilePath <- queryList) {
        // not returning cached query result
        spark.catalog.clearCache()
        val queryName = new File(queryFilePath).getName

        // Log the query name to queryStartedFile
        appendToCsv(queryStartedFile, Seq("query"), Seq(queryName))

        val startTime = System.currentTimeMillis()

        // Ensuring io Source is closed
        val query = Using(scala.io.Source.fromFile(queryFilePath)) {
          _.mkString
        }.get

        try {
          val resultDF = spark.sql(query)
          resultDF.show()
          val endTime = System.currentTimeMillis()
          val runtime = endTime - startTime
          val data = Seq(queryName, dataset, runtime, false)  // no listener; column kept for a uniform schema
          appendToCsv(outfile, headers, data)
        } catch {
          case e: Exception =>
            println(s"Query failed: ${e.getMessage}")
            val data = Seq(queryName, dataset, -1, false)
            appendToCsv(outfile, headers, data)
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
}
