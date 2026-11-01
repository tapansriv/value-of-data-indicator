#!/usr/bin/env python3
"""
Test script for query parsing functionality.

Usage:
    python test_query_parser.py <query_file> [table_name]
    
    If table_name is not provided, the script will attempt to extract
    all table names from the query and show columns for each.
    
    The parser now uses the schema registry to map columns to their
    base tables, avoiding incorrect associations with CTEs.
"""

import sys
import re
import json
from pathlib import Path
from typing import Dict, Set, Optional
from column_cache import ColumnCache


def load_schema_registry(schema_file: Path = Path("schema/tpcds_schema_registry.json")) -> Dict[str, Set[str]]:
    """
    Load the schema registry from JSON file.
    
    Returns:
        Dictionary mapping table names to sets of column names
    """
    if not schema_file.exists():
        print(f"Warning: Schema registry '{schema_file}' not found. Column-to-table mapping may be inaccurate.")
        return {}
    
    with open(schema_file, 'r') as f:
        schemas_json = json.load(f)
    
    # Convert lists back to sets
    return {table: set(columns) for table, columns in schemas_json.items()}


def identify_column_table(column_name: str, schema_registry: Dict[str, Set[str]]) -> Optional[str]:
    """
    Identify which base table a column belongs to by looking it up in the schema registry.
    
    Returns:
        Table name if found, None otherwise
    """
    for table_name, columns in schema_registry.items():
        if column_name in columns:
            return table_name
    return None


# Deprecated: Use cache.extract_table_names() instead
def extract_table_names(query: str) -> Set[str]:
    """
    Extract table names from a SQL query.
    This is a simple heuristic - looks for table names in FROM and JOIN clauses.
    Also handles file paths like 'table.parquet' or "table.parquet".
    """
    tables = set()
    
    # Normalize query
    query = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    # Find FROM clauses with file paths (e.g., 'lineitem.parquet' or "lineitem.parquet")
    # Pattern: FROM 'filename.parquet' or FROM "filename.parquet"
    from_file_pattern = r"(?i)\bFROM\s+['\"]([^'\"]+)\.parquet['\"]"
    from_file_matches = re.findall(from_file_pattern, query)
    for match in from_file_matches:
        # Extract table name from file path
        table_name = match.split('/')[-1]  # Handle paths like 'path/to/table.parquet'
        tables.add(table_name)
    
    # Find FROM clauses with table names
    from_pattern = r'(?i)\bFROM\s+(\w+)(?:\s+AS\s+\w+)?(?:\s|,|JOIN|WHERE|GROUP|ORDER|LIMIT|$)'
    from_matches = re.findall(from_pattern, query)
    tables.update(from_matches)
    
    # Find JOIN clauses with file paths
    join_file_pattern = r"(?i)\bJOIN\s+['\"]([^'\"]+)\.parquet['\"]"
    join_file_matches = re.findall(join_file_pattern, query)
    for match in join_file_matches:
        table_name = match.split('/')[-1]
        tables.add(table_name)
    
    # Find JOIN clauses with table names
    join_pattern = r'(?i)\bJOIN\s+(\w+)(?:\s+AS\s+\w+)?(?:\s|ON|WHERE|GROUP|ORDER|LIMIT|$)'
    join_matches = re.findall(join_pattern, query)
    tables.update(join_matches)
    
    # Also handle comma-separated file paths in FROM clause
    # Pattern: FROM 'file1.parquet', 'file2.parquet'
    # This will also catch file paths in subqueries (EXCEPT, UNION, etc.)
    from_comma_pattern = r"['\"]([^'\"]+)\.parquet['\"]"
    comma_matches = re.findall(from_comma_pattern, query)
    for match in comma_matches:
        table_name = match.split('/')[-1]
        tables.add(table_name)
    
    # Also extract file paths from subqueries in EXCEPT/UNION/INTERSECT
    # These might be in nested SELECT statements
    subquery_file_pattern = r"(?i)(?:SELECT|EXCEPT|UNION|INTERSECT).*?FROM\s+['\"]([^'\"]+)\.parquet['\"]"
    subquery_matches = re.findall(subquery_file_pattern, query, re.DOTALL)
    for match in subquery_matches:
        table_name = match.split('/')[-1]
        tables.add(table_name)
    
    # Handle CREATE TABLE statements that might reference tables
    # Pattern: CREATE TABLE ... FROM 'table.parquet'
    create_table_pattern = r"(?i)CREATE\s+TABLE\s+\w+\s+AS\s+.*?FROM\s+['\"]([^'\"]+)\.parquet['\"]"
    create_matches = re.findall(create_table_pattern, query, re.DOTALL)
    for match in create_matches:
        table_name = match.split('/')[-1]
        tables.add(table_name)
    
    # Also extract tables from subqueries in CREATE TABLE statements
    create_table_subquery_pattern = r"(?i)CREATE\s+TABLE\s+\w+\s+AS\s*\(.*?FROM\s+['\"]([^'\"]+)\.parquet['\"]"
    create_sub_matches = re.findall(create_table_subquery_pattern, query, re.DOTALL)
    for match in create_sub_matches:
        table_name = match.split('/')[-1]
        tables.add(table_name)
    
    # Remove common SQL keywords that might be caught
    sql_keywords = {
        'select', 'from', 'where', 'join', 'inner', 'left', 'right', 'full',
        'outer', 'on', 'group', 'by', 'order', 'having', 'limit', 'offset',
        'union', 'except', 'intersect', 'as', 'and', 'or', 'not', 'in', 'is',
        'null', 'like', 'between', 'exists', 'case', 'when', 'then', 'else', 'end'
    }
    tables = {t for t in tables if t.lower() not in sql_keywords}
    
    return tables


