package vdi.placement

import org.apache.spark.scheduler.{SparkListener, SparkListenerJobStart, SparkListenerStageSubmitted, SparkListenerTaskEnd}
import org.apache.spark.sql.{Row, SparkSession}
import org.apache.spark.sql.catalyst.expressions.ExprId
import org.apache.spark.sql.catalyst.plans.logical.LogicalPlan
import org.apache.spark.sql.execution.QueryExecution
import org.apache.spark.sql.execution.datasources.{HadoopFsRelation, LogicalRelation}
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.types.{DoubleType, IntegerType, StringType, StructField, StructType, TimestampType}
import org.apache.spark.sql.util.QueryExecutionListener

import java.sql.Timestamp
import java.time.Instant
import java.util.concurrent.{ConcurrentHashMap, CountDownLatch, TimeUnit}
import java.util.concurrent.atomic.AtomicLong

/**
 * VDI listener for the data placement experiment (R2D14, R3W1, R3D1), implementing §5.2:
 * when a query completes it determines which tables and columns were accessed, looks up
 * the task's value in the Task Value table, computes each column's data value (Equal
 * dividing: TaskValue / #columns), and appends rows to the Data Value table.
 *
 * Registered through `spark.sql.queryExecutionListeners`. The harness tags each query in
 * the session conf (task id = TPC-DS query template, plus a unique execution id it waits
 * on via `awaitExecution`). With `spark.vdi.placement.writeDataValue=false` (static mode)
 * the listener still observes every query but appends nothing.
 *
 * Column extraction is the same rule as LineageAPI.UsageCollector: columns per base table,
 * resolved through the optimized plan's scan relations by exprId, including subqueries.
 * `columnsForSql` applies it before execution so the cache fetches exactly those columns.
 */
class PlacementUsageListener extends QueryExecutionListener {
  import PlacementUsageListener._

  override def onSuccess(funcName: String, qe: QueryExecution, durationNs: Long): Unit =
    handle(funcName, qe, None)

  override def onFailure(funcName: String, qe: QueryExecution, exception: Exception): Unit =
    handle(funcName, qe, Some(exception))

  private def handle(funcName: String, qe: QueryExecution, failure: Option[Exception]): Unit = {
    val conf = qe.sparkSession.conf
    val execId = conf.getOption(ExecIdKey).orNull
    // Only the tagged query's own action counts. The listener's own Spark jobs (reading Task
    // Value, appending Data Value) come back through here under other action names.
    if (execId == null || funcName != conf.get(ActionKey, DefaultAction)) return
    if (completed.containsKey(execId)) return
    val result = try {
      failure match {
        case Some(e) => s"error:query failed: ${e.getMessage}"
        case None =>
          val write = conf.get(WriteKey, "true").toBoolean
          val n = if (write) {
            logDataValue(qe.sparkSession, conf.get(TaskIdKey), qe.optimizedPlan,
              conf.get(TaskValueTableKey, DefaultTaskValueTable),
              conf.get(DataValueTableKey, DefaultDataValueTable))
          } else 0
          s"ok:$n"
      }
    } catch {
      case e: Throwable => s"error:data value write failed: ${e.getMessage}"
    }
    completed.put(execId, result)
    latchFor(execId).countDown()
  }
}

object PlacementUsageListener {
  val TaskIdKey = "spark.vdi.placement.taskId"
  val ExecIdKey = "spark.vdi.placement.execId"
  val WriteKey = "spark.vdi.placement.writeDataValue"
  val TaskValueTableKey = "spark.vdi.placement.taskValueTable"
  val DataValueTableKey = "spark.vdi.placement.dataValueTable"
  val ActionKey = "spark.vdi.placement.action"
  // PySpark's DataFrame.collect() reaches the listener as this action.
  val DefaultAction = "collectToPython"
  val DefaultTaskValueTable = "vdi.placement.task_value"
  val DefaultDataValueTable = "vdi.placement.data_value"

  /** Data Value table schema (paper §3); RowGroupID is NULL at column granularity. */
  val DataValueSchema: StructType = StructType(Seq(
    StructField("task_id", StringType, nullable = false),
    StructField("table_name", StringType, nullable = false),
    StructField("column_name", StringType, nullable = true),
    StructField("row_group_id", IntegerType, nullable = true),
    StructField("ts", TimestampType, nullable = false),
    StructField("value", DoubleType, nullable = false)))

  private val completed = new ConcurrentHashMap[String, String]()
  private val latches = new ConcurrentHashMap[String, CountDownLatch]()

  private def latchFor(execId: String): CountDownLatch =
    latches.computeIfAbsent(execId, _ => new CountDownLatch(1))

