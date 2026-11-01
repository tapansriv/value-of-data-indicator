"""
Starting data values (the "1500-query history") from column sets logged by Spark.

Same computation as assign_val_to_de.py (Equal dividing at column granularity over N
queries sampled uniformly with numpy's default_rng(seed)), but the per-query column sets
come from Spark instead of sqlglot:

    spark column sets:  tools/extract_spark_columns.py -> tpcds_columns_in_queries_spark.json

--check reproduces the shipped metadata/data_val_cols_custom.json from the sqlglot column
sets first, so the seed and N used for the DuckDB results are confirmed before anything
new is generated.

Usage:
    python3 spark_baselines.py --check
    python3 spark_baselines.py --columns tpcds_columns_in_queries_spark.json \
        --out ../metadata/spark/data_val_cols_custom.json
"""

import json
import os
from argparse import ArgumentParser
from typing import Dict, List

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(HERE, "..", "metadata")
QUERIES = [f"{i:02d}.sql" for i in range(1, 100)]


def column_values(columns_in_queries: Dict[str, Dict[str, List[str]]], all_columns: List[str],
                  query_values: pd.DataFrame, value_iters: List[str], n: int, seed: int):
    rng = np.random.default_rng(seed)
    sampled = rng.integers(len(QUERIES), size=n)
    qv = query_values.set_index("query_id")
    out = {}
    for it in value_iters:
        dv = {c: 0 for c in all_columns}
        for idx in sampled:
            q = QUERIES[idx]
            rel_cols = [c for cols in columns_in_queries[q].values() for c in cols]
            cval = qv.loc[q, it] / len(rel_cols)
            for c in rel_cols:
                dv[c] += cval
        out[it] = dv
    return out, sampled


def max_abs_diff(a, b):
    return max(abs(a[it][c] - b[it][c]) for it in b for c in b[it])


def main():
    ap = ArgumentParser()
    ap.add_argument("--columns", default=os.path.join(HERE, "tpcds_columns_in_queries.json"))
    ap.add_argument("--query-values", default=os.path.join(META, "tpcds_query_values_custom.csv"))
    ap.add_argument("-n", "--num-samples", type=int, default=1500)
    ap.add_argument("-s", "--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--check", action="store_true",
                    help="reproduce metadata/data_val_cols_custom.json from the sqlglot sets")
    args = ap.parse_args()

    all_columns = [x.strip() for x in open(os.path.join(HERE, "tpcds_column_names.csv")) if x.strip()]
    qv = pd.read_csv(args.query_values)
    iters = [c for c in qv.columns if c not in ("query_id",) and not c.startswith("Unnamed")]

    if args.check:
        shipped = json.load(open(os.path.join(META, "data_val_cols_custom.json")))
        sqlglot_cols = json.load(open(os.path.join(HERE, "tpcds_columns_in_queries.json")))
        mine, _ = column_values(sqlglot_cols, all_columns, qv, iters, args.num_samples, args.seed)
        d = max_abs_diff(mine, shipped)
        print(f"n={args.num_samples} seed={args.seed}: max |diff| vs shipped = {d:.3g} "
              f"-> {'REPRODUCED' if d < 1e-9 else 'NOT reproduced'}")
        return

    cols = json.load(open(args.columns))
    values, sampled = column_values(cols, all_columns, qv, iters, args.num_samples, args.seed)
    out = args.out or os.path.join(META, "spark", "data_val_cols_custom.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fp:
        json.dump(values, fp, indent=4, sort_keys=True)
    with open(out.replace(".json", ".provenance.json"), "w") as fp:
        json.dump({"columns_file": os.path.abspath(args.columns), "n": args.num_samples,
                   "seed": args.seed, "query_values": os.path.abspath(args.query_values),
                   "sampled_query_counts": {QUERIES[i]: int(c) for i, c in
                                            zip(*np.unique(sampled, return_counts=True))}},
                  fp, indent=2, sort_keys=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
