import java.io.{BufferedWriter, File, FileWriter}
import java.net.InetAddress
import java.time.Instant
import java.util.concurrent.{CountDownLatch, TimeUnit}
import java.util.concurrent.atomic.AtomicLong

import scala.io.Source
import scala.util.Using

import org.apache.spark.scheduler.{SparkListener, SparkListenerTaskEnd}
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.{FileSourceScanExec, SparkPlan}
import org.apache.spark.sql.execution.adaptive.AdaptiveSparkPlanHelper
import org.apache.spark.sql.execution.datasources.v2.BatchScanExec
import org.json4s._
import org.json4s.jackson.JsonMethods._

/** Runs TPC-DS queries against chosen Iceberg layouts and records bytes read per query.
  *
  * usage: SortingRunner <plan.json>
  *
  * plan.json (written by make_runs.py):
  *   catalog, warehouse, query_dir, usage_path, out, explain (bool),
  *   runs: [{run_id, bindings: {table: namespace}, queries: ["01", ...]}]
  * Tables not named in bindings resolve to namespace "base". Each query is bound through
  * temp views (CREATE TEMP VIEW t AS SELECT * FROM catalog.ns.t), which Spark inlines, so
  * pushdown and dynamic partition pruning see the Iceberg table directly.
  *
  * The column/table listener (LineageAPI.UsageCollector) is registered for every query.
  * Queries execute with collect(), not show(): show() adds LIMIT 21, which can stop
  * scans early and understate bytes read.
  *
  * Output: one JSON line per (run_id, query) appended to `out`; rerunning the same plan
  * skips pairs already recorded with status "ok". Three bytes measures are recorded so the
  * pilot can choose between them: Spark task inputMetrics.bytesRead, the JVM's
  * /proc/self/io rchar delta (local mode: executors share the driver JVM), and every
  * scan node's SQL metrics (Iceberg reports file counts and sizes there).
  */
object SortingRunner extends AdaptiveSparkPlanHelper {
  implicit val formats: Formats = DefaultFormats

  val LISTENER_TIMEOUT_MIN = 30L

  /** Input bytes over all tasks that end while one query is being measured. Queries run
    * one at a time, and the listener's usage-log write reads no input. */
  class InputBytes extends SparkListener {
    val bytes = new AtomicLong(0)
    val records = new AtomicLong(0)
    val tasks = new AtomicLong(0)
    override def onTaskEnd(e: SparkListenerTaskEnd): Unit = {
      val m = e.taskMetrics
      if (m != null) {
        bytes.addAndGet(m.inputMetrics.bytesRead)
        records.addAndGet(m.inputMetrics.recordsRead)
      }
      tasks.incrementAndGet()
    }
    def reset(): Unit = { bytes.set(0); records.set(0); tasks.set(0) }
  }

  def procIo(): Map[String, Long] = {
    val f = new File("/proc/self/io")
    if (!f.exists) Map.empty
    else Using(Source.fromFile(f))(_.getLines().toList).get.flatMap { l =>
      l.split(":\\s*") match {
        case Array(k, v) => Some(k -> v.trim.toLong)
        case _ => None
      }
    }.toMap
  }

  def str(j: JValue, k: String): String = (j \ k).extract[String]

  def appendLine(path: String, j: JValue): Unit = {
    Using(new BufferedWriter(new FileWriter(path, true))) { w =>
      w.write(compact(render(j))); w.newLine()
    }.get
  }

  def done(path: String): Set[(String, String)] = {
    val f = new File(path)
    if (!f.exists) Set.empty
    else Using(Source.fromFile(f))(_.getLines().toList).get.flatMap { l =>
      val j = parse(l)
      if ((j \ "status").extractOpt[String].contains("ok"))
        Some(str(j, "run_id") -> str(j, "query")) else None
    }.toSet
  }

  def metricsJson(p: SparkPlan): JValue =
    JObject(p.metrics.toList.sortBy(_._1).map { case (k, m) => k -> JInt(m.value) })

  def scansJson(plan: SparkPlan): List[JValue] = collectWithSubqueries(plan) {
    case s: BatchScanExec =>
      JObject(
        "node" -> JString("BatchScan"),
        "table" -> JString(s.table.name()),
        "runtime_filters" -> JInt(s.runtimeFilters.size),
        "description" -> JString(s.scan.description().take(800)),
        "metrics" -> metricsJson(s))
    case f: FileSourceScanExec =>
      JObject(
        "node" -> JString("FileSourceScan"),
        "table" -> JString(f.tableIdentifier.map(_.table)
          .getOrElse(f.relation.location.rootPaths.headOption.map(_.getName).getOrElse("?"))),
        "runtime_filters" -> JInt(f.partitionFilters.count(_.toString.contains("dynamicpruning"))),
        "description" -> JString(""),
        "metrics" -> metricsJson(f))
  }.toList

