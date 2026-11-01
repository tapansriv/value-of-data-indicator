"""Inputs for the sorting harness (clustering/spark) to run the Redbench IMDb workload (R3D4).

Value assignments (Tapan, 2026-10-08): the paper's five, as for TPC-DS (value_iter "0".."4"):
Constant, and Value N for N in {50, 100, 500, 1000} -- high-value queries N, medium-value
queries N/10, the rest 1 (evaluation.tex). High = every query touching the headline `role`
tier-1 DE (cast_info.role_id); medium = every remaining query touching a `role` tier-2 DE.

Superseded (2026-10-07, never run): r : sqrt(r) : 1 for r in {10, 100, 1000} over all four
selections below. The selections are still reported (tiers in profile.json).

Selections (decided 2026-10-07):
  role  tier 1 cast_info.role_id; tier 2 name.gender, name.name_pcode_nf   HEADLINE
  comp  tier 1 movie_companies.note; tier 2 company_name.country_code,
        movie_companies.company_type_id                                    narrow
  rare  tier 1 person_info.info; tier 2 movie_info_idx.info, aka_name.name narrow / rare
  hot   tier 1 title.production_year; tier 2 keyword.keyword               control: the
        hottest DE, so value aligns with frequency
r = 1 is identical for every selection, so it appears once, as `const`.

Net utility (decided 2026-10-07): each query's contribution is weighted by how many times it
ran in the trace -- sum over queries of executions(q) * value(q) * plain(q) / bytes(q),
normalized to No Sort (sum of executions(q) * value(q)) at the end. Frequency is never
normalized away. The ranking side is consistent with that: a column's value is the sum, over
executions, of the executing query's value divided by the number of columns it references.

Writes harness/: value_cols.json, frequency_cols.json, query_values.csv,
query_executions.json, profile.json. Column keys are qualified `table.column` (IMDb's 108
table-columns share only 38 bare names); clustering/src/rank.py strips the prefix on output.
"""
import csv, json, math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "harness"
SELECTIONS = {
    "role": ("cast_info.role_id (headline)", ["cast_info.role_id"],
             ["name.gender", "name.name_pcode_nf"]),
    "comp": ("movie_companies.note (narrow)", ["movie_companies.note"],
             ["company_name.country_code", "movie_companies.company_type_id"]),
    "rare": ("person_info.info (rare)", ["person_info.info"],
             ["movie_info_idx.info", "aka_name.name"]),
    "hot":  ("title.production_year (control: hottest DE)", ["title.production_year"],
             ["keyword.keyword"]),
}
HEADLINE = "role"
PAPER_HIGH = [50, 100, 500, 1000]    # Value N: high N, medium N/10, low 1


