import org.apache.spark.sql.SparkSession
import java.io.File

object QueryRunner {
  def main(args: Array[String]): Unit = {
    if (args.length != 2) {
      println("Usage: QueryRunner <queryFile> <dataPath>")
      sys.exit(1)
    }

    val queryFile = args(0)
    val dataPath = args(1)

    val spark = SparkSession.builder()
      .appName("QueryRunner")
      // Master intentionally unset: governed by --master on spark-submit, so the
      // same jar runs single-node (spark-submit defaults to local[*]) or against a
      // standalone cluster. Setting it here silently overrides --master.
      .getOrCreate()

    // Load all Parquet files in dataPath as temp views
    val files = new File(dataPath).listFiles().filter(_.getName.endsWith(".parquet"))
    files.foreach { file =>
      val tableName = file.getName.stripSuffix(".parquet")
      val df = spark.read.parquet(file.getAbsolutePath)
      df.createOrReplaceTempView(tableName)
    }

    // Read query from file and run it
    val query = scala.io.Source.fromFile(queryFile).mkString
    val result = spark.sql(query)
    result.show()

    spark.stop()
  }
}
