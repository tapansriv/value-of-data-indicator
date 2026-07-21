import os
import duckdb
from pathlib import Path

HOME = os.path.expanduser("~")
TPCDS_DIR = os.path.join(HOME, "tpcds_30gb")

VALUE_DIR = Path("../queries/tpcds_value_part")
FREQ_DIR = Path("../queries/tpcds_freq_part")

def validate_directory(con, directory, label):
    print(f"\n===== Validating {label} queries =====")

    success = 0
    failed = 0

    for sql_file in sorted(directory.glob("*.sql")):
        sql = sql_file.read_text()

        try:
            con.execute(f"EXPLAIN {sql}")
            print(f"✅ {sql_file.name}")
            success += 1
        except Exception as e:
            print(f"❌ {sql_file.name}")
            print(f"   Error: {e}")
            failed += 1
    print(f"\n{label} Summary: {success} succeeded, {failed} failed")
    return failed

def main():
    con = duckdb.connect()

    # Critical line: make relative parquet paths resolve correctly
    con.execute(f"SET file_search_path='{TPCDS_DIR}'")

    total_failed = 0
    total_failed += validate_directory(con, VALUE_DIR, "VALUE")
    total_failed += validate_directory(con, FREQ_DIR, "FREQ")

    if total_failed == 0:
        print("\n🎉 All queries validated successfully.")
    else:
        print(f"\n⚠️  {total_failed} queries failed validation.")


if __name__ == "__main__":
    main()