def main():
    OUT.mkdir(exist_ok=True)
    cq = json.load(open(HERE / "imdb_columns_in_queries.json"))
    reg = json.load(open(HERE / "imdb_schema_registry.json"))
    all_cols = sorted(f"{t}.{c}" for t, cs in reg.items() for c in cs)
    qcols = {q.split(".")[0]: sorted(f"{t}.{c}" for t, cs in d.items() for c in cs)
             for q, d in cq.items()}
    ex = Counter(r["query_file"].split(".")[0] for r in csv.DictReader(open(HERE / "stream.csv")))
    queries = sorted(qcols)
    assert set(ex) <= set(queries), "stream references a query with no column set"

    iters, names, per_query = ["0"], {"0": "Constant"}, {"0": {q: 1.0 for q in queries}}
    tiers_report, tiers = {}, {}
    for sel, (label, t1, t2) in SELECTIONS.items():
        T1 = {q for q in queries if set(qcols[q]) & set(t1)}
        T2 = {q for q in queries if q not in T1 and set(qcols[q]) & set(t2)}
        tiers[sel] = (T1, T2)
        e = sum(ex.values())
        tiers_report[sel] = {"tier1_queries": len(T1), "tier2_queries": len(T2),
                             "tier1_exec_pct": round(100 * sum(ex[q] for q in T1) / e, 2),
                             "tier2_exec_pct": round(100 * sum(ex[q] for q in T2) / e, 2)}
    T1, T2 = tiers[HEADLINE]
    for i, n in enumerate(PAPER_HIGH, start=1):
        it = str(i)
        iters.append(it); names[it] = f"Value {n}"
        per_query[it] = {q: float(n) if q in T1 else n / 10 if q in T2 else 1.0 for q in queries}

    value_cols = {}
    for it in iters:
        v = {c: 0.0 for c in all_cols}
        for q in queries:
            if not qcols[q]:
                continue
            share = ex[q] * per_query[it][q] / len(qcols[q])
            for c in qcols[q]:
                v[c] += share
        value_cols[it] = v
    freq = {c: 0 for c in all_cols}
    for q in queries:
        for c in qcols[q]:
            freq[c] += ex[q]

    json.dump(value_cols, open(OUT / "value_cols.json", "w"), indent=1, sort_keys=True)
    json.dump(freq, open(OUT / "frequency_cols.json", "w"), indent=1, sort_keys=True)
    json.dump({q: ex[q] for q in queries}, open(OUT / "query_executions.json", "w"), indent=1)
    with open(OUT / "query_values.csv", "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["query_id"] + iters)
        for q in queries:
            w.writerow([f"{q}.sql"] + [per_query[it][q] for it in iters])

    profile = {
        "note": "Generated by redbench_imdb/make_harness_inputs.py. Paths are relative to the "
                "value-of-data-metric repo root. Read by clustering/src/workload.py when WORKLOAD=imdb.",
        "value_json": "redbench_imdb/harness/value_cols.json",
        "freq_json": "redbench_imdb/harness/frequency_cols.json",
        "tables_json": "redbench_imdb/imdb_schema_registry_qualified.json",
        "row_counts_json": "redbench_imdb/imdb_row_counts.json",
        "columns_in_queries": "redbench_imdb/imdb_columns_in_queries.json",
        "values_csv": "redbench_imdb/harness/query_values.csv",
        "query_executions": "redbench_imdb/harness/query_executions.json",
        "weighting": "executions",
        "queries": queries,
        "query_dir": "redbench_imdb/queries_spark",
        "manifest": "clustering/spark/manifest_imdb.json",
        "value_iters": iters,
        "value_names": names,
        "k_sweep": list(range(1, 15)),
        "expect_eligible": 14,
        "validate": [["0", "value", 2, 2], ["4", "value", 2, 2],
                     ["4", "random", 2, 2], ["0", "frequency", 5, 2]],
        # Value 100 (100 : 10 : 1) equals the superseded role100, so the pilot layout is unchanged.
        "pilot": {"strategy": "value", "value_iter": "2", "table": "cast_info"},
        "high_value_selection": HEADLINE,
        "tiers": tiers_report,
    }
    json.dump(profile, open(OUT / "profile.json", "w"), indent=2)

    # The tier definitions as they go in the paper: which data columns make a query high or
    # medium value, the resulting queries, and the values per assignment.
    label, hi_cols, mid_cols = SELECTIONS[HEADLINE]
    e = sum(ex.values())
    tier_q = {"high": sorted(T1), "medium": sorted(T2), "low": sorted(set(queries) - T1 - T2)}
    json.dump({
        "note": "Value tiers for the Redbench IMDb sorting experiment (paper's method: a query "
                "touching a high-value column is high; else touching a medium-value column is "
                "medium; else low). Generated by redbench_imdb/make_harness_inputs.py.",
        "high_value_columns": hi_cols,
        "medium_value_columns": mid_cols,
        "values": {names[it]: {"high": per_query[it][next(iter(T1))] if T1 else None,
                               "medium": per_query[it][next(iter(T2))] if T2 else None,
                               "low": 1.0} for it in iters},
        "tiers": {t: {"distinct_queries": len(qs),
                      "executions": sum(ex[q] for q in qs),
                      "exec_pct": round(100 * sum(ex[q] for q in qs) / e, 2),
                      "queries": qs} for t, qs in tier_q.items()},
        "total_distinct_queries": len(queries),
        "total_executions": e,
    }, open(OUT / "value_tiers.json", "w"), indent=1)
    print(f"{len(queries)} queries, {sum(ex.values()):,} executions, {len(iters)} value assignments")
    for sel, t in tiers_report.items():
        print(f"  {sel:5s} tier1 {t['tier1_queries']:3d} q / {t['tier1_exec_pct']:5.2f}% exec   "
              f"tier2 {t['tier2_queries']:3d} q / {t['tier2_exec_pct']:5.2f}% exec")


if __name__ == "__main__":
    main()
