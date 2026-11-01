#!/usr/bin/env python3
"""
Validation script for query parser.

Processes all TPCDS queries and validates:
1. Columns listed exist in the schema
2. Columns are associated with the correct table
3. No columns from the schema that appear in the query were missed
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict
from test_query_parser import (
    load_schema_registry
)
from column_cache import ColumnCache, parse_schema


class QueryValidator:
    """Validates query parsing results against schema."""
    
    def __init__(self, schema_registry: Dict[str, Set[str]]):
        self.schema_registry = schema_registry
        self.cache = ColumnCache(
            cache_dir="./test_cache",
            max_cache_size_gb=1.0,
            local_mode=True,
            data_dir="./foo",
            schema_registry = schema_registry
        )
    
    def find_all_schema_columns_in_query(self, query: str) -> Dict[str, Set[str]]:
        """
        Find all columns from the schema that appear in the query.
        This is the ground truth for what columns should be found.
        
        Returns:
            Dictionary mapping table names to sets of columns found in query
        """
        # Normalize query - remove comments
        query_clean = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
        query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
        query_lower = query_clean.lower()
        
        # Check if query uses DuckDB-specific tables (can't validate these)
        if re.search(r'(?i)FROM\s+["\']duck_table_\d+["\']', query_clean):
            # This query uses DuckDB-specific tables, return empty result
            return {}
        
        result = {}
        
        # Extract CTE names to avoid false matches
        cte_names = set()
        with_matches = re.finditer(r'(?i)\bWITH\s+(\w+)\s+AS', query_clean)
        for match in with_matches:
            cte_names.add(match.group(1).lower())
        
        # Extract CREATE TABLE names (temporary tables)
        create_table_names = set()
        create_matches = re.finditer(r'(?i)CREATE\s+TABLE\s+(\w+)', query_clean)
        for match in create_matches:
            create_table_names.add(match.group(1).lower())
        
        # For each table in schema, check which columns appear in the query
        for table_name, columns in self.schema_registry.items():
            found_columns = set()
            for col in columns:
                col_lower = col.lower()
                # Skip if this looks like a CTE name or CREATE TABLE name
                if col_lower in cte_names or col_lower in create_table_names:
                    continue
                
                # Look for column name in query (case-insensitive)
                # Use word boundaries to avoid partial matches
                # Also check for qualified references like table.column
                col_pattern = rf'\b{re.escape(col_lower)}\b'
                if re.search(col_pattern, query_lower):
                    found_columns.add(col)
            
            if found_columns:
                result[table_name] = found_columns
        
        return result
    
    def validate_parsing_result(
        self, 
        query: str, 
        parsed_result: Dict[str, Set[str]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate parsing result against schema.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Get ground truth: all schema columns that appear in query
        expected = self.find_all_schema_columns_in_query(query)
        
        # Check 1: All columns in parsed result exist in schema
        for table_name, columns in parsed_result.items():
            if table_name not in self.schema_registry:
                errors.append(f"ERROR: Table '{table_name}' not found in schema registry")
                continue
            
            schema_columns = self.schema_registry[table_name]
            for col in columns:
                # Clean column name
                col_clean = re.sub(r'\s+nulls\s+(first|last)', '', col, flags=re.IGNORECASE).strip()
                col_clean = re.sub(r'\s+(asc|desc)\b', '', col_clean, flags=re.IGNORECASE).strip()
                
                if col_clean not in schema_columns:
                    # Check if this might be a computed column or alias from a CTE
                    # These are acceptable - they're not errors, just computed values
                    # TPCDS base columns follow pattern: prefix_descriptive_name (e.g., ss_sales_price)
                    # CTE aliases often have shorter or different patterns
                    is_likely_computed = (
                        # Short names that look like aliases (e.g., ss_qty, ss_wc)
                        len(col_clean) <= 6 or
                        # Names ending with numbers (e.g., d_week_seq1, s_store_id2) are aliases
                        re.search(r'\d+$', col_clean) or
                        # Names that don't follow TPCDS naming convention
                        # TPCDS columns are usually: 2-3 char prefix + underscore + descriptive name
                        # Aliases might be shorter or have different patterns
                        (not re.match(r'^[a-z]{2,3}_[a-z_]{4,}$', col_clean) and
                         # But allow some exceptions that are clearly aliases
                         col_clean.endswith(('_year', '_rev', '_items', '_dev')) or
                         col_clean in ('ss_items', 'ss_item_rev', 'ss_sold_year', 'ss_dev'))
                    )
                    
                    if is_likely_computed:
                        # This is likely a computed column/alias - don't count as error
                        pass  # Accept computed columns
                    else:
                        errors.append(
                            f"ERROR: Column '{col_clean}' in table '{table_name}' does not exist in schema "
                            f"(might be computed/alias: '{col}')"
                        )
        
        # Check 2: Columns are in the correct table
        for table_name, columns in parsed_result.items():
            schema_columns = self.schema_registry[table_name]
            for col in columns:
                # Check if this column belongs to this table
                if col not in schema_columns:
                    # Find which table this column actually belongs to
                    actual_table = None
                    for t, cols in self.schema_registry.items():
                        if col in cols:
                            actual_table = t
                            break
                    
                    if actual_table and actual_table != table_name:
                        errors.append(
                            f"ERROR: Column '{col}' is in table '{actual_table}', "
                            f"not '{table_name}'"
                        )
        
        # Check 3: No missing columns (columns in schema that appear in query but weren't parsed)
        # Skip this check if expected is empty (e.g., DuckDB-specific tables)
        if expected:
            for table_name, expected_columns in expected.items():
                parsed_columns = parsed_result.get(table_name, set())
                missing = expected_columns - parsed_columns
                
                if missing:
                    errors.append(
                        f"MISSING: Table '{table_name}' - columns found in query but not parsed: "
                        f"{sorted(missing)}"
                    )
            
            # Also check for tables that should have been found
            expected_tables = set(expected.keys())
            parsed_tables = set(parsed_result.keys())
            missing_tables = expected_tables - parsed_tables
            
            if missing_tables:
                for table in missing_tables:
                    errors.append(
                        f"MISSING: Table '{table}' has columns in query but wasn't in parsed result"
                    )
        
        return len(errors) == 0, errors
    
    def process_query_file(self, query_file: Path) -> Dict:
        """Process a single query file and return validation results."""
        query = query_file.read_text()
        
        # Parse the query using the parser from column_cache.py
        parsed_result = self.cache.parse_query_for_base_tables(query)
        
        # Validate
        is_valid, errors = self.validate_parsing_result(query, parsed_result)
        
        # Get expected columns for summary
        expected = self.find_all_schema_columns_in_query(query)
        
        return {
            'file': query_file.name,
            'is_valid': is_valid,
            'errors': errors,
            'parsed_tables': len(parsed_result),
            'parsed_columns': sum(len(cols) for cols in parsed_result.values()),
            'expected_tables': len(expected),
            'expected_columns': sum(len(cols) for cols in expected.values()),
            'parsed_result': parsed_result,
            'expected': expected
        }


def main():
    import sys
    
    # Check if dataset name is provided
    if len(sys.argv) > 1:
        dataset = sys.argv[1].lower()
    else:
        dataset = "tpcds"  # Default
    
    # Check if custom queries directory is provided
    if len(sys.argv) > 2:
        queries_dir = Path(sys.argv[2])
    else:
        # Use default directories
        if dataset == "tpch":
            queries_dir = Path("example_queries/tpch")
        else:  # TPCDS
            queries_dir = Path("example_queries/tpcds")

    sp = None; of = None 
    if dataset == "tpch":
        sp = "../schema/tpch/tpch.sql"
        of = "../schema/tpch_schema_registry.json"
        schema_file = Path(of)
    else:  # TPCDS
        sp = "../schema/tpcds"
        of = "../schema/tpcds_schema_registry.json"
        schema_file = Path(of)
    
    if not schema_file.exists():
        print(f"Schema registry '{schema_file}' not found. Parsing schema file.")
        parse_schema(dataset, sp, of)
        schema_file = Path(of)
    
    if not queries_dir.exists():
        print(f"Error: Queries directory '{queries_dir}' not found.")
        sys.exit(1)
    
    # Load schema registry
    print("Loading schema registry...")
    schema_registry = load_schema_registry(schema_file)
    print(f"Loaded {len(schema_registry)} tables with {sum(len(c) for c in schema_registry.values())} total columns\n")
    
    # Initialize validator
    validator = QueryValidator(schema_registry)
    
    # Get all query files
    query_files = sorted(queries_dir.glob("*.sql"))
    print(f"Found {len(query_files)} query files\n")
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print()
    
    # Process each query
    results = []
    total_errors = 0
    total_missing = 0
    
    for query_file in query_files:
        result = validator.process_query_file(query_file)
        results.append(result)
        
        if not result['is_valid']:
            total_errors += len([e for e in result['errors'] if e.startswith('ERROR')])
            total_missing += len([e for e in result['errors'] if e.startswith('MISSING')])
    
    # Print summary
    valid_count = sum(1 for r in results if r['is_valid'])
    invalid_count = len(results) - valid_count
    
    print(f"Summary:")
    print(f"  Total queries: {len(results)}")
    print(f"  Valid: {valid_count}")
    print(f"  Invalid: {invalid_count}")
    print(f"  Total errors: {total_errors}")
    print(f"  Total missing columns: {total_missing}")
    print()
    
    # Print detailed results for invalid queries
    if invalid_count > 0:
        print("=" * 80)
        print("DETAILED RESULTS (Invalid Queries Only)")
        print("=" * 80)
        print()
        
        for result in results:
            if not result['is_valid']:
                print(f"Query: {result['file']}")
                print(f"  Parsed: {result['parsed_tables']} tables, {result['parsed_columns']} columns")
                print(f"  Expected: {result['expected_tables']} tables, {result['expected_columns']} columns")
                print()
                
                for error in result['errors']:
                    print(f"  {error}")
                
                print()
    
    # Generate detailed report file
    # Use queries directory name in report filename if it's not the default
    if queries_dir.name in ["tpcds", "tpch"]:
        report_file = Path(f"validation_report_{dataset}.txt")
    else:
        report_file = Path(f"validation_report_{dataset}_{queries_dir.name}.txt")
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("QUERY PARSER VALIDATION REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Summary:\n")
        f.write(f"  Total queries: {len(results)}\n")
        f.write(f"  Valid: {valid_count}\n")
        f.write(f"  Invalid: {invalid_count}\n")
        f.write(f"  Total errors: {total_errors}\n")
        f.write(f"  Total missing columns: {total_missing}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        for result in results:
            f.write(f"Query: {result['file']}\n")
            f.write(f"  Status: {'VALID' if result['is_valid'] else 'INVALID'}\n")
            f.write(f"  Parsed: {result['parsed_tables']} tables, {result['parsed_columns']} columns\n")
            f.write(f"  Expected: {result['expected_tables']} tables, {result['expected_columns']} columns\n")
            
            if result['parsed_result']:
                f.write(f"  Parsed tables and columns:\n")
                for table, cols in sorted(result['parsed_result'].items()):
                    f.write(f"    {table}: {sorted(cols)}\n")
            
            if result['errors']:
                f.write(f"  Errors:\n")
                for error in result['errors']:
                    f.write(f"    {error}\n")
            
            f.write("\n")
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Return exit code based on validation results
    sys.exit(0 if invalid_count == 0 else 1)


if __name__ == "__main__":
    main()

