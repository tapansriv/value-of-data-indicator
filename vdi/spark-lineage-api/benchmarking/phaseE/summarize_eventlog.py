"""Summarize Spark event logs per query: CPU vs run time, spill, shuffle, input, driver heap.

    python3 summarize_eventlog.py <eventlog file or dir> [...]

Point it at the eventlog/ directories that 40_fetch.sh --eventlogs brings down
(benchmarking/data/ec2/<run-id>/rep<k>/<variant>/eventlog/). Plain JSON-lines event logs
(spark.eventLog.compress is left off); no third-party packages.

Per query (one SQL execution per query: the listener's `show()`), it reports:
  - cpu/run   sum(Executor CPU Time) / sum(Executor Run Time) over the query's tasks.
              Falls toward 0 as tasks wait on I/O. REVISION_SCALEUP.md §4.3: compare it
              across node counts; a declining ratio means the cluster is becoming I/O-bound.
  - input     bytes read from storage (S3)
  - shuffle   shuffle bytes written
  - spill     memory and disk bytes spilled (disk spill lands on the gp3 root volume)
Per application: executors seen (must equal the worker count), executors removed (must
be 0), and the driver's peak JVM heap (REVISION_SCALEUP.md §1.1).
"""
import json
import os
import sys
from collections import defaultdict

SQL_START = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionStart"
SQL_END = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionEnd"


def files(args):
    for a in args:
        if os.path.isdir(a):
            for root, _, names in os.walk(a):
                for n in sorted(names):
                    if not n.endswith((".crc", ".inprogress")) and not n.startswith("."):
                        yield os.path.join(root, n)
        else:
            yield a


def gb(x):
    return f"{x / 1e9:8.2f}"


def summarize(path):
    sql = {}                      # execution id -> {desc, start, end}
    job_exec = {}                 # job id -> execution id
    stage_exec = {}               # stage id -> execution id
    agg = defaultdict(lambda: defaultdict(float))
    executors_added, executors_removed = set(), set()
    driver_heap_peak = 0
    app = os.path.basename(path)

    with open(path) as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ev = e.get("Event")
            if ev == SQL_START:
                sql[e["executionId"]] = {"desc": e.get("description", ""), "start": e.get("time", 0), "end": None}
            elif ev == SQL_END:
                if e["executionId"] in sql:
                    sql[e["executionId"]]["end"] = e.get("time")
            elif ev == "SparkListenerApplicationStart":
                app = e.get("App ID", app)
            elif ev == "SparkListenerJobStart":
                xid = (e.get("Properties") or {}).get("spark.sql.execution.id")
                if xid is not None:
                    job_exec[e["Job ID"]] = int(xid)
                    for sid in e.get("Stage IDs", []):
                        stage_exec[sid] = int(xid)
            elif ev == "SparkListenerTaskEnd":
                xid = stage_exec.get(e.get("Stage ID"))
                m = e.get("Task Metrics") or {}
                if xid is None or not m:
                    continue
                a = agg[xid]
                a["tasks"] += 1
                a["run_ms"] += m.get("Executor Run Time", 0)
                a["cpu_ns"] += m.get("Executor CPU Time", 0)
                a["mem_spill"] += m.get("Memory Bytes Spilled", 0)
                a["disk_spill"] += m.get("Disk Bytes Spilled", 0)
                a["input"] += (m.get("Input Metrics") or {}).get("Bytes Read", 0)
                a["shuffle_w"] += (m.get("Shuffle Write Metrics") or {}).get("Shuffle Bytes Written", 0)
                if (e.get("Task Info") or {}).get("Speculative"):
                    a["speculative"] += 1
                if (e.get("Task End Reason") or {}).get("Reason", "Success") != "Success":
                    a["failed_tasks"] += 1
            elif ev == "SparkListenerExecutorAdded":
                executors_added.add(e.get("Executor ID"))
            elif ev == "SparkListenerExecutorRemoved":
                executors_removed.add(e.get("Executor ID"))
            elif ev == "SparkListenerStageExecutorMetrics":
                if e.get("Executor ID") == "driver":
                    driver_heap_peak = max(driver_heap_peak, (e.get("Executor Metrics") or {}).get("JVMHeapMemory", 0))

    queries = [(xid, s) for xid, s in sorted(sql.items(), key=lambda kv: kv[1]["start"])
               if s["desc"].startswith("show at")]
    print(f"== {app}  executors added={len(executors_added)} removed={len(executors_removed)}"
          f"  driver peak heap={driver_heap_peak / 2**30:.2f} GiB  queries={len(queries)}")
    print(f"   {'#':>2} {'wall s':>8} {'tasks':>7} {'cpu/run':>7} {'input GB':>9} {'shuf GB':>8} "
          f"{'memspill':>8} {'diskspill':>9} {'spec':>4} {'fail':>4}")
    for i, (xid, s) in enumerate(queries, 1):
        a = agg[xid]
        wall = (s["end"] - s["start"]) / 1000 if s["end"] else float("nan")
        ratio = (a["cpu_ns"] / 1e6) / a["run_ms"] if a["run_ms"] else float("nan")
        print(f"   {i:>2} {wall:8.1f} {int(a['tasks']):>7} {ratio:7.3f} {gb(a['input']):>9} {gb(a['shuffle_w']):>8} "
              f"{gb(a['mem_spill']):>8} {gb(a['disk_spill']):>9} {int(a['speculative']):>4} {int(a['failed_tasks']):>4}")
    if executors_removed:
        print("   WARNING: executors were removed during the run (lost worker or executor)")
    if any(agg[x]["speculative"] for x, _ in queries):
        print("   WARNING: speculative tasks present; row-group counts may be double-counted")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in files(sys.argv[1:]):
        summarize(p)


if __name__ == "__main__":
    main()
