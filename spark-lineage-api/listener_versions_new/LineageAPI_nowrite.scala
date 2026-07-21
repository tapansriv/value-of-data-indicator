import org.apache.spark.sql.{DataFrame, SaveMode, SparkSession}
import org.apache.spark.sql.execution.QueryExecution
import org.apache.spark.sql.util.QueryExecutionListener
import org.apache.spark.sql.catalyst.expressions.AttributeReference
import java.time.Instant
import java.io.{BufferedWriter, File, FileWriter}

import scala.util.Using

object LineageAPI {

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
    val catalogName = args(4)

    val scriptExecId = java.util.UUID.randomUUID().toString
    val isTpch: Boolean = sourcePath.contains("tpch")
    val dataset = if (isTpch) "tpch" else "tpcds"
    val queryList = listFiles(queryDir)
    val headers = Seq("query", "dataset", "runtime")
    val outfile = "spark_internal_listener_nowrite_results.csv"
    val queryStartedFile = "spark_nowrite_queries_started.csv"


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

    // Load source data into Spark
    loadData(spark, sourceType, sourcePath, catalogName)
    if (sourceType == "iceberg") spark.sql(s"USE $catalogName.default")

    for (i <- 1 to 1) {
      for (queryFilePath <- queryList) {
        // not returning cached query result
        spark.catalog.clearCache()
        val queryName = new File(queryFilePath).getName

        // Log the query name to queryStartedFile
        appendToCsv(queryStartedFile, Seq("query"), Seq(queryName))

        val startTime = System.currentTimeMillis()

        // Register listener (no-write version)
        val usageCollector = new UsageCollector(spark, scriptExecId)
        spark.listenerManager.register(usageCollector)

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
          case e: Exception => println(s"Query failed: ${e.getMessage}")
        } finally {
          spark.listenerManager.unregister(usageCollector)
        }
      }
    }
    spark.stop()
  }

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

  // Listener that collects metadata but skips writing to disk
  class UsageCollector(spark: SparkSession, scriptExecId: String)
    extends QueryExecutionListener {

    override def onSuccess(funcName: String, qe: QueryExecution, durationNs: Long): Unit = {
      val dataTaskId = s"${qe.id}_$scriptExecId"
      val timestamp = Instant.now()

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
        .mapValues(_.map(_._2).toSet)
        .toMap

      if (inputColumnsByTable.nonEmpty) {
        // Still simulate log construction
        val usageLogs = inputColumnsByTable.flatMap { case (tableName, columns) =>
          columns.map { colName =>
            UsageLog(tableName, colName, None, dataTaskId, timestamp, 1.0)
          }
        }.toSeq

        // Do NOT write to disk
        // import spark.implicits._
        // val usageDF = spark.createDataset(usageLogs).toDF()
        // usageDF.write.mode(SaveMode.Append).parquet(usageTablePath)
      }
    }

    override def onFailure(funcName: String, qe: QueryExecution, exception: Exception): Unit = {
      println(s"Query failed: ${exception.getMessage}")
    }
  }
}
