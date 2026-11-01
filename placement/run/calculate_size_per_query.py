from column_cache import ColumnCache
import os
import json
from argparse import ArgumentParser



if __name__ == "__main__":
    parser = ArgumentParser(description="Caching experiment runner")
    parser.add_argument("--cache-dir", type=str, help="Directory to use for column cache", default="../metadata/cache")
    parser.add_argument("--max-cache-size", type=float, help="Maximum size of cache (GB)", default=10.0)
    parser.add_argument("--s3-region", type=str, help="S3 region (if using S3 for cache storage)", default=None)
    parser.add_argument("--s3-access-key", type=str, help="S3 access key (if using S3 for cache storage)", default=None)
    parser.add_argument("--s3-secret-key", type=str, help="S3 secret key (if using S3 for cache storage)", default=None)
    parser.add_argument("--local-mode", action='store_true', help="Use local mode for cache storage", default=True)
    parser.add_argument("--data-dir", type=str, help="Directory containing TPC-DS parquet files", 
                        default="/Users/tapansriv/value_of_data/value-of-data-metric/spark-lineage-api/tpcds/parquet")
    parser.add_argument("--policy", type=str, help="Cache eviction policy", default="lru")
    parser.add_argument("--schema-file", type=str, help="Path to schema file", default="../metadata/tpcds_schema_registry.json")
    parser.add_argument("--value-file", type=str, help="Path to value file", default="../metadata/data_val_cols.json")
    parser.add_argument("--size-file", type=str, help="Path to size file", default="../metadata/column_sizes.json")
    args = parser.parse_args()

    assert args.local_mode or args.s3_region is not None, "Either S3 region must be provided or local mode must be enabled."

    # Make cache directory and load schema registry
    os.makedirs(args.cache_dir, exist_ok=True)
    with open(args.schema_file, 'r') as f:
        schema_registry = json.load(f)

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
    )

    queries = {}
    querydir = "../test/example_queries/tpcds/"
    for i in range(1, 100):
        if i < 10: 
            key = f"0{i}.sql"
        else: 
            key = f"{i}.sql"
        f = open(querydir + key, 'r')
        query = f.read()
        f.close()
        queries[key] = query

    ret = cache.get_required_space_per_query(queries, table_paths)
    with open("../metadata/size_per_query.json", 'w') as f:
        json.dump(ret, f, indent=4)