# Deprecated: Use cache.extract_all_column_references() instead
def extract_all_column_references(query: str) -> Set[str]:
    """
    Extract all column references from a query, including those in expressions.
    This is a more aggressive extraction that looks for column-like identifiers.
    """
    # Normalize query - remove CREATE TABLE statements for parsing (they're temporary)
    # But keep the SELECT parts
    query_clean = query
    # Remove CREATE TABLE ... AS statements but keep the SELECT part
    query_clean = re.sub(r'(?i)CREATE\s+TABLE\s+\w+\s+AS\s*\(', '(', query_clean)
    
    # Normalize query
    query_clean = re.sub(r'--.*?$', '', query_clean, flags=re.MULTILINE)
    query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
    
    columns = set()
    
    # Extract CTE names to filter them out
    cte_names = set()
    with_matches = re.finditer(r'(?i)\bWITH\s+(\w+)\s+AS', query_clean)
    for match in with_matches:
        cte_names.add(match.group(1).lower())
    
    # Also extract CREATE TABLE names (these are temporary tables)
    create_table_names = set()
    create_matches = re.finditer(r'(?i)CREATE\s+TABLE\s+(\w+)', query_clean)
    for match in create_matches:
        create_table_names.add(match.group(1).lower())
    
    # Extract DuckDB-specific table names (like "duck_table_37_0")
    duck_table_pattern = r'(?i)FROM\s+["\']duck_table_\d+["\']'
    has_duck_table = bool(re.search(duck_table_pattern, query_clean))
    
    # Find all identifiers that look like column names
    # Pattern: word characters, possibly qualified with table/alias
    # This will catch columns in SELECT, WHERE, expressions, etc.
    # Also handle quoted identifiers like "i_item_id"
    # Use a more comprehensive pattern that finds column-like identifiers anywhere
    # TPCDS columns follow pattern: prefix_rest (e.g., ss_sold_date_sk)
    col_pattern = r'\b([a-z][a-z0-9_]*_[a-z0-9_]+)\b'
    matches = re.findall(col_pattern, query_clean, re.IGNORECASE)
    
    # Filter out SQL keywords and common function names
    sql_keywords = {
        'select', 'from', 'where', 'join', 'inner', 'left', 'right', 'full',
        'outer', 'on', 'group', 'by', 'order', 'having', 'limit', 'offset',
        'union', 'except', 'intersect', 'as', 'and', 'or', 'not', 'in', 'is',
        'null', 'like', 'between', 'exists', 'case', 'when', 'then', 'else', 'end',
        'sum', 'count', 'avg', 'min', 'max', 'coalesce', 'rank', 'over', 'partition',
        'with', 'all', 'distinct', 'desc', 'asc', 'nulls', 'last', 'first',
        'interval', 'day', 'days', 'week', 'weeks', 'month', 'months', 'year', 'years'
    }
    
    for match in matches:
        col = match.lower()
        # Clean up column name - remove SQL clauses that might be attached
        # Remove things like "NULLS FIRST", "NULLS LAST", etc.
        col_clean = re.sub(r'\s+nulls\s+(first|last)', '', col, flags=re.IGNORECASE)
        col_clean = re.sub(r'\s+asc\b', '', col_clean, flags=re.IGNORECASE)
        col_clean = re.sub(r'\s+desc\b', '', col_clean, flags=re.IGNORECASE)
        col_clean = col_clean.strip()
        
        # Skip if it's a SQL keyword, CTE name, CREATE TABLE name, or too short
        if (col_clean not in sql_keywords and 
            col_clean not in cte_names and
            col_clean not in create_table_names and
            len(col_clean) > 2 and
            '_' in col_clean):  # TPCDS columns have underscores
            columns.add(col_clean)
    
    return columns


