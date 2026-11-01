import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.QueryExecution
import org.apache.spark.sql.execution.datasources.parquet.RowGroupMetricsRegistry
import org.apache.spark.sql.util.QueryExecutionListener

import org.apache.hadoop.fs.Path
import java.io.{BufferedWriter, File, FileWriter}
import java.util.concurrent.{CountDownLatch, TimeUnit}
import scala.util.Using

/**
 * Row-group access capture for the R2D7 scale-factor run.
 *
 * Runs each TPC-DS query once through the instrumented Spark and writes, per query, every
 * (file, row group) the Parquet scans read. oracle/scripts/spark_rg_to_access.py turns the
 * output into the per-query access.json that assign_val_to_de.py consumes.
 *
 * Differs from LineageAPI_rgs.scala (the overhead-benchmark variant, left untouched):
 *  - Executes with collect(), not show(). show() plans a separate limit query whose id does
 *    not match the one being tracked, and a limit can stop a final-stage scan early.
 *  - Records the query name and row-group ordinal alongside offset and row count.
 *  - Finds the statement's execution IDs from the registry itself (IDs that appear while it
 *    runs; statements run one at a time), not by walking the final plan: when AQE finds a
 *    stage empty it replaces that part of the plan, and every scan can vanish from it even
 *    though the scans ran.
 *  - Runs each statement of a multi-statement file (TPC-DS 14, 23, 24, 39) and attributes
 *    all of them to that query.
 *  - Writes plain CSV from the driver instead of a Spark job, so logging never re-enters
 *    the listener.
 *
 * Usage: RowGroupCapture <parquetDir> <queryDir> <outDir> [firstQuery-lastQuery]
 *   parquetDir: flat directory of <table>.parquet files, one file per table
 *   queryDir:   directory of queryN.sql files (Spark dialect)
 *   outDir:     local directory; gets queries.csv, rg/<N>.csv, rg/<N>.done, spark_conf.txt
 * Queries whose rg/<N>.done exists are skipped, so an interrupted run can be resumed.
 */
object RowGroupCapture {
  private val QueryFile = "^query(\\d+)\\.sql$".r
  private val ListenerTimeoutMinutes = 10L

  private def appendLine(file: File, header: String, line: String): Unit = {
    val writeHeader = !file.exists() || file.length() == 0
    Using.resource(new BufferedWriter(new FileWriter(file, true))) { bw =>
      if (writeHeader) { bw.write(header); bw.newLine() }
      bw.write(line)
      bw.newLine()
    }
  }

  private def csvField(s: String): String = "\"" + s.replace("\"", "\"\"").replace("\n", " ") + "\""

  def main(args: Array[String]): Unit = {
    if (args.length < 3) {
      println("Usage: RowGroupCapture <parquetDir> <queryDir> <outDir> [first-last]")
      sys.exit(1)
    }
    val Array(dataDir, queryDir, outDirPath) = args.take(3)
    val (first, last) = if (args.length > 3) {
      val Array(a, b) = args(3).split("-").map(_.toInt)
      (a, b)
    } else (1, 99)

    val outDir = new File(outDirPath)
    val rgDir = new File(outDir, "rg")
    rgDir.mkdirs()
    val queriesCsv = new File(outDir, "queries.csv")
    val queriesHeader = "query,stmt,status,runtime_ms,rows_returned,exec_ids,rg_entries,error"

    val queries = new File(queryDir).listFiles().toSeq
      .flatMap(f => f.getName match {
        case QueryFile(n) if n.toInt >= first && n.toInt <= last => Some(n.toInt -> f)
        case _ => None
      })
      .sortBy(_._1)

    val spark = SparkSession.builder()
      .appName("RowGroupCapture")
      // Speculative duplicate tasks would add their row groups to the accumulator twice.
      .config("spark.speculation", "false")
      // Row-group capture is only instrumented on the vectorized path, and row-group
      // skipping depends on filter pushdown. Both are Spark defaults; pinned so a stray
      // spark-defaults.conf cannot silently change what is measured.
      .config("spark.sql.parquet.enableVectorizedReader", "true")
      .config("spark.sql.parquet.filterPushdown", "true")
      // Same as the benchmark listener: no reuse of exchanges or subqueries.
      .config("spark.sql.execution.reuseExchange", "false")
      .config("spark.sql.execution.reuseSubquery", "false")
      .getOrCreate()
    require(spark.conf.get("spark.speculation") == "false", "spark.speculation must be false")

    Using.resource(new BufferedWriter(new FileWriter(new File(outDir, "spark_conf.txt")))) { bw =>
      spark.sparkContext.getConf.getAll.sorted.foreach { case (k, v) => bw.write(s"$k=$v\n") }
      bw.write(s"spark.version=${spark.version}\n")
    }

    loadData(spark, dataDir)

    for ((n, file) <- queries) {
      val done = new File(rgDir, s"$n.done")
      if (done.exists()) {
        println(s"Skipping query $n (already captured)")
      } else {
        val rgFile = new File(rgDir, s"$n.csv")
        rgFile.delete() // drop partial output from an interrupted attempt
        val text = Using.resource(scala.io.Source.fromFile(file))(_.mkString)
        val statements = text.split(";").map(_.trim)
          .filter(s => s.linesIterator.exists(l => l.trim.nonEmpty && !l.trim.startsWith("--")))

        var allOk = true
        for ((stmt, i) <- statements.zipWithIndex) {
          spark.catalog.clearCache()
          val start = System.currentTimeMillis()
          val (status, rows, execIds, entries, error) = runStatement(spark, stmt, n, i, rgFile)
          val runtime = System.currentTimeMillis() - start
          if (status != "ok") allOk = false
          appendLine(queriesCsv, queriesHeader,
            Seq(n, i, status, runtime, rows, execIds.mkString(";"), entries, csvField(error)).mkString(","))
          println(s"query $n stmt $i: $status in ${runtime} ms, $entries row-group entries")
        }
        if (allOk) done.createNewFile()
      }
    }
    spark.stop()
  }

