import os
import re
from pathlib import Path

SRC = Path("tpcds_parquet_tables")
DST = Path("tpcds_s3_tables")
DST.mkdir(exist_ok=True)

pattern = re.compile(r"([A-Za-z0-9_]+)\.parquet")

for file in SRC.glob("*.sql"):
    text = file.read_text()
    new_text = pattern.sub(r"s3://vod-tpcds-10gb/\1.parquet", text)
    outpath = DST / file.name
    outpath.write_text(new_text)
    print(f"Converted {file.name} -> {outpath}")