  def main(args: Array[String]): Unit = {
    val planFile = args(0)
    val plan = parse(new File(planFile))
    val catalog = str(plan, "catalog")
    val queryDir = str(plan, "query_dir")
    val usagePath = str(plan, "usage_path")
    val out = str(plan, "out")
    val explainOnly = (plan \ "explain").extractOpt[Boolean].getOrElse(false)
    val runs = (plan \ "runs").extract[List[JValue]]

    // Catalog and every other setting come from spark-submit (run_phase.sh), so they are
    // visible in one place and recorded below.
    val spark = SparkSession.builder().appName("SortingRunner").getOrCreate()
    val sc = spark.sparkContext
    val input = new InputBytes
    sc.addSparkListener(input)

    new File(out).getAbsoluteFile.getParentFile.mkdirs()
    val icebergVersion = scala.util.Try(Class.forName("org.apache.iceberg.IcebergBuild")
      .getMethod("fullVersion").invoke(null).toString).getOrElse("?")
    appendLine(out + ".meta.jsonl", JObject(
      "ts" -> JString(Instant.now().toString),
      "plan" -> JString(new File(planFile).getAbsolutePath),
      "host" -> JString(InetAddress.getLocalHost.getHostName),
      "spark_version" -> JString(spark.version),
      "iceberg_version" -> JString(icebergVersion),
      "explain_only" -> JBool(explainOnly),
      "conf" -> JObject(spark.conf.getAll.toList.sortBy(_._1).map { case (k, v) => k -> JString(v) })))

    val tables = spark.sql(s"SHOW TABLES IN $catalog.base").collect().map(_.getString(1)).sorted
    // 24 for TPC-DS (plans written before base_tables existed); make_runs.py records the count.
    val baseTables = (plan \ "base_tables").extractOpt[Int].getOrElse(24)
    require(tables.length == baseTables,
      s"expected $baseTables tables in $catalog.base, found ${tables.length}")
    val already = done(out)

    def quiesce(): Long = {
      val start = System.currentTimeMillis()
      var last = -1L
      var stable = 0
      while (stable < 3 && System.currentTimeMillis() - start < 120000) {
        Thread.sleep(200)
        val now = input.tasks.get()
        if (sc.statusTracker.getActiveJobIds().isEmpty && now == last) stable += 1 else stable = 0
        last = now
      }
      System.currentTimeMillis() - start
    }

    for (run <- runs) {
      val runId = str(run, "run_id")
      val bindings = (run \ "bindings").extract[Map[String, String]]
      val queries = (run \ "queries").extract[List[String]].filterNot(q => already((runId, q)))
      if (queries.nonEmpty) {
        for ((t, ns) <- bindings)
          require(spark.catalog.tableExists(s"$catalog.$ns.$t"), s"$runId: missing $catalog.$ns.$t")
        for (t <- tables) {
          val ns = bindings.getOrElse(t, "base")
          spark.sql(s"CREATE OR REPLACE TEMP VIEW $t AS SELECT * FROM $catalog.$ns.$t")
        }
        println(s"== $runId: ${queries.size} queries, bindings $bindings")
      }

      for (q <- queries) {
        val sql = Using(Source.fromFile(s"$queryDir/$q.sql"))(_.mkString).get
        spark.catalog.clearCache()
        val base: List[JField] = List(
          "run_id" -> JString(runId), "query" -> JString(q),
          "bindings" -> JObject(bindings.toList.sorted.map { case (k, v) => k -> JString(v) }),
          "ts" -> JString(Instant.now().toString))

        val record: JValue = if (explainOnly) {
          try {
            val exec = spark.sql(sql).queryExecution.executedPlan
            JObject(base ++ List(
              "status" -> JString("ok"),
              "dpp_in_plan" -> JBool(exec.toString.toLowerCase.contains("dynamicpruning")),
              "scans" -> JArray(scansJson(exec))))
          } catch {
            case e: Throwable => JObject(base ++ List("status" -> JString("error"),
              "error" -> JString(String.valueOf(e.getMessage).take(2000))))
          }
        } else {
          val latch = new CountDownLatch(1)
          val collector = new LineageAPI.UsageCollector(spark, usagePath, s"$runId:$q", latch)
          spark.listenerManager.register(collector)
          quiesce()
          input.reset()
          val io0 = procIo()
          val t0 = System.nanoTime()
          try {
            val df = spark.sql(sql)
            val rows = df.collect().length
            val runtimeMs = (System.nanoTime() - t0) / 1e6
            val listenerOk = latch.await(LISTENER_TIMEOUT_MIN, TimeUnit.MINUTES)
            val quiesceMs = quiesce()
            val io1 = procIo()
            val exec = df.queryExecution.executedPlan
            val scans = scansJson(exec)
            JObject(base ++ List(
              "status" -> JString("ok"),
              "rows" -> JInt(rows),
              "runtime_ms" -> JDouble(runtimeMs),
              "listener_ok" -> JBool(listenerOk),
              "quiesce_ms" -> JInt(quiesceMs),
              "task_bytes_read" -> JInt(input.bytes.get()),
              "task_records_read" -> JInt(input.records.get()),
              "tasks" -> JInt(input.tasks.get()),
              "proc_rchar" -> JInt(io1.getOrElse("rchar", 0L) - io0.getOrElse("rchar", 0L)),
              "proc_read_bytes" -> JInt(io1.getOrElse("read_bytes", 0L) - io0.getOrElse("read_bytes", 0L)),
              "dpp_in_plan" -> JBool(exec.toString.toLowerCase.contains("dynamicpruning") ||
                scans.exists(s => (s \ "runtime_filters").extract[Int] > 0)),
              "scans" -> JArray(scans)))
          } catch {
            case e: Throwable => JObject(base ++ List("status" -> JString("error"),
              "error" -> JString(String.valueOf(e.getMessage).take(2000))))
          } finally {
            spark.listenerManager.unregister(collector)
          }
        }
        appendLine(out, record)
        println(s"   $runId $q ${(record \ "status").extract[String]}")
      }
    }
    spark.stop()
  }
}
