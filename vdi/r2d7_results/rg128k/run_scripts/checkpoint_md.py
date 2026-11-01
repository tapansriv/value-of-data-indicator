"""Write CHECKPOINT_SF<N>.md (REVISION_R2D7_RG128K.md §7) from pruning.json, acceptance json, monitor log."""
import json, sys, subprocess
sf, R, rgtable = sys.argv[1], sys.argv[2], sys.argv[3]
P = json.load(open(f"{R}/sf{sf}/pruning.json")); Q = P["queries"]
A = json.load(open(f"{R}/sf{sf}/rg_selective_acceptance.json"))
L = [f"# Checkpoint SF{sf} — rg128k rerun (record, not a gate)\n",
     "Written after the SF%s capture. Capture dir `sf%s/capture`; per-query JSON `sf%s/pruning.json`; "
     "authored-query acceptance `sf%s/rg_selective_acceptance.json`.\n" % (sf, sf, sf, sf),
     "## 1. Row groups per table, old (128 MiB) vs new (128,000 rows)\n", open(rgtable).read(),
     "Every non-final row group has exactly 128,000 rows (verify.py assertion with RG_ROWS=128000; "
     "the last row group of each file holds the remainder).\n",
     "## 2. Authored queries 132–163\n",
     "| q | tmpl | base | target | added predicate | RGs read / total | frac | base reads | rows returned | accepted |",
     "|---|---|---|---|---|---:|---:|---:|---:|---|"]
for r in A:
    L.append(f"| {r['query']} | {r['template']}{r['level']} | q{r['base']} | {r['table']} | `{r['predicate']}` | "
             f"{r['rgs_read']}/{r['total_rgs']} | {100*r['frac_read']:.2f}% | {r['base_rgs_read']} | "
             f"{r['rows_returned']} | {'yes' if r['accepted'] else 'NO'} |")
L += ["", "### Queries 100–131 (the pre-existing extra queries)\n",
      "| q | rows | tables with RGs skipped (read/total) | big tables read |", "|---|---:|---|---|"]
for q in range(100, 132):
    v = Q.get(str(q))
    if not v:
        L.append(f"| {q} | – | not captured | |"); continue
    pr = ", ".join(f"{t} {v['new'][t][0]}/{v['new'][t][1]}" for t in v["new_pruned_tables"]) or "none"
    big = ", ".join(f"{t} {n}/{tot}" for t, (n, tot) in v["new"].items() if tot > 1)
    L.append(f"| {q} | {v['rows_returned']} | {pr} | {big} |")
L += ["", "## 3. Queries 1–99 at 128,000-row row groups\n"]
from collections import defaultdict
agg = defaultdict(lambda: [0, 0.0, 0, 0, 0.0, 0])
for q, v in Q.items():
    if int(q) > 99: continue
    for t, (n, tot) in v["new"].items():
        a = agg[t]; a[0] += 1; a[1] += n / tot; a[2] += n < tot
        if v["old"] and t in v["old"]:
            o, ot = v["old"][t]; a[3] += 1; a[4] += o / ot; a[5] += o < ot
n99 = sum(1 for q in Q if int(q) <= 99)
pr_new = sorted(int(q) for q, v in Q.items() if int(q) <= 99 and v["new_pruned_tables"])
L.append(f"{n99} of queries 1–99 captured cleanly. Queries 1–99 that skip any row group of any table: "
         f"{pr_new or 'none'}.\n")
for q in pr_new:
    v = Q[str(q)]
    L.append(f"- q{q}: new " + ", ".join(f"{t} {v['new'][t][0]}/{v['new'][t][1]}" for t in v["new_pruned_tables"])
             + "; old " + (", ".join(f"{t} {x[0]}/{x[1]}" for t, x in (v["old"] or {}).items() if x[0] < x[1]) or "none"))
L += ["", "| table | queries reading it (new) | mean RGs read/total new | queries pruning new | queries reading it (old) | mean read/total old | queries pruning old |",
      "|---|---:|---:|---:|---:|---:|---:|"]
for t, a in sorted(agg.items()):
    L.append(f"| {t} | {a[0]} | {a[1]/a[0]:.4f} | {a[2]} | {a[3]} | {a[4]/a[3] if a[3] else float('nan'):.4f} | {a[5]} |")
open(f"{R}/CHECKPOINT_SF{sf}.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
