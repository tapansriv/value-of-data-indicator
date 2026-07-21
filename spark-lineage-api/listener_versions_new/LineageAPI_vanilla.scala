import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.{FileSourceScanExec, QueryExecution, SparkPlan}
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

    val scriptExecId = java.util.UUID.randomUUID().toString
    val isTpch: Boolean = sourcePath.contains("tpch")
    val dataset = if (isTpch) "tpch" else "tpcds"
    val queryList = listFiles(queryDir)
    val headers = Seq("query", "dataset", "runtime")
    val outfile = "spark_internal_listener_vanilla_results.csv"
    val queryStartedFile = "spark_vanilla_queries_started.csv"

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
          val data = Seq(queryName, dataset, runtime)
          appendToCsv(outfile, headers, data)
        } catch {
          case e: Exception =>
            println(s"Query failed: ${e.getMessage}")
            val data = Seq(queryName, dataset, -1)
            appendToCsv(outfile, headers, data)
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
}
