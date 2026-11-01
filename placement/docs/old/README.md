# Selective Column Cache for S3 Parquet Files

A lightweight caching system that selectively caches columns from S3 Parquet files to local disk for efficient querying with DuckDB.

## Features

- **Selective Column Caching**: Cache only the columns you need, not entire tables
- **Automatic Cache Management**: LRU eviction policy with configurable size limits
- **Transparent Query Execution**: Queries work the same whether data is cached or not
- **Low Implementation Time**: Built on DuckDB's native S3 and Parquet support

## Architecture

The system consists of:

1. **Query Analyzer**: Extracts required columns from SQL queries
2. **Cache Manager**: Tracks cached columns using SQLite metadata
3. **Column Fetcher**: Downloads columns from S3 using DuckDB
4. **Eviction Policy**: LRU-based cache management
5. **Query Executor**: Executes queries on cached or S3 data

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set up AWS credentials either through:
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- AWS credentials file (`~/.aws/credentials`)
- Or pass directly to `ColumnCache` constructor

## Usage

### Basic Usage

```python
from column_cache import ColumnCache

# Initialize cache
cache = ColumnCache(
    cache_dir="./cache",
    max_cache_size_gb=10.0,
    s3_region="us-east-1"
)

# Cache specific columns
s3_path = "s3://my-bucket/data/my_table.parquet"
cache.ensure_columns_cached(s3_path, "my_table", ["id", "name", "timestamp"])

# Execute query (automatically caches required columns)
result = cache.execute_query(
    "SELECT id, name FROM my_table WHERE id > 100",
    s3_path,
    "my_table"
)

# Get cache statistics
stats = cache.get_cache_stats()
print(f"Cached {stats['total_columns']} columns from {stats['total_tables']} tables")
```

### Advanced Usage

```python
# Clear cache for a specific table
cache.clear_cache(table_name="my_table")

# Clear all cache
cache.clear_cache()

# Check cache statistics
stats = cache.get_cache_stats()
print(f"Cache size: {stats['total_size_gb']:.2f} GB / {stats['max_size_gb']:.2f} GB")
```

## How It Works

1. **Query Analysis**: When you execute a query, the system extracts which columns are needed
2. **Cache Check**: It checks if those columns are already cached locally
3. **Column Fetching**: Missing columns are fetched from S3 using DuckDB's column projection
4. **Cache Management**: If cache is full, least recently used columns are evicted
5. **Query Execution**: Query runs on local cached data (much faster than S3)

## Cache Structure

```
cache/
├── metadata.duckdb      # DuckDB database tracking cache state
├── tables/
│   ├── table1/
│   │   ├── col1.parquet
│   │   ├── col2.parquet
│   │   └── col3.parquet
│   └── table2/
│       └── ...
```

## Performance Considerations

- **First Query**: May be slower as columns are downloaded from S3
- **Subsequent Queries**: Much faster using local cache
- **Cache Hit Rate**: Monitor and adjust based on query patterns
- **Storage**: Balance cache size with available disk space

## Limitations & Future Improvements

Current implementation is a starting point. Consider:

1. **Better Query Parsing**: Use DuckDB's query planner for accurate column extraction
2. **Column Combination**: Efficiently combine cached columns for queries
3. **Parallel Downloads**: Fetch multiple columns concurrently
4. **Predictive Caching**: Pre-cache columns based on query patterns
5. **Compression**: Compress cached columns to save space
6. **Incremental Updates**: Handle updates to source Parquet files

## Alternative Approaches

### Simpler Alternative: Use DuckDB's Built-in Cache
If you want even lower implementation time, consider using DuckDB's external file cache:

```python
import duckdb

conn = duckdb.connect()
conn.execute("INSTALL httpfs")
conn.execute("LOAD httpfs")
conn.execute("SET enable_external_file_cache = true")

# DuckDB will automatically cache files from S3
result = conn.execute("SELECT col1, col2 FROM read_parquet('s3://bucket/file.parquet')")
```

**Pros**: Zero implementation, automatic caching
**Cons**: Caches entire files, not individual columns, less control

### More Advanced: Hybrid Approach
Combine both strategies:
- Use DuckDB's cache for frequently accessed files
- Use column cache for selective column access

## License

MIT

