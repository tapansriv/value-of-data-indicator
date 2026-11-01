"""Derive IMDb column sets for the Redbench workload, in the formats clustering/ expects.

Outputs (same shapes as the TPC-DS files they mirror):
  imdb_schema_registry.json    {table: [all columns]}        <- clustering/schema/tpcds_schema_registry.json
  imdb_columns_in_queries.json {query.sql: {table: [cols]}}  <- value_generation/tpcds_columns_in_queries.json
  imdb_column_names.csv        flat list of every column     <- value_generation/tpcds_column_names.csv
  imdb_filter_columns.json     {query.sql: {table: [cols]}}  filter-predicate columns only (narrower)

Column extraction uses sqlglot's AST with alias resolution, not regex: every Column node is
resolved through the query's FROM/JOIN aliases to its base table. Unqualified columns are
attributed only when exactly one table in the query owns that name, otherwise reported as
ambiguous.
"""
import csv, json, re, sys
from collections import defaultdict
from pathlib import Path
import sqlglot
from sqlglot import exp

HERE = Path(__file__).resolve().parent
SCHEMA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "/private/tmp/claude-501/-Users-tapansriv-value-of-data/"
    "4a505d28-6811-432e-8482-7d42649a51de/scratchpad/imdb/schema.sql")

# ---- schema registry from the shipped JOB schema ----
txt = SCHEMA.read_text()
registry = {}
for m in re.finditer(r"CREATE TABLE (\w+)\s*\((.*?)\n\);", txt, re.S):
    tbl, body = m.group(1), m.group(2)
    cols = []
    for line in body.split("\n"):
        line = line.strip().rstrip(",")
        if not line:
            continue
        name = line.split()[0]
        if name.upper() in ("PRIMARY", "FOREIGN", "CONSTRAINT", "UNIQUE", "CHECK"):
            continue
        cols.append(name)
    registry[tbl] = sorted(cols)
owner = defaultdict(list)
for t, cols in registry.items():
    for c in cols:
        owner[c].append(t)

FILTER_OPS = (exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE, exp.Like, exp.ILike,
              exp.In, exp.Between, exp.Is)

def column_sets(sql):
    """-> (all_referenced {tbl:set(cols)}, filter_only {tbl:set(cols)}, ambiguous [names])"""
    tree = sqlglot.parse_one(sql, read="duckdb")
    alias = {}
    for tnode in tree.find_all(exp.Table):
        if tnode.name in registry:
            alias[tnode.alias or tnode.name] = tnode.name
    def resolve(col):
        if col.table:
            return alias.get(col.table)
        cands = owner.get(col.name, [])
        in_q = [t for t in cands if t in alias.values()]
        return in_q[0] if len(in_q) == 1 else None
    allref, filt, amb = defaultdict(set), defaultdict(set), []
    for col in tree.find_all(exp.Column):
        t = resolve(col)
        if t is None:
            amb.append(col.sql()); continue
        allref[t].add(col.name)
    for node in tree.find_all(*FILTER_OPS):
        cols = [c for c in node.find_all(exp.Column)]
        lits = list(node.find_all(exp.Literal)) + list(node.find_all(exp.Null))
        # a filter predicate compares a column against literal(s), not another column
        if len(cols) == 1 and lits:
            t = resolve(cols[0])
            if t: filt[t].add(cols[0].name)
    return allref, filt, amb

files = sorted((HERE / "queries").glob("*.sql"))
in_q, filt_q, ambiguous, failed = {}, {}, [], []
for f in files:
    try:
        a, fl, amb = column_sets(f.read_text())
    except Exception as e:
        failed.append((f.name, str(e).split("\n")[0][:100])); continue
    in_q[f.name] = {t: sorted(c) for t, c in sorted(a.items())}
    filt_q[f.name] = {t: sorted(c) for t, c in sorted(fl.items())}
    ambiguous.extend(amb)

json.dump(registry, open(HERE/"imdb_schema_registry.json","w"), indent=4, sort_keys=True)
json.dump(in_q, open(HERE/"imdb_columns_in_queries.json","w"), indent=4, sort_keys=True)
json.dump(filt_q, open(HERE/"imdb_filter_columns.json","w"), indent=4, sort_keys=True)
with open(HERE/"imdb_column_names.csv","w") as fp:
    for t in sorted(registry):
        for c in registry[t]:
            fp.write(c+"\n")

ncols = sum(len(v) for v in registry.values())
print(f"schema: {len(registry)} tables, {ncols} columns")
print(f"queries parsed: {len(in_q)}/{len(files)}  failed: {len(failed)}  unresolved column refs: {len(ambiguous)}")
for n,e in failed[:5]: print("   FAIL", n, e)
tot_all = sum(len(c) for q in in_q.values() for c in q.values())
tot_f  = sum(len(c) for q in filt_q.values() for c in q.values())
print(f"mean columns per query: all-referenced {tot_all/max(len(in_q),1):.1f}, filter-only {tot_f/max(len(filt_q),1):.1f}")
