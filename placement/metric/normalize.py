import pandas as pd
import os

def normalize_query_id(query_value_file: str) -> None:
    dir_, full_filename = os.path.split(query_value_file)
    filename, ext = os.path.splitext(full_filename)
    outfile = os.path.join(dir_, f"{filename}_mod{ext}")
    df = pd.read_csv(query_value_file)
    df["query_id"] = df["query_id"].apply(lambda x: f"{int(x[-2:]):02d}.sql")
    df.to_csv(outfile, index=False)


if __name__ == "__main__":
    files = ["../metadata/tpcds_query_values.csv",
             "../metadata/tpcds_query_values_zipf.csv"]

    for file in files:
        normalize_query_id(file)
