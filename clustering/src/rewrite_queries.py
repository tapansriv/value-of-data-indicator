import os
import json
from pathlib import Path
import sqlglot
from sqlglot import exp
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("--value-iter", type=str, default="0", help="iteration")
args = parser.parse_args()


# HOME = os.path.expanduser("~")
HOME = "/home/cc"

# SRC_QUERY_DIR = "../queries/tpcds_parquet_tables"
SRC_QUERY_DIR = "../queries/tpcds"

OUT_VALUE_DIR = "../queries/tpcds_value_part"
OUT_FREQ_DIR = "../queries/tpcds_freq_part"
OUT_RAND_DIR = "../queries/tpcds_rand_part"
OUT_PLAIN_DIR = "../queries/tpcds_plain_part"

SCHEMA_FILE = "../schema/tpcds_schema_registry.json"
with open(SCHEMA_FILE, "r") as f:
    SCHEMA = json.load(f)

VALUE_ROOT = os.path.join(HOME, "tpcds_cluster_value")
FREQ_ROOT = os.path.join(HOME, "tpcds_cluster_freq")
RAND_ROOT = os.path.join(HOME, "tpcds_cluster_rand")
BASE_ROOT = os.path.join(HOME, "tpcds_cluster_base")

# ---- these should come from your ranking step ----
inputs = json.load(open(f"ranked_tbls_{args.value_iter}.json"))
top_value_tables = inputs["value"].keys()
top_freq_tables = inputs["frequency"].keys()
top_rand_tables = inputs["random"].keys()

# --------------------------------------------------

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def make_read_parquet_node(table, alias, root, hive=False):
    if hive:
        path = f"{root}/{table}/*.parquet"
        func = exp.Anonymous(
            this="read_parquet",
            expressions=[
                exp.Literal.string(path),
            ],
        )
        return exp.alias_(func, alias, table=False)

    else: 
        path = f"{BASE_ROOT}/{table}/*.parquet"
        func = exp.Anonymous(
            this="read_parquet",
            expressions=[
                exp.Literal.string(path),
            ],
        )
        return exp.alias_(func, alias, table=False)



def rewrite_query(sql, target_tables, root):
    tree = sqlglot.parse_one(sql, read="duckdb")

    for table in tree.find_all(exp.Table):
        name = table.name  # e.g. "store_sales"

        if name not in SCHEMA:
            continue

        alias = table.alias_or_name
        new_node = None
        if name not in target_tables:
            new_node = make_read_parquet_node(name, alias, root, hive=False)
        else:
            new_node = make_read_parquet_node(name, alias, root, hive=True)
        table.replace(new_node)

    return tree.sql(dialect="duckdb", pretty=True, indent=4)


def process_queries():
    ensure_dir(OUT_VALUE_DIR)
    ensure_dir(OUT_FREQ_DIR)
    ensure_dir(OUT_PLAIN_DIR)

    for file in Path(SRC_QUERY_DIR).glob("*.sql"):
        sql = file.read_text()

        value_sql = rewrite_query(sql, top_value_tables, VALUE_ROOT)
        freq_sql = rewrite_query(sql, top_freq_tables, FREQ_ROOT)
        rand_sql = rewrite_query(sql, top_rand_tables, RAND_ROOT)
        plain_sql = rewrite_query(sql, [], None)

        (Path(OUT_VALUE_DIR) / file.name).write_text(value_sql)
        (Path(OUT_FREQ_DIR) / file.name).write_text(freq_sql)
        (Path(OUT_RAND_DIR) / file.name).write_text(rand_sql)
        (Path(OUT_PLAIN_DIR) / file.name).write_text(rand_sql)

        print(f"Rewrote {file.name}")


if __name__ == "__main__":
    process_queries()
