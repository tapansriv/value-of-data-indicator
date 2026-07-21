import os
import json
import duckdb
from pathlib import Path
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("--value-iter", type=str, default="0", help="iteration")
parser.add_argument("--plain-only", action='store_true', help="iteration")
args = parser.parse_args()

HOME = os.path.expanduser("~")
TPCDS_DIR = os.path.join(HOME, "tpcds_30gb")

QUERY_DIRS = {
    # "value": Path("../queries/tpcds_value_part"),
    # "frequency": Path("../queries/tpcds_freq_part"),
    # "random": Path("../queries/tpcds_rand_part"),
    "plain": Path("../queries/tpcds_plain_part"),
}

PROFILE_ROOT = Path(f"profiles_{args.value_iter}")
PROFILE_ROOT.mkdir(exist_ok=True)

# Ensure subdirs for value/frequency
for strategy in QUERY_DIRS:
    (PROFILE_ROOT / strategy).mkdir(exist_ok=True)


def run_query_with_profiling(db, sql, profile_path):
    con = duckdb.connect(db)

    # Set search path for relative parquet refs
    con.execute(f"SET file_search_path='{TPCDS_DIR}';")
    # Enable profiling to capture JSON
    con.execute("PRAGMA enable_profiling='json';")
    con.execute("PRAGMA profiling_output='" + str(profile_path) + "';")

    ret = con.execute(sql)
    ret.fetchall()

def main():
    db = "test"
    for strategy, query_dir in QUERY_DIRS.items():
        print(f"\n=== Running queries for strategy: {strategy} ===")
        for sql_file in sorted(query_dir.glob("*.sql")):
            sql = sql_file.read_text()

            profile_filename = f"{sql_file.stem}_{strategy}.json"
            profile_path = PROFILE_ROOT / strategy / profile_filename

            print(f"Running {sql_file.name} ...")
            try:
                run_query_with_profiling(db, sql, profile_path)
                print(f"  ✅ Profile saved to {profile_path}")
            except Exception as e:
                print(f"  ❌ Failed: {e}")


if __name__ == "__main__":
    main()
