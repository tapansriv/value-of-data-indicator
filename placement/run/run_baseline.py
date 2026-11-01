from column_cache import ColumnCache
import os
import duckdb
import json
import numpy as np
from typing import List, Set, Dict, Optional, Tuple
from argparse import ArgumentParser
import time
import pandas as pd
import boto3


# the values are already populated, so just run the queries and don't provide
# the values for each query (default to 0) or explicitly set them to 0, either way
def run_baseline_duckdb(query_keys, queries) -> Dict[str, float]:
    session = boto3.Session()
    credentials = session.get_credentials()
    access_key = credentials.access_key
    secret_key = credentials.secret_key
    sec = f'''
        CREATE OR REPLACE SECRET secret (
            TYPE s3,
            PROVIDER config,
            KEY_ID '{access_key}',
            SECRET '{secret_key}',
            REGION 'us-east-2'
        );
    '''

    print(f"running baseline!!!!")
    ret: Dict[str, float] = {}
    # total_start = time.time()

    for idx, query in enumerate(queries):
        print("===============================")
        print(query_keys[idx])
        con = duckdb.connect()
        con.execute(sec)

        query_start = time.time()
        con.execute(query)
        query_end = time.time()

        query_runtime = query_end - query_start
        ret[query_keys[idx]] = query_runtime

    # runtime = time.time() - total_start
    # print(f"Total time for experiment: {runtime} seconds")
    # ret["total_time"] = runtime
    return ret

def run_baseline(query_keys, queries) -> Dict[str, float]:
    con = duckdb.connect()
    print(f"running baseline!!!!")
    ret: Dict[str, float] = {}
    total_start = time.time()

    for idx, query in enumerate(queries):
        print("===============================")
        print(query_keys[idx])
        query_start = time.time()

        con.execute(query)
        query_end = time.time()

        query_runtime = query_end - query_start
        ret[query_keys[idx]] = query_runtime

    runtime = time.time() - total_start
    print(f"Total time for experiment: {runtime} seconds")
    ret["total_time"] = runtime
    return ret


if __name__ == "__main__":
    queries = []
    query_keys = []
    querydir = "../test/example_queries/tpcds_s3_tables/"
    for i in range(1, 100):
        if i < 10: 
            outkey = f"0{i}.sql"
        else: 
            outkey = f"{i}.sql"
        f = open(querydir + outkey, 'r')
        query = f.read()
        f.close()
        query_keys.append(outkey)
        queries.append(query)

        # modified_query = cache.rewrite_query(query, local_table_paths)
        # with open(f"{outkey}", 'w') as fp:
        #     fp.write(modified_query)

    ret = run_baseline_duckdb(query_keys=query_keys, queries=queries)
    with open("baseline_times.json", 'w') as fp:
        json.dump(ret, fp, indent=4)
    









