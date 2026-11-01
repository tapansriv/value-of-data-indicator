import os
import glob
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

def get_table_for_column(column, schema_registry):
    for table, columns in schema_registry.items():
        if column in columns:
            return table
    return None

def parse_columns_for_query(query, schema_registry): 
    tree = sqlglot.parse_one(query, read="duckdb")
    ret = {}
    lst = []
    for col in tree.find_all(exp.Column):
        column_name = None
        if hasattr(col, "name") and col.name:
            column_name = str(col.name)
        elif isinstance(col.this, exp.Identifier):
            column_name = str(col.this.this)
        else:
            column_name = str(col.this).lower()

        tbl = get_table_for_column(column_name, schema_registry)
        lst.append(column_name)
        if tbl:
            if tbl not in ret:
                ret[tbl] = set()
            ret[tbl].add(column_name)
        
    # print(lst)
    # print(set(lst))
    # print(ret)
    for key in ret:
        foo = len(ret[key]) != len(set(ret[key]))
        print(f"duplicates {foo}, {key}")
        ret[key] = list(ret[key])
    return ret

if __name__ == "__main__":
    schema_files = {"tpcds": "../schema/tpcds_schema_registry.json", "tpch": "../schema/tpch_schema_registry.json"}

    for dataset in schema_files:
        print(f"Dataset: {dataset}")
        schema_file = schema_files[dataset]

        with open(schema_file) as f:
            schema_registry = json.load(f)

        if dataset == "tpcds":
            querydir = "../test/example_queries/tpcds/"
            values = {}
            for i in range(1, 100):
                if i < 10: 
                    key = f"0{i}.sql"
                else: 
                    key = f"{i}.sql"
                f = open(querydir + key, 'r')
                query = f.read()
                f.close()
                print(key)
                ret = parse_columns_for_query(query, schema_registry)
                values[key] = ret
            with open(f"{dataset}_columns_in_queries.json", 'w') as fp:
                json.dump(values, fp, indent=4, sort_keys=True)
        else:
            queries = glob.glob("../test/example_queries/tpch/*.sql")
            values = {}
            for qfile in queries:
                print(qfile)
                f = open(qfile)
                query = f.read()
                f.close()
                ret = parse_columns_for_query(query, schema_registry)
                key = os.path.basename(qfile)
                values[key] = ret
            with open(f"{dataset}_columns_in_queries.json", 'w') as fp:
                json.dump(values, fp, indent=4, sort_keys=True)







