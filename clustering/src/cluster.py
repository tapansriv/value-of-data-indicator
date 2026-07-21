import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc
from pathlib import Path
import math
import os
import json
from argparse import ArgumentParser

def cluster_parquet_table(
    input_parquet_path: str,
    output_dir: str,
    sort_columns: list[str],
    rows_per_file: int,
    row_group_size: int,
    compression: str = "zstd",
    cluster: bool = True,
):
    """
    Read a single-file Parquet table, sort by multiple columns,
    and write it out as fixed-size Parquet chunks with consistent row groups.

    Parameters
    ----------
    input_parquet_path : str
        Path to the input Parquet file (single file).
    output_dir : str
        Directory where clustered Parquet files will be written.
    sort_columns : list[str]
        Columns to sort by (lexicographic order).
    rows_per_file : int
        Number of rows per output Parquet file.
    row_group_size : int
        Number of rows per row group.
    compression : str
        Parquet compression codec (default: zstd).
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Read entire table ----
    table = pq.read_table(input_parquet_path)

    # ---- Validate sort columns ----
    for col in sort_columns:
        if col not in table.schema.names:
            raise ValueError(f"Sort column '{col}' not found in schema")

    # ---- Sort table ----
    if cluster: 
        # lexsort_keys = [(column, "ascending"), ...]
        sort_keys = [(col, "ascending") for col in sort_columns]
        sorted_table = pc.sort_indices(table, sort_keys=sort_keys)
        table = table.take(sorted_table)

    total_rows = table.num_rows
    num_files = math.ceil(total_rows / rows_per_file)

    # ---- Write fixed-size chunks ----
    for i in range(num_files):
        start = i * rows_per_file
        end = min(start + rows_per_file, total_rows)

        chunk = table.slice(start, end - start)

        output_path = output_dir / f"part-{i:05d}.parquet"

        pq.write_table(
            chunk,
            output_path,
            row_group_size=row_group_size,
            compression=compression,
            use_dictionary=True,
            write_statistics=True,
        )

    print(
        f"Wrote {num_files} files to {output_dir} "
        f"(rows_per_file={rows_per_file}, row_group_size={row_group_size})"
    )

if __name__ == "__main__":
    parser = ArgumentParser(description="Cluster Parquet Tables by Specified Columns")
    parser.add_argument("--value-iter", type=str, default="0", help="iteration")
    args = parser.parse_args()


    # Parameters (match your clustering setup)
    ROW_GROUP_SIZE = 128_000
    # row_groups_per_file = 32
    ROWS_PER_FILE = ROW_GROUP_SIZE * 32  # e.g. 4 million rows per file

    tables = ["call_center", "catalog_page", "catalog_returns",
            "catalog_sales", "customer", "customer_address",
            "customer_demographics", "date_dim", "household_demographics",
            "income_band", "inventory", "item", "promotion", "reason", "ship_mode",
            "store", "store_returns", "store_sales", "time_dim", "warehouse",
            "web_page", "web_returns", "web_sales", "web_site"]

    # Directory paths (update as per your setup)
    INPUT_DIR = "/home/cc/tpcds_30gb"
    VOD_OUTPUT_DIR = "/home/cc/tpcds_cluster_value"
    FREQ_OUTPUT_DIR = "/home/cc/tpcds_cluster_freq"
    RAND_OUTPUT_DIR = "/home/cc/tpcds_cluster_rand"
    BASE_OUTPUT_DIR = "/home/cc/tpcds_cluster_base"

    inputs = json.load(open(f"ranked_tbls_{args.value_iter}.json"))
    vod_inputs = [(tbl, cols) for tbl, cols in inputs["value"].items()]
    freq_inputs = [(tbl, cols) for tbl, cols in inputs["frequency"].items()]
    rand_inputs = [(tbl, cols) for tbl, cols in inputs["random"].items()]

    print("\n===== REWRITING VALUE TABLES =====")
    for arg in vod_inputs: 
        tbl = arg[0]
        cols = arg[1]
        input_path = os.path.join(INPUT_DIR, f"{tbl}.parquet")
        output_path = os.path.join(VOD_OUTPUT_DIR, tbl)
        print(arg)
        print(input_path)
        print(output_path)
        cluster_parquet_table(
            input_parquet_path=input_path,
            output_dir=output_path,
            sort_columns=cols,
            rows_per_file=ROWS_PER_FILE,
            row_group_size=ROW_GROUP_SIZE,
        )


    print("\n===== REWRITING FREQ TABLES =====")
    for arg in freq_inputs: 
        tbl = arg[0]
        cols = arg[1]
        input_path = os.path.join(INPUT_DIR, f"{tbl}.parquet")
        output_path = os.path.join(FREQ_OUTPUT_DIR, tbl)
        print(arg)
        print(input_path)
        print(output_path)
        cluster_parquet_table(
            input_parquet_path=input_path,
            output_dir=output_path,
            sort_columns=cols,
            rows_per_file=ROWS_PER_FILE,
            row_group_size=ROW_GROUP_SIZE,
        )

    print("\n===== REWRITING RAND TABLES =====")
    for arg in rand_inputs: 
        tbl = arg[0]
        cols = arg[1]
        input_path = os.path.join(INPUT_DIR, f"{tbl}.parquet")
        output_path = os.path.join(RAND_OUTPUT_DIR, tbl)
        print(arg)
        print(input_path)
        print(output_path)
        cluster_parquet_table(
            input_parquet_path=input_path,
            output_dir=output_path,
            sort_columns=cols,
            rows_per_file=ROWS_PER_FILE,
            row_group_size=ROW_GROUP_SIZE,
        )

    # # Run for all tables
    # print("\n===== REWRITING NO CLUSTER TABLES =====")
    # for tbl in tables:
    #     input_path = os.path.join(INPUT_DIR, f"{tbl}.parquet")
    #     output_path = os.path.join(BASE_OUTPUT_DIR, tbl)
    #     print(tbl)
    #     print(input_path)
    #     print(output_path)
    #     cluster_parquet_table(
    #         input_parquet_path=input_path,
    #         output_dir=output_path,
    #         sort_columns=[],
    #         rows_per_file=ROWS_PER_FILE,
    #         row_group_size=ROW_GROUP_SIZE,
    #         cluster=False
    #     )

