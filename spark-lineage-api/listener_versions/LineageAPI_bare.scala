import org.apache.spark.sql.{DataFrame, SaveMode, SparkSession}
import org.apache.spark.sql.execution.QueryExecution
import org.apache.spark.sql.util.QueryExecutionListener
import org.apache.spark.sql.catalyst.expressions.AttributeReference
import java.time.Instant
import java.io.File

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

  def main(args: Array[String]): Unit = {
    if (args.length < 5) {
      println("Usage: LineageAPI <sourceType> <sourcePath> <queryFile> <usageTable> <catalogName>")
      sys.exit(1)
    }

    val sourceType = args(0).toLowerCase
    val sourcePath = args(1)
    val queryFilePath = args(2)
    val catalogName = args(4)
    // Generate a unique ID per script run to differentiate executions
    val scriptExecId = java.util.UUID.randomUUID().toString
    val query = scala.io.Source.fromFile(queryFilePath).mkString

    val spark = SparkSession.builder()
      .appName("LineageAPI")
      .master("local[*]")
      .config(s"spark.sql.catalog.$catalogName", "org.apache.iceberg.spark.SparkCatalog")
      .config(s"spark.sql.catalog.$catalogName.type", "hadoop")
      .config(s"spark.sql.catalog.$catalogName.warehouse", "file:///tmp/iceberg/warehouse")
      .getOrCreate()

    // Create usage table if it doesn't exist
    import spark.implicits._

    // Only create the table if the storage path doesn't exist
    val usageTablePath = "/tmp/iceberg/warehouse/usage_logs"

    val fs = org.apache.hadoop.fs.FileSystem.get(spark.sparkContext.hadoopConfiguration)
    val exists = fs.exists(new org.apache.hadoop.fs.Path(usageTablePath))

    if (!exists) {
      val emptyDF = Seq.empty[UsageLog].toDF()
      emptyDF.write.format("parquet").save(usageTablePath)
    }

    // Register listener for capturing usage metadata
    val usageCollector = new UsageCollector(spark, usageTablePath, scriptExecId)
    spark.listenerManager.register(usageCollector)

    // Load source data into Spark
    loadData(spark, sourceType, sourcePath, catalogName)

    if (sourceType == "iceberg") spark.sql(s"USE $catalogName.default")

    try {
      val resultDF = spark.sql(query)
      resultDF.show()
    } catch {
      case e: Exception => println(s"Query failed: ${e.getMessage}")
    } finally {
      spark.stop()
    }
  }

  // Load data from given path and register views or tables
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

  // Listener that logs table/column usage after each query
  class UsageCollector(spark: SparkSession, usageTablePath: String, scriptExecId: String)
    extends QueryExecutionListener {

    override def onSuccess(funcName: String, qe: QueryExecution, durationNs: Long): Unit = {
      val _ = qe.analyzed
    }

    override def onFailure(funcName: String, qe: QueryExecution, exception: Exception): Unit = {
      println(s"Query failed: ${exception.getMessage}")
    }
  }
}
