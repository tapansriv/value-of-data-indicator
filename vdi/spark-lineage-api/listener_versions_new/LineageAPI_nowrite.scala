import org.apache.spark.sql.{DataFrame, SaveMode, SparkSession}
import org.apache.spark.sql.execution.QueryExecution
import org.apache.spark.sql.util.QueryExecutionListener
import org.apache.spark.sql.catalyst.expressions.AttributeReference
import org.apache.hadoop.fs.Path
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

    val scriptExecId = java.util.UUID.randomUUID().toString
    val isTpch: Boolean = sourcePath.contains("tpch")
    val dataset = if (isTpch) "tpch" else "tpcds"
    val queryList = listFiles(queryDir)
    val headers = Seq("query", "dataset", "runtime")
    val outfile = "spark_internal_listener_nowrite_results.csv"
    val queryStartedFile = "spark_nowrite_queries_started.csv"


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
