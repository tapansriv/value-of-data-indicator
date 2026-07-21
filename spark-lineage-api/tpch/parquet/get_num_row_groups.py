import pyarrow.parquet as pq
import sys 

assert(len(sys.argv) > 1)
tbl = sys.argv[1]

# Load the Parquet file metadata
parquet_file = pq.ParquetFile(f"{tbl}.parquet")

# Get the number of row groups
num_row_groups = parquet_file.num_row_groups

print(f"The Parquet file contains {num_row_groups} row groups.")

