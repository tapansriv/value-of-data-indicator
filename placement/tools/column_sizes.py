# write function which takes set of column names and runs a SQL SUM
# aggreagation where column name is in the list of column_names passed in
# and it just returns a number. Avoid potential overhead of reading local
# sizes. That or we could pre-size it? 
# How do we get the size of a remote column in a parquet file? Could just
# pre-compute the sizes and then put that in a dict to use
import os
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from datetime import datetime
import re
import json
import sqlglot
from sqlglot import expressions as exp
from concurrent.futures import ThreadPoolExecutor
import json


def _calculate_column_sizes():
    schema_file = "../schema/tpcds_schema_registry.json"
    with open(schema_file) as fp:
        schema_registry = json.load(fp)

    ret = {}
    for table_name, column_names in schema_registry.items():
        ret[table_name] = {}
        # local_path = f"/Users/tapansriv/value_of_data/value-of-data-metric/spark-lineage-api/tpcds/parquet/{table_name}.parquet"
        local_path = f"/mnt/data_10gb/tpcds/{table_name}.parquet"
        pf = pq.ParquetFile(local_path)
        for col_name in column_names: 
            print(col_name)
            col_idx = pf.schema_arrow.get_field_index(col_name)
            size = 0
            for rg in range(pf.num_row_groups):
                col_chunk = pf.metadata.row_group(rg).column(col_idx)
                size += col_chunk.total_compressed_size
            ret[table_name][col_name] = size

    with open("column_sizes.json", 'w') as fp:
        json.dump(ret, fp, indent=4, sort_keys=True)
    return ret


def check():
    schema_file = "../schema/tpcds_schema_registry.json"
    with open(schema_file) as fp:
        schema_registry = json.load(fp)

    with open("column_sizes.json") as fp:
        column_sizes = json.load(fp)

    total_size = 0
    for table_name, columns in schema_registry.items():
        for col in columns:
            assert col in column_sizes[table_name], f"No size provided for column {col} in table {table_name}"
            total_size += column_sizes[table_name][col]

    import math
    total_size_gb = total_size / math.pow(2,30)
    print(f"Total size bytes: {total_size}, Total size GB: {total_size_gb}")

if __name__ == '__main__':
    # _calculate_column_sizes()    
    check()



