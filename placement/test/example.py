"""
Example usage of the ColumnCache system.

This demonstrates how to use the caching system for querying S3 Parquet files.
"""

from column_cache import ColumnCache


def main():
    # Initialize the cache system
    cache = ColumnCache(
        cache_dir="./cache",
        max_cache_size_gb=10.0,
        s3_region="us-east-1"  # Adjust to your AWS region
        # Credentials can be set via environment variables or AWS config
    )
    
    # Example S3 path - replace with your actual path
    s3_path = "s3://your-bucket/path/to/your_table.parquet"
    table_name = "your_table"
    
    # Method 1: Explicitly cache specific columns
    print("Caching specific columns...")
    cache.ensure_columns_cached(
        s3_path=s3_path,
        table_name=table_name,
        columns=["id", "name", "timestamp", "value"]
    )
    
    # Method 2: Execute query (automatically caches required columns)
    # The parser now handles complex queries including:
    # - WITH clauses and CTEs
    # - Table-qualified columns (table.column)
    # - Table aliases
    # - JOINs, WHERE, GROUP BY, ORDER BY clauses
    
    print("Executing simple query (will cache columns if needed)...")
    # Single table query
    result = cache.execute_query(
        query="SELECT id, name FROM your_table WHERE id > 100 LIMIT 10",
        table_paths={table_name: s3_path}
    )
    
    # Multi-table query example:
    # result = cache.execute_query(
    #     query="""
    #         SELECT t1.id, t2.name 
    #         FROM your_table t1 
    #         JOIN other_table t2 ON t1.id = t2.id
    #     """,
    #     table_paths={
    #         "your_table": "s3://your-bucket/path/to/your_table.parquet",
    #         "other_table": "s3://your-bucket/path/to/other_table.parquet"
    #     }
    # )
    
    # Example: Query with table alias and qualified columns
    # result = cache.execute_query(
    #     query="SELECT t.id, t.name FROM your_table AS t WHERE t.id > 100",
    #     table_paths={table_name: s3_path}
    # )
    
    # Example: Query with WITH clause (CTE)
    # result = cache.execute_query(
    #     query="""
    #         WITH filtered AS (
    #             SELECT id, name, value FROM your_table WHERE value > 50
    #         )
    #         SELECT id, name FROM filtered WHERE id > 100
    #     """,
    #     table_paths={table_name: s3_path}
    # )
    
    print(f"Query returned {len(result)} rows")
    print(f"First few results: {result[:3]}")
    
    # Check cache statistics
    stats = cache.get_cache_stats()
    print("\nCache Statistics:")
    print(f"  Total columns cached: {stats['total_columns']}")
    print(f"  Total tables: {stats['total_tables']}")
    print(f"  Cache size: {stats['total_size_gb']:.2f} GB / {stats['max_size_gb']:.2f} GB")
    
    # Example: Clear cache for a specific table
    # cache.clear_cache(table_name=table_name)
    
    # Example: Clear all cache
    # cache.clear_cache()


if __name__ == "__main__":
    main()

