"""
Selective Column Caching System for S3 Parquet Files with DuckDB

This module provides a caching layer that selectively caches columns
from S3 Parquet files to local disk for efficient querying.
"""

import os
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from datetime import datetime, timedelta
import json
import math
import sqlglot
from sqlglot import expressions as exp
from concurrent.futures import ThreadPoolExecutor

BATCH_SIZE = 32
GB_TO_BYTES = math.pow(2, 30)

class ColumnCache:
    """
    Manages selective column caching from S3 Parquet files to local disk.
    """

    def __init__(
        self,
        cache_dir: str = "./cache",
        max_cache_size_gb: float = 10.0,
        s3_region: Optional[str] = None,
        s3_access_key: Optional[str] = None,
        s3_secret_key: Optional[str] = None,
        local_mode: bool = False,
        data_dir: Optional[str] = None, 
        eviction_policy: str = "lru",
        schema_file: str = "./metadata/tpcds_schema_registry.json",
        value_file: str = "./metadata/data_val_cols.json",
        size_file: str = "./metadata/column_sizes.json",
        value_iter: str = "0",
        verbose: bool = False,
        tie_round_digits: Optional[int] = None,
    ):
        """
        Initialize the column cache system.
        
        Args:
            cache_dir: Directory for local cache storage (directory2 in local mode)
            max_cache_size_gb: Maximum cache size in GB
            s3_region: AWS region for S3 access (ignored in local mode)
            s3_access_key: AWS access key (optional, can use env vars, ignored in local mode)
            s3_secret_key: AWS secret key (optional, can use env vars, ignored in local mode)
            local_mode: If True, operate on local filesystem instead of S3
            data_dir: Directory where data files are stored (directory1 in local mode, required if local_mode=True)
            eviction_policy: What cache eviction policy to be used ("lru" default)
            schema_registry: Dictionary mapping table names to sets of column names (optional)
        """
        self.local_mode = local_mode
        self.data_dir = Path(data_dir) if data_dir else None
        if eviction_policy not in ("lru", "vod"):
            raise ValueError("eviction_policy must be either 'lru' or 'vod'")
        self.eviction_policy = eviction_policy
        self.verbose = verbose
        # Test hooks for comparing against the Spark harness (test/validate_spark_vdi.py);
        # both default off, leaving the original behaviour unchanged. With
        # tie_round_digits set, eviction ties are broken by (table, column) after rounding.
        self.tie_round_digits = tie_round_digits
        self.eviction_log: List[List[Tuple[str, str]]] = []
        # With tie_round_digits set, LRU recency is per phase of a query (columns it
        # touches share one time, columns it caches a later one) instead of per column in
        # set-iteration order, which Python randomizes per process.
        self._frozen_now = None
        self._logical_us = 0


        with open(schema_file) as fp:
            self.schema_registry = json.load(fp)

        with open(value_file) as fp:
            column_value_set = json.load(fp)
            assert value_iter in column_value_set, f"Value iteration {value_iter} not found in value file"
            self.column_values = column_value_set[value_iter]

        with open(size_file) as fp:
            self.column_sizes = json.load(fp)

        for table_name, columns in self.schema_registry.items():
            for col in columns:
                assert col in self.column_sizes[table_name], f"No size provided for column {col} in table {table_name}"

        self.filesystem = None
        if local_mode and not data_dir:
            raise ValueError("data_dir must be provided when local_mode=True")

        if local_mode and self.data_dir:
            if not self.data_dir.exists():
                raise ValueError(f"Data directory does not exist: {data_dir}")
            if not self.data_dir.is_dir():
                raise ValueError(f"Data path is not a directory: {data_dir}")

        self.cache_dir = Path(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.tables_dir = f"{self.cache_dir}/tables"
        os.makedirs(self.tables_dir, exist_ok=True)
        
        self.max_cache_size_bytes = max_cache_size_gb * GB_TO_BYTES

        self.rg_cache = {} # cache of number of row groups per table
        
        # Initialize DuckDB connection
        # Use persistent database for metadata (stored in cache directory)
        metadata_db_path = str(f"{self.cache_dir}/metadata.duckdb")
        self.conn = duckdb.connect(metadata_db_path)
        
        if not local_mode:
            self.filesystem = pa.fs.S3FileSystem(
                region=s3_region,
                access_key=s3_access_key,
                secret_key=s3_secret_key
            )
            self._setup_duckdb(s3_region, s3_access_key, s3_secret_key)
        
        # Initialize metadata tables in DuckDB
        self._init_metadata_db()

    def _now(self):
        return self._frozen_now if self._frozen_now is not None else datetime.now()

    def _freeze_now(self):
        if self.tie_round_digits is not None:
            self._logical_us += 1
            self._frozen_now = datetime(2000, 1, 1) + timedelta(microseconds=self._logical_us)

    def _setup_duckdb(self, region: Optional[str], access_key: Optional[str], secret_key: Optional[str]):
        """Configure DuckDB for S3 access."""
        # Install and load httpfs extension
        self.conn.execute("INSTALL httpfs")
        self.conn.execute("LOAD httpfs")
        
        # Configure S3 credentials if provided
        if access_key and secret_key:
            s3_config = {
                'key_id': access_key,
                'secret': secret_key,
            }
            if region:
                s3_config['region'] = region
            
            # Create S3 secret
            config_str = ", ".join([f"{k} '{v}'" for k, v in s3_config.items()])
            self.conn.execute(f"CREATE SECRET IF NOT EXISTS s3_secret (TYPE s3, {config_str})")
        elif region:
            # If using IAM role (no explicit credentials), still set region
            # DuckDB will use AWS SDK defaults (IAM role) for credentials
            self.conn.execute(f"CREATE SECRET IF NOT EXISTS s3_secret (TYPE s3, region '{region}')")
        else: 
            raise ValueError("S3 access_key and secret_key must be provided, or region must be specified for IAM role usage.")

    def _init_metadata_db(self):
        """Initialize the metadata DuckDB table."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cached_columns (
                table_name VARCHAR,
                column_name VARCHAR,
                local_path VARCHAR,
                size_bytes BIGINT,
                last_accessed TIMESTAMP,
                eviction_metric DOUBLE,
                access_count BIGINT DEFAULT 0,
                cached_at TIMESTAMP,
                in_cache BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (table_name, column_name)
            )
        """)

        # if self.eviction_policy == "lru":
        #     self.conn.execute("""
        #         CREATE INDEX IF NOT EXISTS idx_last_accessed
        #         ON cached_columns(last_accessed)
        #     """)
        # else:  # vod
        #     self.conn.execute("""
        #         CREATE INDEX IF NOT EXISTS idx_eviction_metric
        #         ON cached_columns(eviction_metric)
        #     """)

    def _get_table_for_column(self, column: str) -> Optional[str]:
        for table, columns in self.schema_registry.items():
            if column in columns:
                return table
        return None

    def get_columns_for_tables(self, query: str) -> Dict[str, Set[str]]:
        tree = sqlglot.parse_one(query, read="duckdb")
        ret = {}
        for col in tree.find_all(exp.Column):
            # column name might be in col.name or col.this
            column_name = None
            if hasattr(col, "name") and col.name:
                column_name = str(col.name)
            elif isinstance(col.this, exp.Identifier):
                column_name = str(col.this.this)
            else:
                column_name = str(col.this).lower()

            tbl = self._get_table_for_column(column_name)
            if tbl:
                if tbl not in ret:
                    ret[tbl] = set()
                ret[tbl].add(column_name)
        return ret

    def _get_cached_columns(self) -> Dict[str, Dict]:
        """Get all cached columns."""
        result = self.conn.execute("""
            SELECT column_name, local_path, size_bytes, last_accessed, eviction_metric, access_count
            FROM cached_columns
            WHERE in_cache = TRUE
            ORDER BY eviction_metric DESC
        """).fetchall()
        
        cached = {}
        for row in result:
            cached[row[0]] = {
                'local_path': row[1],
                'size_bytes': row[2],
                'last_accessed': row[3],
                'eviction_metric': row[4],
                'access_count': row[5]
            }
        return cached
    
    def _get_local_path(self, table_name: str) -> Optional[Path]:
        """Get local path of a cached column."""
        result = self.conn.execute("""
            SELECT DISTINCT(local_path) FROM cached_columns
            WHERE table_name = ? AND in_cache = TRUE
        """, [table_name]).fetchone()
        
        if result:
            assert len(result) == 1, "Multiple local paths found for the same table"
            return Path(result[0])
        return None

    def _is_column_cached(self, table_name: str, column_name: str) -> bool:
        """Check if a column is cached locally."""
        result = self.conn.execute("""
            SELECT 1 FROM cached_columns
            WHERE table_name = ? AND column_name = ? AND in_cache = TRUE
        """, [table_name, column_name]).fetchone()
        
        return result is not None

    def _get_parquet_metadata(self, table_name: str, source_path: str) -> int:
        """Get number of row groups in a Parquet file. Cache to avoid repeated reads."""
        if table_name in self.rg_cache:
             return self.rg_cache[table_name]
        pf = pq.ParquetFile(source_path, filesystem=self.filesystem)
        self.rg_cache[table_name] = (pf.num_row_groups, pf.metadata.row_group(0).num_rows)
        return (pf.num_row_groups, pf.metadata.row_group(0).num_rows)

    # Currently unused, but could be used to calculate column sizes dynamically
    # using PyArrow library. At the moment, we assume that sizes are precomputed
    # and provided in a JSON file.
    def _calculate_column_sizes_arrow(self, local_path: str, column_names: List[str]) -> Dict[str, int]:
        try:
            pf = pq.ParquetFile(local_path, filesystem=None)
            ret = {}
            for col_name in column_names: 
                col_idx = pf.schema_arrow.get_field_index(col_name)
                size = 0
                for rg in range(pf.num_row_groups):
                    col_chunk = pf.metadata.row_group(rg).column(col_idx)
                    size += col_chunk.total_compressed_size
                ret[col_name] = size
            return ret
        except Exception as e:
            print(column_names)
            raise e


    def _cache_columns(self, table_name: str, column_names: List[str],
                       source_path: str, local_path: Path, value_per_column = 0):
        """Register a cached column in metadata."""
        local_con = self.conn.cursor()
        for column_name in column_names:
            now = self._now()
            size_bytes = self.column_sizes[table_name][column_name]
            # If no entry in the DB already, add value to the baseline value loaded from the file.
            # If there is an entry, add the passed in value to the existing value in the metadata cache
            assert column_name in self.column_values
            eviction_metric = self.column_values[column_name] + value_per_column

            # DuckDB uses INSERT ... ON CONFLICT for upsert
            local_con.execute("""
                INSERT INTO cached_columns
                (table_name, column_name, local_path, size_bytes, last_accessed, eviction_metric, access_count, cached_at, in_cache)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, TRUE)
                ON CONFLICT (table_name, column_name) 
                DO UPDATE SET 
                    local_path = EXCLUDED.local_path,
                    size_bytes = EXCLUDED.size_bytes,
                    last_accessed = EXCLUDED.last_accessed,
                    eviction_metric = cached_columns.eviction_metric + ?,
                    access_count = cached_columns.access_count + 1,
                    cached_at = EXCLUDED.cached_at,
                    in_cache = EXCLUDED.in_cache

            """, [table_name, column_name, str(local_path), size_bytes, now, eviction_metric, now, value_per_column])
    
    def _update_column_values(self, table_name: str, column_name: str, value_per_column = 0):
        """Update last accessed time, increment access count, update value of
        data. Assumes that column is already cached
        ."""
        self.conn.execute("""
            UPDATE cached_columns
            SET last_accessed = ?, access_count = access_count + 1, eviction_metric = eviction_metric + ?
            WHERE table_name = ? AND column_name = ?
        """, [self._now(), value_per_column, table_name, column_name])

    def _fetch_columns_batch(self, source_path: str, table_name: str, batch_id: int, required_columns: list[str]):
        num_rgs, _ = self._get_parquet_metadata(table_name, source_path)
        rg_start = batch_id * BATCH_SIZE
        rg_end = min(rg_start + BATCH_SIZE, num_rgs)
        rg_ids = list(range(rg_start, rg_end))

        batch_path = os.path.join(
            self.tables_dir, table_name, f"batch_{batch_id:06d}.parquet"
        )
        os.makedirs(os.path.dirname(batch_path), exist_ok=True)

        cached_tbl = None
        cached_cols = set()

        if os.path.exists(batch_path):
            cached_pf = pq.ParquetFile(batch_path, filesystem=None)
            try: 
                cached_tbl = cached_pf.read()
                cached_cols = set(cached_tbl.schema.names)
            except:
                print(f"FAILED {table_name}, {batch_id}")
                raise

        src_pf = pq.ParquetFile(source_path, filesystem=self.filesystem)
        fetched_tbl = src_pf.read_row_groups(rg_ids, columns=required_columns)
        if cached_tbl is not None:
            merged = pa.Table.from_arrays(
                list(cached_tbl.columns) + list(fetched_tbl.columns),
                names=list(cached_tbl.schema.names) + list(required_columns),
            )
        else:
            merged = fetched_tbl
        pq.write_table(merged, batch_path)

    def _fetch_columns_parallel(self, source_path: str, table_name: str,
                                column_names: list[str], max_workers: int = 4):
        """
        Fetch specific columns from a Parquet file (S3 or local) and save
        locally. Data is read in batches of 32 row groups at a time in parallel
        threads for performance and to avoid memory pressure.

        Args:
            source_path: S3 path (e.g., s3://bucket/path/file.parquet) or local path
            table_name: Name of the table
            column_name: Name of the column to fetch
            max_workers: Number of parallel threads to use 

        Returns:
            Path to the local cached files for table
        """
        local_path = os.path.join(self.tables_dir, table_name, "*.parquet")
        print(f"Fetching {column_names} from {source_path} to {local_path}")

        num_row_groups, _ = self._get_parquet_metadata(table_name, source_path)
        # ceiling div not commutative, need -1 when num_rgs aligns with batch size
        num_batches = (num_row_groups + BATCH_SIZE - 1) // BATCH_SIZE
        def task(batch_id):
            self._fetch_columns_batch(
                source_path,
                table_name,
                batch_id,
                column_names,
            )

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for _ in ex.map(task, range(num_batches)):
                pass
        print("Finished fetching columns.")

    def _fetch_columns(self, source_path: str, table_name: str, column_names: List[str]) -> Path:
        """
        Deprecated: Switched to _fetch_columns_parallel which reads tables in
        row group chunks at a time  to avoid memory pressure

        """
        # Create table directory
        local_path = f"{self.tables_dir}/{table_name}.parquet"
        print(f"Fetching columns from {source_path} to {local_path}")
        fetched_columns = pq.read_table(source_path, columns=column_names,
                                        filesystem=self.filesystem)
        ret = fetched_columns
        if os.path.exists(local_path):
            merged = pq.read_table(local_path, filesystem=None)
            for col in column_names:
                merged = merged.append_column(col, fetched_columns.column(col))
            ret = merged
        pq.write_table(ret, local_path, filesystem=None)
        return local_path

    def _get_total_cache_size(self) -> int:
        """Get total size of cached data in bytes."""
        local_con = self.conn.cursor()
        result = local_con.execute("SELECT SUM(size_bytes) FROM cached_columns WHERE in_cache = TRUE").fetchone()
        return result[0] if result and result[0] is not None else 0

    def _evict_columns_batch(self, batch_path: str, columns_to_evict: List[str], 
                              delete_file: bool):
        if delete_file:
            os.remove(batch_path)
        else:
            pf = pq.ParquetFile(batch_path, filesystem=None)
            tbl = pf.read()
            trimmed = tbl.drop(columns_to_evict)
            pq.write_table(trimmed, batch_path)

    def _evict_columns_parallel(self, table_name: str, columns_to_evict: List[str], 
                               delete_file: bool, max_workers: int = 4):

        table_dir = os.path.join(self.tables_dir, table_name)
        batch_files = sorted(f for f in os.listdir(table_dir) if f.endswith(".parquet"))

        def task(fname):
            self._evict_columns_batch(
                os.path.join(table_dir, fname),
                columns_to_evict,
                delete_file
            )

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for _ in ex.map(task, batch_files):
                pass

    def _evict_columns(self, required_space: int, required_columns: List[str],
                       replay=False):
        """
        Evict columns to free up space using the eviction policy passed in at
        object creation.

        Args:
            required_space: Amount of space needed in bytes
            required_columns: List of columns that are required by the current query and so cannot be evicted
            replay: If True, only replay effect on cache in metadata without modifying underlying files
        """
        print("EVICTING!!")
        sort_metric = "last_accessed" if self.eviction_policy == "lru" else "eviction_metric"
        if self.tie_round_digits is not None:
            if self.eviction_policy == "vod":
                sort_metric = f"ROUND(eviction_metric, {self.tie_round_digits})"
            sort_metric += " ASC, table_name ASC, column_name"

        local_con = self.conn.cursor()
        rows = local_con.execute(f"""
            SELECT table_name, column_name, local_path, size_bytes
            FROM cached_columns
            WHERE in_cache = TRUE
            ORDER BY {sort_metric} ASC
        """).fetchall()
        evicted: List[Tuple[str, str]] = []
        self.eviction_log.append(evicted)

        counts = local_con.execute(f"""
            SELECT table_name, COUNT(*) as col_count
            FROM cached_columns 
            WHERE in_cache = TRUE
            GROUP BY table_name
        """).fetchall()

        table_counts = {row[0]: row[1] for row in counts}
        to_evict = {}
        freed_space = 0
        for row in rows:
            if freed_space >= required_space:
                break

            table_name, column_name, local_path, size_bytes = row
            if column_name in required_columns: 
                if self.verbose:
                    print(f"Skipping eviction of {table_name}.{column_name} as it is required for current query")
                continue

            freed_space += size_bytes
            evicted.append((table_name, column_name))
            if table_name not in to_evict:
                to_evict[table_name] = []
            to_evict[table_name].append((column_name, local_path))
            if self.verbose:
                print(f"Evicting {table_name}.{column_name}, size: {size_bytes}")
            # Keep in metadata to preserve VoD information but mark as not in cache
            local_con.execute("""
                UPDATE cached_columns
                SET in_cache = FALSE
                WHERE table_name = ? AND column_name = ?
            """, [table_name, column_name])

        # scoped function
        def remove_columns_from_file(args: Tuple[str, List[str], bool]):
            tbl_name, columns_to_drop, delete_file = args
            self._evict_columns_parallel(tbl_name, columns_to_drop, delete_file)

        if not replay:
            arg_list = []
            for table_name, col_info in to_evict.items():
                columns_to_drop = [col[0] for col in col_info]
                arg = [table_name, columns_to_drop, (len(col_info) == table_counts[table_name])]
                arg_list.append(arg)

            with ThreadPoolExecutor(max_workers = len(arg_list)) as pool:
                for _ in pool.map(remove_columns_from_file, arg_list):
                    pass

    def evict_necessary_columns(self, args: List[Tuple[str, str, List[str]]],
                                value_per_column = 0, replay: bool = False) -> List[Tuple[str, str, List[str]]]: 
        if self.verbose and replay:
            cached_columns = self._get_cached_columns()
            for key in cached_columns:
                val = cached_columns[key]
                print(f"Column: {key}, local_path: {val['local_path']}, size: {val['size_bytes']}, " + \
                      f"last_accessed: {val['last_accessed']}, " + \
                      f"eviction_metric: {val['eviction_metric']}, " + \
                      f"access_count: {val['access_count']}")

        ret = []
        total_size_to_fetch = 0
        column_list = []
        for arg in args:
            (source_path, table_name, columns) = arg
            columns_to_fetch = []
            column_list.extend(columns)
            for column in columns:
                if not self._is_column_cached(table_name, column):
                    columns_to_fetch.append(column)
                    total_size_to_fetch += self.column_sizes[table_name][column]
                else: 
                    self._update_column_values(table_name, column,
                                               value_per_column = value_per_column)
            # If there are columns that need to be fetched for this table, add
            # to the list of tables/columns to fetch. If all columns are already
            # cached, we can skip fetching for this table entirely.
            if len(columns_to_fetch) > 0:
                ret.append([source_path, table_name, columns_to_fetch])
            else: 
                print(f"All columns for {table_name} are already cached, skipping fetch. ")

        # Check if we need to evict columns
        current_size = self._get_total_cache_size()
        if current_size + total_size_to_fetch > self.max_cache_size_bytes:
            space_needed = (current_size + total_size_to_fetch) - self.max_cache_size_bytes
            percent_evicted = 100 * space_needed / self.max_cache_size_bytes
            if self.verbose:
                print(f"Current cache size: {current_size/GB_TO_BYTES}, " + \
                      f"need to fetch additional {total_size_to_fetch/GB_TO_BYTES}, " + \
                      f"evicting {space_needed/GB_TO_BYTES} GB " + \
                      f"max size: {self.max_cache_size_bytes/GB_TO_BYTES}")
            self._evict_columns(space_needed, column_list, replay=replay)
        return ret

    def ensure_columns_cached(self, arg_list: List[Tuple[str, str, List[str]]],
                              value_per_column = 0) -> Dict[str, str]:
        # list of (source_path, table_name, columns),  for each one we need to
        # pull those columns from the source path to the cache in parallel
        # Then update cache for each new entry 
        # Return mapping of tables to local paths for the query text replacement 
        args_list_to_fetch = self.evict_necessary_columns(arg_list, value_per_column = value_per_column)

        def helper(arg):
            (source_path, table_name, columns_to_fetch) = arg
            local_path = os.path.join(self.tables_dir, table_name, "*.parquet")
            self._fetch_columns_parallel(source_path, table_name, columns_to_fetch)
            self._cache_columns(table_name, columns_to_fetch, source_path,
                                local_path, value_per_column = value_per_column)

        # Fetch columns from source (S3 or local)
        # Using a ThreadPoolExecutor to parallelize pulling columns into the
        # cache and updating the metadata of what is cached per table/column.
        if len(args_list_to_fetch) > 0:
            with ThreadPoolExecutor(max_workers = len(args_list_to_fetch)) as pool:
                for _ in  pool.map(helper, args_list_to_fetch):
                    pass

    def rewrite_query(
        self,
        sql: str, 
        table_to_local_path: Dict[str, str],
        dialect: str = "duckdb"
    ) -> str:
        mapping = {k.lower(): v for k, v in table_to_local_path.items()}
        tree = sqlglot.parse_one(sql, read=dialect)

        cte_names = set()
        with_node = tree.find(exp.With)
        if with_node:
            for cte in with_node.expressions:
                cte_names.add(cte.alias.lower())

        used_aliases = set()

        # Walk table nodes and replace where appropriate
        for table_node in list(tree.find_all(exp.Table)):
            base_node = table_node.this
            if isinstance(base_node, exp.Identifier):
                base_name = base_node.this
            else:
                base_name = str(base_node)

            alias = table_node.alias
            if base_name.lower() in cte_names or base_name.lower() not in mapping:
                continue
            if not alias:
                alias = base_name
            if alias.lower() in used_aliases or alias.lower() in cte_names:
                raise ValueError(f"Alias conflict for table {base_name} with alias {alias}")

            used_aliases.add(alias.lower)
            local_path = mapping[base_name.lower()]
            func = exp.Anonymous(
                this="read_parquet",
                expressions=[exp.Literal.string(local_path)],
            )
            alias_expr = exp.Alias(this=func, alias=exp.to_identifier(alias))
            table_node.replace(alias_expr)

        modified_sql = tree.sql(dialect=dialect)
        return modified_sql

    def get_required_space_per_query(
        self,
        queries: Dict[str, str],
        table_paths: Dict[str, str],
    ) -> Dict[str, float]:
        ret = {}
        for query_id, query in queries.items():
            columns_for_table = self.get_columns_for_tables(query)

            # Validate that all tables in query have paths provided
            missing_tables = set(columns_for_table.keys()) - set(table_paths.keys())
            if missing_tables:
                raise ValueError(f"Missing source paths for tables: {missing_tables}. ")
            total_size_needed: float = 0.0
            for table_name, columns in columns_for_table.items():
                for column in columns:
                    total_size_needed += self.column_sizes[table_name][column] 
            ret[query_id] = total_size_needed / GB_TO_BYTES
        return ret

    def replay_query(
        self,
        query: str,
        table_paths: Dict[str, str],
        value = 0,
    ) -> List[Tuple]:
        """
        Update the cache metadata based on a query
        """
        columns_for_table = self.get_columns_for_tables(query)
        num_relevant_columns = sum([len(cols) for cols in columns_for_table.values()])
        value_per_column = value / num_relevant_columns if (value > 0 and num_relevant_columns > 0 ) else 0

        # Validate that all tables in query have paths provided
        missing_tables = set(columns_for_table.keys()) - set(table_paths.keys())
        if missing_tables:
            raise ValueError(f"Missing source paths for tables: {missing_tables}. ")
        
        # Generate list: (source path for data, table name, list of columns referenced)
        # to fetch. We put them in a list to allow for copying in parallel
        arg_list = []
        for table_name in columns_for_table:
            source_path = table_paths[table_name]

            # In local mode, resolve the source path relative to data_dir
            if self.local_mode:
                if not Path(source_path).is_absolute():
                    source_path = f"{self.data_dir}/{source_path}"

            columns = list(columns_for_table[table_name])
            # if no columns specified, cache all columns for the table
            if columns is None:
                columns = list(self.schema_registry[table_name])
            arg_list.append((source_path, table_name, columns))

        self._freeze_now()
        args_list_to_fetch = self.evict_necessary_columns(arg_list, value_per_column = value_per_column, replay = True)
        self._freeze_now()

        for arg in args_list_to_fetch:
            (source_path, table_name, columns_to_fetch) = arg
            local_path = f"{self.tables_dir}/{table_name}.parquet"
            self._cache_columns(table_name, columns_to_fetch, source_path,
                                local_path, value_per_column = value_per_column)

    def materialize_cache_from_metadata(self, table_paths: Dict[str, str]):
        """Based on what columns are cached per the metadata table, copy those
        columns for real from the source path to the local cache so that after
        this function runs, the real filesystem reflects what the metadata sees,
        including parquet files stored in the right paths and so on"""

        # duckdb scan for in_cache = TRUE
        # group by table_name, get list of columns per table
        # cache those columns specifically in a one-time read using the APIs
        # we've written already. Should be pretty easy, not on the "timed"
        # critical path

        results = self.conn.execute("""
            SELECT column_name, table_name
            FROM cached_columns
            WHERE in_cache = TRUE
        """).fetchall()

        collected_columns = {}
        for row in results:
            column_name, table_name = row
            if table_name not in collected_columns:
                collected_columns[table_name] = []
            collected_columns[table_name].append(column_name)


        columns_to_materialize = []
        for table_name, column_names in collected_columns.items():
            source_path = table_paths[table_name]
            # In local mode, resolve the source path relative to data_dir
            if self.local_mode:
                if not Path(source_path).is_absolute():
                    source_path = f"{self.data_dir}/{source_path}"
            columns_to_materialize.append((source_path, table_name, column_names))

        def helper(arg):
            (source_path, table_name, columns_to_fetch) = arg
            self._fetch_columns_parallel(source_path, table_name, columns_to_fetch)

        with ThreadPoolExecutor(max_workers = 4) as pool:
            for _ in  pool.map(helper, columns_to_materialize):
                pass

    def execute_query(
        self, 
        query: str, 
        table_paths: Dict[str, str],
        value = 0,
    ):
        """
        Execute a query, ensuring required columns are cached for all tables.
        
        Args:
            query: SQL query string
            table_paths: Dictionary mapping table names to their source paths, e.g.:
                        {'table1': 's3://bucket/table1.parquet', 'table2': 's3://bucket/table2.parquet'}
                        In local mode, paths can be relative to data_dir or absolute.
        
        Returns:
            Query results as a list of tuples
        """
        
        columns_for_table = self.get_columns_for_tables(query)
        num_relevant_columns = sum([len(cols) for cols in columns_for_table.values()])
        value_per_column = value / num_relevant_columns if (value > 0 and num_relevant_columns > 0 ) else 0

        # Validate that all tables in query have paths provided
        missing_tables = set(columns_for_table.keys()) - set(table_paths.keys())
        if missing_tables:
            raise ValueError(f"Missing source paths for tables: {missing_tables}. ")
        
        # Generate a list of (source path for data, table name, list of columns
        # referenced) to fetch. We put
        # them in a list to allow for copying in parallel
        arg_list = []
        for table_name in columns_for_table:
            source_path = table_paths[table_name]

            # In local mode, resolve the source path relative to data_dir
            if self.local_mode:
                if not Path(source_path).is_absolute():
                    source_path = f"{self.data_dir}/{source_path}"

            columns = list(columns_for_table[table_name])
            # if no columns specified, cache all columns for the table
            if columns is None:
                columns = list(self.schema_registry[table_name])
            arg_list.append((source_path, table_name, columns))



        table_path_mappings = {}
        for table_name in columns_for_table:
            local_path = os.path.join(self.tables_dir, table_name, "*.parquet")
            table_path_mappings[table_name] = local_path

        self.ensure_columns_cached(arg_list, value_per_column = value_per_column)
        modified_query = self.rewrite_query(query, table_path_mappings)
        # print(query)
        # print("================================")
        # print(modified_query)
        return self.conn.execute(modified_query).fetchall()

    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache."""
        row = self.conn.execute("""
            SELECT 
                COUNT(*) as total_columns,
                SUM(size_bytes) as total_size,
                COUNT(DISTINCT table_name) as total_tables
            FROM cached_columns
            WHERE in_cache = TRUE
        """).fetchone()
        
        return {
            'total_columns': row[0] or 0,
            'total_size_gb': (row[1] or 0) / (1024 ** 3) if row[1] else 0,
            'total_tables': row[2] or 0,
            'max_size_gb': self.max_cache_size_bytes / (1024 ** 3)
        }
    
    def clear_cache(self, table_name: Optional[str] = None, delete_files: bool = True):
        """
        Clear cache for a specific table or all tables.
        
        Args:
            table_name: If provided, clear only this table's cache
        """
        if table_name:
            rows = self.conn.execute(
                "SELECT local_path FROM cached_columns WHERE table_name = ?", 
                [table_name]
            ).fetchall()
            self.conn.execute(
                "UPDATE cached_columns SET in_cache = FALSE WHERE table_name = ?", 
                [table_name]
            )
        else:
            rows = self.conn.execute("SELECT local_path FROM cached_columns").fetchall()
            self.conn.execute("UPDATE cached_columns SET in_cache = FALSE")
        
        # Delete files
        if delete_files:
            for row in rows:
                path = Path(row[0])
                if path.exists():
                    path.unlink()


# Example usage
if __name__ == "__main__":
    os.makedirs("./metadata/cache", exist_ok=True)
    schema_file = "./metadata/tpcds_schema_registry.json"
    with open(schema_file, 'r') as f:
        schema_registry = json.load(f)

    table_paths = {}
    for table_name in schema_registry.keys():
        # table_paths[table_name] = f"/Users/tapansriv/tpc/tpcds/{table_name}.parquet"
        table_paths[table_name] = f"/Users/tapansriv/value_of_data/value-of-data-metric/spark-lineage-api/tpcds/parquet/{table_name}.parquet"
        # table_paths[table_name] = f"/mnt/data_10gb/tpcds/{table_name}.parquet"

    cache = ColumnCache(
        cache_dir="./metadata/cache",
        # cache_dir="/home/cc/column_cache/cache",
        max_cache_size_gb=10.0,
        local_mode=True,
        data_dir="/Users/tapansriv/value_of_data/value-of-data-metric/spark-lineage-api/tpcds/parquet",
        # data_dir="/mnt/data_10gb/tpcds",
        eviction_policy="lru",
        schema_file=schema_file
    )

    querydir = "../../test/example_queries/tpcds/"
    for i in range(1, 100):
        if i < 10: 
            key = f"0{i}.sql"
        else: 
            key = f"{i}.sql"
        f = open(querydir + key, 'r')
        query = f.read()
        f.close()
        print("===============================")
        print(key)
        result = cache.execute_query(
            query,
            table_paths
        )

    # Get cache statistics
    stats = cache.get_cache_stats()
    print(f"Cache stats: {stats}")
    # Clear cache
    cache.clear_cache()