def parse_query_for_base_tables(query: str, cache: ColumnCache, schema_registry: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """
    Parse a query and extract columns mapped to their base tables.
    
    This function now delegates to cache.parse_query_for_base_tables() to ensure
    all parsing logic is in column_cache.py.
    
    Returns:
        Dictionary mapping base table names to sets of column names
    """
    return cache.parse_query_for_base_tables(query, schema_registry)


def format_output(results: Dict[str, Set[str]]) -> str:
    """
    Format the parsing results for display.
    Shows base tables and their columns (no CTEs).
    """
    output_lines = []
    output_lines.append("=" * 70)
    output_lines.append("QUERY PARSING RESULTS - BASE TABLES ONLY")
    output_lines.append("=" * 70)
    output_lines.append("")
    output_lines.append("Note: Columns are mapped to their base tables, not CTEs.")
    output_lines.append("")
    
    if not results:
        output_lines.append("No base tables found in query.")
    else:
        for table_name in sorted(results.keys()):
            columns = results[table_name]
            output_lines.append(f"Base Table: {table_name}")
            output_lines.append("-" * 70)
            
            if columns:
                sorted_columns = sorted(columns)
                output_lines.append(f"  Columns ({len(sorted_columns)}):")
                for col in sorted_columns:
                    output_lines.append(f"    - {col}")
            else:
                output_lines.append("  Columns: (none found)")
            
            output_lines.append("")
    
    output_lines.append("=" * 70)
    return "\n".join(output_lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_query_parser.py <query_file> [table_name]")
        print("\nExample:")
        print("  python test_query_parser.py query.sql")
        print("  python test_query_parser.py query.sql my_table")
        sys.exit(1)
    
    query_file = Path(sys.argv[1])
    if not query_file.exists():
        print(f"Error: File '{query_file}' not found.")
        sys.exit(1)
    
    # Read query from file
    query = query_file.read_text()
    
    # Load schema registry
    schema_registry = load_schema_registry()
    if schema_registry:
        print(f"Loaded schema registry: {len(schema_registry)} tables")
    print()
    
    # Initialize cache (we only need it for the parsing methods, not actual caching)
    cache = ColumnCache(
        cache_dir="./test_cache",
        max_cache_size_gb=1.0,
        s3_region="us-east-1"
    )
    
    # Parse query and map columns to base tables
    print("Parsing query and mapping columns to base tables...")
    print("=" * 70)
    print()
    
    if len(sys.argv) >= 3:
        # Specific table name provided - but we still map to base tables
        table_name = sys.argv[2]
        print(f"Note: Table '{table_name}' specified, but output shows base table mappings")
        print()
    
    # Use the parser from column_cache.py
    results = cache.parse_query_for_base_tables(query, schema_registry)
    
    # Display results
    output = format_output(results)
    print(output)
    
    # Also write to output file
    output_file = query_file.parent / f"{query_file.stem}_parsed.txt"
    output_file.write_text(output)
    print(f"\nResults also saved to: {output_file}")


if __name__ == "__main__":
    main()