  /** Block until the listener has handled `execId`: "ok:<rows written>", "error:<msg>" or "timeout". */
  def awaitExecution(execId: String, timeoutMs: Long): String = {
    if (!latchFor(execId).await(timeoutMs, TimeUnit.MILLISECONDS)) return "timeout"
    latches.remove(execId)
    completed.remove(execId)
  }

  /** Columns per base table for a plan; same rule as LineageAPI.UsageCollector. */
  def columnsByTable(plan: LogicalPlan): Map[String, Set[String]] = {
    val relations = plan.collectWithSubqueries { case r: LogicalRelation => r }
    val referenced: Set[ExprId] =
      plan.collectWithSubqueries { case p => p.references.toSeq.map(_.exprId) }.flatten.toSet
    relations
      .flatMap { r =>
        val table = baseTableName(r)
        r.output.filter(a => referenced.contains(a.exprId)).map(a => table -> a.name)
      }
      .groupBy(_._1)
      .map { case (t, cols) => t -> cols.map(_._2).toSet }
  }

  /** Columns a SQL query will read, from its optimized plan, without executing it. JSON object. */
  def columnsForSql(spark: SparkSession, sql: String): String =
    toJson(columnsByTable(spark.sql(sql).queryExecution.optimizedPlan))

  // Table name of a scan: the file or directory basename (the harness registers each view
  // under it: <dir>/<table>.parquet or <cache>/tables/<table>), or the catalog name.
  private def baseTableName(r: LogicalRelation): String = r.relation match {
    case h: HadoopFsRelation if h.location.rootPaths.nonEmpty =>
      h.location.rootPaths.head.getName.stripSuffix(".parquet")
    case _ => r.catalogTable.map(_.identifier.table).getOrElse("unknown")
  }

  private def logDataValue(spark: SparkSession, taskId: String, plan: LogicalPlan,
                           taskValueTable: String, dataValueTable: String): Int = {
    val cols = columnsByTable(plan)
    val n = cols.values.map(_.size).sum
    if (n == 0) return 0
    val taskValue = spark.table(taskValueTable).where(col("task_id") === taskId)
      .select("task_value").collect().headOption.map(_.getDouble(0)).getOrElse(0.0)
    val ts = Timestamp.from(Instant.now())
    val share = taskValue / n
    val rows = for {
      (table, cs) <- cols.toSeq.sortBy(_._1)
      c <- cs.toSeq.sorted
    } yield Row(taskId, table, c, null, ts, share)
    spark.createDataFrame(spark.sparkContext.parallelize(rows, 1), DataValueSchema)
      .writeTo(dataValueTable).append()
    rows.size
  }

  private def toJson(m: Map[String, Set[String]]): String = {
    def q(s: String) = "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
    m.toSeq.sortBy(_._1)
      .map { case (t, cs) => q(t) + ":[" + cs.toSeq.sorted.map(q).mkString(",") + "]" }
      .mkString("{", ",", "}")
  }
}

/**
 * Bytes Spark read per query (task input metrics), for the "bytes scanned" metric.
 * Registered through `spark.extraListeners`. The harness runs each query under its own job
 * group; tasks are attributed to the job group of their stage. Shares the listener bus
 * queue with the query listener, so a query's task-end events are counted before its
 * completion is reported by PlacementUsageListener.awaitExecution.
 */
class PlacementBytesListener extends SparkListener {
  import PlacementBytesListener._

  override def onJobStart(e: SparkListenerJobStart): Unit = {
    val group = Option(e.properties).flatMap(p => Option(p.getProperty("spark.jobGroup.id")))
    group.foreach(g => e.stageIds.foreach(s => stageGroup.put(s, g)))
  }

  override def onStageSubmitted(e: SparkListenerStageSubmitted): Unit = {
    val group = Option(e.properties).flatMap(p => Option(p.getProperty("spark.jobGroup.id")))
    group.foreach(g => stageGroup.put(e.stageInfo.stageId, g))
  }

  override def onTaskEnd(e: SparkListenerTaskEnd): Unit = {
    val g = stageGroup.get(e.stageId)
    if (g != null && e.taskMetrics != null) {
      bytes.computeIfAbsent(g, _ => new AtomicLong()).addAndGet(e.taskMetrics.inputMetrics.bytesRead)
    }
  }
}

object PlacementBytesListener {
  private val stageGroup = new ConcurrentHashMap[Int, String]()
  private val bytes = new ConcurrentHashMap[String, AtomicLong]()

  /** Input bytes read by tasks of this job group so far; clears the counter. */
  def takeBytesRead(group: String): Long = {
    val v = bytes.remove(group)
    if (v == null) 0L else v.get()
  }
}
