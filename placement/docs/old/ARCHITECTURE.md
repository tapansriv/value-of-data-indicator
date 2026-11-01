# Columnar Cache Architecture for S3 Parquet Files

## Overview
This system provides selective column caching from S3 Parquet files to local disk, with intelligent cache management and DuckDB query execution.

## Architecture Components

### 1. Query Analyzer
- **Purpose**: Parse SQL queries to identify required columns
- **Implementation**: Use DuckDB's query planner or simple SQL parsing
- **Output**: List of required columns per table

### 2. Cache Manager
- **Purpose**: Track which columns are cached locally
- **Storage**: 
  - Metadata: DuckDB table tracking cache state (table → columns → local paths)
  - Data: Local Parquet files organized by table/column
- **Operations**:
  - Check cache status
  - Register new cached columns
  - Evict columns based on policy

### 3. Column Fetcher
- **Purpose**: Download required columns from S3 when not cached
- **Implementation**: 
  - Use DuckDB to read specific columns from S3 Parquet
  - Write to local Parquet files
  - Update cache metadata

### 4. Cache Eviction Policy
- **Strategy**: LRU (Least Recently Used) with configurable size limits
- **Metrics**: 
  - Last access time
  - Access frequency
  - Column size
- **Eviction**: Remove least recently used columns when cache limit reached

### 5. Query Executor
- **Purpose**: Execute queries on DuckDB using cached data
- **Strategy**: 
  - Check if all required columns are cached
  - Fetch missing columns from S3
  - Execute query on local Parquet files
  - Update access metadata

## Data Organization

### Local Cache Structure
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

### Metadata Schema
```sql
CREATE TABLE cached_columns (
    table_name VARCHAR,
    column_name VARCHAR,
    local_path VARCHAR,
    size_bytes BIGINT,
    last_accessed TIMESTAMP,
    access_count BIGINT DEFAULT 0,
    cached_at TIMESTAMP,
    PRIMARY KEY (table_name, column_name)
);
```

## Implementation Strategy (Low Time)

### Phase 1: Basic Functionality
1. Query analyzer (simple regex/parsing)
2. Basic cache manager (SQLite metadata)
3. Column fetcher using DuckDB
4. Simple query executor

### Phase 2: Cache Management
1. LRU eviction policy
2. Cache size monitoring
3. Automatic cleanup

### Phase 3: Optimization
1. Batch column fetching
2. Predictive caching
3. Parallel downloads

## Key Design Decisions

1. **Column Storage**: Store each column as separate Parquet file for granular caching
2. **Metadata**: DuckDB table for consistency (same database system for queries and metadata)
3. **DuckDB Integration**: Use DuckDB's native S3 support (httpfs extension)
4. **Query Rewriting**: Rewrite queries to use local paths when columns are cached

## Advantages of This Approach

- **Low Implementation Time**: Leverages DuckDB's built-in S3 and Parquet support
- **Granular Control**: Cache individual columns, not entire tables
- **Flexible**: Easy to add new eviction policies
- **Transparent**: Queries work the same whether data is cached or not

## Performance Considerations

- **Column Projection**: DuckDB can read only required columns from Parquet
- **Local I/O**: Much faster than S3 network calls
- **Cache Hit Rate**: Monitor and optimize based on query patterns
- **Storage**: Balance between cache size and performance

## Alternative Approaches Considered

### Option 1: Store Columns Separately (Chosen)
- **Pros**: Granular control, easy eviction, simple implementation
- **Cons**: Need to combine columns for queries (DuckDB handles this)

### Option 2: Store Row Groups
- **Pros**: Better for range queries
- **Cons**: More complex, less granular

### Option 3: Use DuckDB's Built-in Cache
- **Pros**: Zero implementation
- **Cons**: Less control, caches entire files, not columns

## Recommended Next Steps

1. **Start Simple**: Implement basic column fetching and caching
2. **Add Monitoring**: Track cache hit rates and performance
3. **Optimize**: Based on actual query patterns
4. **Scale**: Add parallel fetching, predictive caching as needed

