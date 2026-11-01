from column_cache import ColumnCache
import os
import json
import numpy as np
from typing import List, Set, Dict, Optional, Tuple
from argparse import ArgumentParser
import time
import pandas as pd

# first run a sample of tpcds queries ahead of time to populate the cache
# Then run the full set of queries. In either case, supply the value of the
# query when we run it to have it update over time

# parameters needed? size of sample, values for each query in tpcds
def run_with_replay(cache: ColumnCache, queries: List[str], query_values: List[float], 
                    table_paths: Dict[str, str], sample_size: int = 50,  
                    full_sample=False, seed = 0):
    print("replaying!!!!")
    num_queries = len(queries)
    query_idxs = None
    if full_sample:
        query_idxs = np.array([i for i in range(num_queries)])
    else:
        rng = np.random.default_rng(seed)
        query_idxs = rng.integers(num_queries, size=sample_size)

    for idx in query_idxs:
        query = queries[idx]
        value = query_values[idx]
        result = cache.replay_query(
            query,
            table_paths,
            value=value
        )
    cache.materialize_cache_from_metadata(table_paths)


# the values are already populated, so just run the queries and don't provide
# the values for each query (default to 0) or explicitly set them to 0, either way
def run_experiment(cache: ColumnCache, per_q_val: bool, queries: List[str],
                   query_keys: List[str], table_paths: Dict[str, str],
                   query_values: List[float]) -> Dict[str, float]:

    print(f"running experiment!!!! {per_q_val}")
    ret: Dict[str, float] = {}
    total_start = time.time()
    for idx, query in enumerate(queries):
        print("===============================")
        print(query_keys[idx])
        q_value = query_values[idx] if per_q_val else 0.0
        query_start = time.time()
        result = cache.execute_query(
            query,
            table_paths,
            value=q_value
        )
        query_end = time.time()
        query_runtime = query_end - query_start
        ret[query_keys[idx]] = query_runtime

    runtime = time.time() - total_start
    print(f"Total time for experiment: {runtime} seconds")
    ret["total_time"] = runtime

    # Get cache statistics
    stats = cache.get_cache_stats()
    print(f"Cache stats: {stats}")
    # Clear cache
    cache.clear_cache(delete_files=True)
    return ret


if __name__ == "__main__":
    parser = ArgumentParser(description="Caching experiment runner")
    parser.add_argument("--cache-dir", type=str, help="Directory to use for column cache", default="../metadata/cache")
    parser.add_argument("--max-cache-size", type=float, help="Maximum size of cache (GB)", default=10.0)
    parser.add_argument("--s3-region", type=str, help="S3 region (if using S3 for cache storage)", default=None)
    parser.add_argument("--s3-access-key", type=str, help="S3 access key (if using S3 for cache storage)", default=None)
    parser.add_argument("--s3-secret-key", type=str, help="S3 secret key (if using S3 for cache storage)", default=None)
    parser.add_argument("--local-mode", action='store_true', help="Use local mode for cache storage", default=False)
    parser.add_argument("--data-dir", type=str, help="Directory containing TPC-DS parquet files in local mode", default=None)
    parser.add_argument("--policy", type=str, help="Cache eviction policy", default="lru")
    parser.add_argument("--schema-file", type=str, help="Path to schema file", default="../metadata/tpcds_schema_registry.json")
    parser.add_argument("--value-file", type=str, help="Path to value file", default="../metadata/data_val_cols.json")
    parser.add_argument("--size-file", type=str, help="Path to size file", default="../metadata/sizes_30gb/column_sizes.json")

    parser.add_argument("--query-value-file", type=str, help="File with query values", 
                        default = "../metadata/tpcds_query_values.csv")
    parser.add_argument("--value-iter", type=str, help="Which iteration of query values to use", default="0")
    parser.add_argument("--fill-cache", action='store_true', help="Should we fill cache beforehand", default=False)
    parser.add_argument("--dynamic", action='store_true', help="Static or dynamic updated values", default=False)
    parser.add_argument("--seed", type=int, help="Random seed for sampling queries", default=42)
    parser.add_argument("--outfile", type=str, help="Output for experiment results", default="experiment_results.json")
    args = parser.parse_args()

    assert args.local_mode or args.s3_region is not None, "Either S3 region must be provided or local mode must be enabled."
    print(args, flush=True)

    # Make cache directory and load schema registry
    os.makedirs(args.cache_dir, exist_ok=True)
    with open(args.schema_file, 'r') as f:
        schema_registry = json.load(f)

    # Define table paths
    table_paths = None
    if not args.local_mode:
        # Using explicit pyarrow filesystem, so path just includes
        # bucket/filename for s3
        table_paths = {table_name: f"vod-tpcds-10gb/{table_name}.parquet" for table_name in schema_registry.keys()}
    else:
        table_paths = {table_name: os.path.join(args.data_dir, f"{table_name}.parquet") for table_name in schema_registry.keys()}

    cache = ColumnCache(
        cache_dir=args.cache_dir,
        max_cache_size_gb=args.max_cache_size,
        s3_region=args.s3_region,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key,
        local_mode=args.local_mode,
        data_dir=args.data_dir,
        eviction_policy=args.policy,
        schema_file=args.schema_file,
        value_file=args.value_file,
        size_file=args.size_file,
        value_iter=args.value_iter
    )

    queries = []
    query_keys = []
    # take specified iteration of query values
    query_values = pd.read_csv(args.query_value_file)[args.value_iter].to_list() 
    querydir = "../test/example_queries/tpcds/"
    for i in range(1, 100):
        key = f"{i:02d}.sql"
        f = open(querydir + key, 'r')
        query = f.read()
        f.close()
        queries.append(query)
        query_keys.append(key)

    # Do we fill the cache first by running some queries before the experiment
    # start
    if args.fill_cache:
        run_with_replay(cache, queries=queries,
                        query_values=query_values, table_paths=table_paths,
                        seed=args.seed, full_sample=True)
        # run_with_replay(cache, sample_size=50, queries=queries,
        #                 query_values=query_values, table_paths=table_paths,
        #                 seed=args.seed)

    # Actual experiment, will be dynamic or static based on args.dynamic flag
    ret = run_experiment(cache, per_q_val=args.dynamic, queries=queries,
                   query_keys=query_keys, table_paths=table_paths,
                   query_values=query_values)
    
    with open(args.outfile, "w") as f:
        json.dump(ret, f, indent=4)


