import org.apache.spark.sql.{SparkSession}
import org.apache.spark.sql.execution.QueryExecution
import org.apache.spark.sql.util.QueryExecutionListener
import java.io.File

object LineageAPI {

  def main(args: Array[String]): Unit = {
    if (args.length < 5) {
      println("Usage: LineageAPI <sourceType> <sourcePath> <queryFile> <usageTable> <catalogName>")
      sys.exit(1)
    }

    val sourceType = args(0).toLowerCase
    val sourcePath = args(1)
    val queryFilePath = args(2)
    val catalogName = args(4)
    val query = scala.io.Source.fromFile(queryFilePath).mkString

    val spark = SparkSession.builder()
      .appName("LineageAPI")
      .master("local[*]")
      .getOrCreate()


    // Register listener for capturing usage metadata
    spark.listenerManager.register(new EmptyListener)


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

  // Listener that does nothing
  class EmptyListener extends QueryExecutionListener {
    override def onSuccess(funcName: String, qe: QueryExecution, durationNs: Long): Unit = { /* noop */ }
    override def onFailure(funcName: String, qe: QueryExecution, exception: Exception): Unit =
      println(s"Query failed inside listener: ${exception.getMessage}")
  }
}
