"""Which workload the sorting harness runs.

  WORKLOAD=tpcds (default)  the published TPC-DS setup; every path and constant below is
                            exactly what the harness hardcoded before this file existed
  WORKLOAD=imdb             the Redbench IMDb workload for R3D4; read from
                            redbench_imdb/harness/profile.json (make_harness_inputs.py)

rank.py, plan_layouts.py, make_runs.py, build_iceberg.py and analyze_sweep.py read their
TPC-DS-specific inputs from `P`; run_phase.sh / env.sh switch the manifest, warehouse and
results directory on the same variable, so a second workload never touches TPC-DS state.
"""
import json
import os
from pathlib import Path

SRC = Path(__file__).resolve().parent
CLUSTERING = SRC.parent
REPO = CLUSTERING.parent
SPARK = CLUSTERING / "spark"
VG = CLUSTERING / "value_generation"
NAME = os.environ.get("WORKLOAD", "tpcds")

_PATH_KEYS = ("value_json", "freq_json", "tables_json", "row_counts_json",
              "columns_in_queries", "values_csv", "query_executions", "query_dir", "manifest")


def _tpcds():
    return {
        "value_json": VG / "data_val_cols_custom.json",
        "freq_json": VG / "frequency_cols_custom.json",
        "tables_json": VG / "tpcds_columns_in_tables.json",
        "row_counts_json": VG / "tpcds_sf30_row_counts.json",
        "columns_in_queries": VG / "tpcds_columns_in_queries.json",
        "values_csv": VG / "tpcds_query_values_custom.csv",
        "query_executions": None,      # utility over distinct queries, as published
        "weighting": "distinct",
        "queries": [f"{i:02d}" for i in range(1, 100)],
        "query_dir": SPARK / "queries_spark",
        "manifest": SPARK / "manifest.json",
        "value_iters": ["0", "1", "2", "3", "4"],
        "value_names": {"0": "Constant", "1": "Value 50", "2": "Value 100",
                        "3": "Value 500", "4": "Value 1000"},
        "k_sweep": list(range(1, 11)),
        "expect_eligible": 10,
        "validate": [["0", "value", 2, 2], ["4", "value", 2, 2], ["4", "random", 2, 2],
                     ["0", "frequency", 5, 2]],
        "pilot": {"strategy": "frequency", "value_iter": "0", "table": "store_sales"},
    }


def _from_profile(path):
    p = json.load(open(path))
    for k in _PATH_KEYS:
        if p.get(k):
            p[k] = REPO / p[k]
    return p


if NAME == "tpcds":
    P = _tpcds()
elif NAME == "imdb":
    P = _from_profile(REPO / "redbench_imdb" / "harness" / "profile.json")
else:
    raise SystemExit(f"unknown WORKLOAD={NAME!r} (expected tpcds or imdb)")


if __name__ == "__main__":    # used by run_phase.sh: python3 workload.py <key>
    import sys
    print(P[sys.argv[1]])
