"""
Small CLI/demo to show rewrite in action.
Run:
    python -m tools.query_rewriter "<SQL>" --map item=/tmp/item.parquet,date_dim=/tmp/date_dim.parquet
"""

import argparse
from .rewriter import QueryRewriter

def parse_map(arg_list):
    m = {}
    for pair in arg_list.split(","):
        k, v = pair.split("=", 1)
        m[k.strip()] = v.strip()
    return m

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sql", help="SQL query (wrap in quotes)")
    parser.add_argument("--map", required=True, help="Comma-separated table=path pairs")
    args = parser.parse_args()
    mapping = parse_map(args.map)
    r = QueryRewriter()
    print(r.rewrite_query(args.sql, mapping))