  /** Runs one statement and appends its row groups to rgFile. */
  private def runStatement(spark: SparkSession, stmt: String, query: Int, stmtIdx: Int,
                           rgFile: File): (String, Long, Seq[String], Int, String) = {
    var df: org.apache.spark.sql.DataFrame = null
    try {
      df = spark.sql(stmt)
    } catch {
      case e: Exception => return ("parse_error", -1, Nil, 0, e.getMessage)
    }
    val latch = new CountDownLatch(1)
    val collector = new CaptureListener(df.queryExecution.id, latch)
    val before = registryKeys()
    spark.listenerManager.register(collector)
    var newIds: Seq[String] = Nil
    try {
      val rows = try {
        df.collect().length.toLong
      } catch {
        case e: Exception =>
          // onFailure may never fire if the plan failed before execution started
          latch.await(1, TimeUnit.MINUTES)
          return ("failed", -1, Nil, 0, e.getMessage)
      }
      if (!latch.await(ListenerTimeoutMinutes, TimeUnit.MINUTES)) {
        return ("listener_timeout", rows, Nil, 0, "listener did not fire")
      }
      if (collector.failed) {
        return ("failed", rows, Nil, 0, "listener reported failure")
      }
      // All jobs of the statement have finished once collect() returns and the listener has
      // fired, so the accumulators hold their final merged values.
      newIds = registryKeys().filterNot(before.contains)
      val rowGroups = newIds.flatMap { id =>
        RowGroupMetricsRegistry.get(id).toSeq
          .flatMap(_.value.toSeq.flatMap { case (path, rgs) => rgs.map(path -> _) })
      }
      val lines = rowGroups.map { case (path, (ord, off, cnt)) =>
        s"$stmtIdx,${csvField(path)},$ord,$off,$cnt"
      }
      lines.foreach(l => appendLine(rgFile, "stmt,file,ordinal,row_index_offset,row_count", l))
      // A statement that reads no row groups still leaves the file behind, so the
      // converter can tell "read nothing" apart from "never captured".
      if (!rgFile.exists()) rgFile.createNewFile()
      ("ok", rows, newIds, lines.size, "")
    } finally {
      spark.listenerManager.unregister(collector)
      (if (newIds.nonEmpty) newIds else registryKeys().filterNot(before.contains))
        .foreach(RowGroupMetricsRegistry.remove)
    }
  }

  private def registryKeys(): Seq[String] = {
    val keys = RowGroupMetricsRegistry.keys
    keys.synchronized { Seq(keys.toArray(Array.empty[String]): _*) }
  }

  /** Registers each <table>.parquet file in a flat directory as a temp view named <table>. */
  def loadData(spark: SparkSession, path: String): Unit = {
    val root = new Path(path)
    val fs = root.getFileSystem(spark.sparkContext.hadoopConfiguration)
    val files = fs.listStatus(root)
      .filter(st => st.isFile && st.getPath.getName.endsWith(".parquet"))
      .map(_.getPath)
      .sortBy(_.toString)
    require(files.nonEmpty, s"no .parquet files in $path")
    files.foreach { p =>
      spark.read.parquet(p.toString).createOrReplaceTempView(p.getName.stripSuffix(".parquet"))
    }
    println(s"Registered ${files.length} tables from $path")
  }

  /** Signals when the target QueryExecution has finished. */
  class CaptureListener(targetId: Long, latch: CountDownLatch) extends QueryExecutionListener {
    @volatile var failed = false

    override def onSuccess(funcName: String, qe: QueryExecution, durationNs: Long): Unit = {
      if (qe.id == targetId) latch.countDown()
    }

    override def onFailure(funcName: String, qe: QueryExecution, exception: Exception): Unit = {
      if (qe.id == targetId) {
        failed = true
        latch.countDown()
      }
    }
  }
}
