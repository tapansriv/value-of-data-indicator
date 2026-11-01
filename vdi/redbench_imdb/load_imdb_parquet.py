"""Build the IMDb source Parquet for the sorting harness: one <table>.parquet per table.

  python3 load_imdb_parquet.py --out $WORK/imdb/source            # downloads imdb.tgz
  python3 load_imdb_parquet.py --out DIR --csv-dir EXISTING_CSVS   # reuse extracted CSVs

Source: the JOB IMDb snapshot, https://event.cwi.nl/da/job/imdb.tgz (1,263,193,115 bytes;
21 tables; ~3.6 GB of CSV). The archive's own schematext.sql is used: its column names match
the canonical JOB schema.sql exactly and its varchar limits are wider, so nothing truncates.

Loading is STRICT: no ignore_errors, because dropping malformed rows would silently change the
row counts the eligibility filter and the layouts depend on. Row counts are checked against
imdb_row_counts.json; any mismatch is an error. Row-group size here is irrelevant: the harness
rewrites everything into Iceberg with 128k-row row groups (build_iceberg.py).
Needs: python duckdb (any recent version).
"""
import argparse, json, os, re, sys, tarfile, urllib.request
from pathlib import Path
import duckdb

URL = "https://event.cwi.nl/da/job/imdb.tgz"
SIZE = 1_263_193_115
HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="directory for <table>.parquet")
    ap.add_argument("--csv-dir", help="already-extracted imdb.tgz (skips the download)")
    ap.add_argument("--work", help="scratch dir for the download/extract (default: <out>/../imdb_csv)")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    if args.csv_dir:
        csv_dir = Path(args.csv_dir)
    else:
        work = Path(args.work or out.parent / "imdb_csv"); work.mkdir(parents=True, exist_ok=True)
        tgz = work / "imdb.tgz"
        if not tgz.exists() or tgz.stat().st_size != SIZE:
            print(f"downloading {URL} ...", flush=True)
            urllib.request.urlretrieve(URL, tgz)
        assert tgz.stat().st_size == SIZE, f"imdb.tgz is {tgz.stat().st_size} bytes, expected {SIZE}"
        csv_dir = work / "csv"
        if not (csv_dir / "schematext.sql").exists():
            csv_dir.mkdir(exist_ok=True)
            with tarfile.open(tgz) as tf:
                tf.extractall(csv_dir)
    schema = (csv_dir / "schematext.sql").read_text()
    tables = re.findall(r"CREATE TABLE (\w+)", schema)
    expected = json.load(open(HERE / "imdb_row_counts.json"))
    assert sorted(tables) == sorted(expected), "schema tables differ from imdb_row_counts.json"

    con = duckdb.connect(str(out.parent / "imdb_load.duckdb"))
    for t in tables:
        con.execute(f"DROP TABLE IF EXISTS {t}")
    con.execute(schema)
    bad = 0
    for t in tables:
        con.execute(f"""COPY {t} FROM '{csv_dir / (t + ".csv")}'
                        (FORMAT CSV, HEADER false, QUOTE '"', ESCAPE '\\', NULLSTR '')""")
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        ok = n == expected[t]; bad += not ok
        con.execute(f"COPY {t} TO '{out / (t + '.parquet')}' (FORMAT PARQUET)")
        print(f"{t:18s} {n:12,d}  {'ok' if ok else f'MISMATCH, expected {expected[t]:,}'}", flush=True)
    con.close()
    os.remove(out.parent / "imdb_load.duckdb")
    if bad:
        sys.exit(f"{bad} table(s) do not match imdb_row_counts.json -- stop and ask Tapan")
    print(f"OK: {len(tables)} tables -> {out}")


if __name__ == "__main__":
    main()
