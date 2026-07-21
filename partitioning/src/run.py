import os
import json
import duckdb
from pathlib import Path

HOME = os.path.expanduser("~")
TPCDS_DIR = os.path.join(HOME, "tpcds_30gb")

QUERY_DIRS = {
    # "value": Path("../queries/tpcds"),
    # "frequency": Path("../queries/tpcds"),
    "plain": Path("../queries/tpcds_parquet_tables"),
}

PROFILE_ROOT = Path("profiles")
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
    # con.execute("SET disabled_optimizers = 'statistics_propagation'")

    ret = con.execute(sql)
    ret.fetchall()

def main():
    for strategy, query_dir in QUERY_DIRS.items():
        if strategy == "value":
            db = "tpcds_vod.db"
        elif strategy == "frequency":
            db = "tpcds_freq.db"
        else: 
            db = "hi"

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
