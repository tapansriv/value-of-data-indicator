"""Event-log bytes per query (attributing each line to the latest SQLExecutionStart's query)."""
import sys, csv, re
f, qcsv = sys.argv[1], sys.argv[2]
ex2q = {}
for r in csv.DictReader(open(qcsv)):
    for e in r["exec_ids"].split(";"):
        if e: ex2q[int(e)] = int(r["query"])
size = {}; cur = None; tot = 0
rx = re.compile(rb'"Event":"org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionStart","executionId":(\d+)')
with open(f, "rb") as fp:
    for line in fp:
        m = rx.search(line[:200])
        if m: cur = ex2q.get(int(m.group(1)), cur)
        size[cur] = size.get(cur, 0) + len(line); tot += len(line)
qs = sorted(k for k in size if k is not None)
cum = 0; cumd = {}
for q in qs: cum += size[q]; cumd[q] = cum
print("total", tot, "unattributed", size.get(None, 0))
for k in (22, 50, 99, 131, 163):
    print(f"cum through q{k}:", max((c for q, c in cumd.items() if q <= k), default=0))
print("top 10 (bytes, q):", sorted(((s, q) for q, s in size.items() if q is not None), reverse=True)[:10])
