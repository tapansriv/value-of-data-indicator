import org.apache.spark.sql.SparkSession
import java.io.File

object QueryRunner {
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
    if (args.length != 2) {
      println("Usage: QueryRunner <queryFile> <dataPath>")
      sys.exit(1)
    }

    val queryDir = args(0)
    val dataPath = args(1)

    val isTpch: Boolean = sourcePath.contains("tpch")
    val dataset = if (isTpch) "tpch" else "tpcds"
    val queryList = listFiles(queryDir)
    val headers = Seq("query", "dataset", "runtime")
    val outfile = "spark_internal_vanilla_results.csv"
    val queryStartedFile = "spark_internal_vanilla_queries_started.csv"


    val spark = SparkSession.builder()
      .appName("QueryRunner")
      .master("local[*]")
      // don't reuse computation
      .config("spark.sql.execution.reuseExchange", "false")
      .config("spark.sql.execution.reuseSubquery", "false")
      .getOrCreate()

    // Load all Parquet files in dataPath as temp views
    val files = new File(dataPath).listFiles().filter(_.getName.endsWith(".parquet"))
    files.foreach { file =>
      val tableName = file.getName.stripSuffix(".parquet")
      val df = spark.read.parquet(file.getAbsolutePath)
      df.createOrReplaceTempView(tableName)
    }

    for (i <- 1 to 3) {
      for (queryFile <- queryList) {
        // Read query from file and run it
        val startTime = System.currentTimeMillis()
        val query = scala.io.Source.fromFile(queryFile).mkString
        val result = spark.sql(query)
        result.show()
        val endTime = System.currentTimeMillis()
        val runtime = endTime - startTime
        val data = Seq(queryName, dataset, runtime)
        appendToCsv(outfile, headers, data)
      }
    }


    spark.stop()
  }
}
