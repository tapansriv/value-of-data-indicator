#!/usr/bin/env python3
""" Schema Parser for TPCDS Schema Files

Parses CREATE TABLE statements from schema files and creates a mapping
of table names to their column names.
"""

import re
from pathlib import Path
from typing import Dict, Set
import json


def parse_schema_file(schema_file: Path) -> Dict[str, Set[str]]:
    """
    Parse a schema file and extract table names and columns.
    Handles both single-table files and multi-table files.
    
    Args:
        schema_file: Path to the schema file
        
    Returns:
        Dictionary mapping table names to sets of column names
    """
    content = schema_file.read_text()
    
    # Find all CREATE TABLE statements in the file
    all_schemas = {}
    
    # Pattern to find CREATE TABLE statements
    create_table_pattern = r'create\s+table\s+(\w+)\s*\('
    
    # Find all table definitions
    for match in re.finditer(create_table_pattern, content, re.IGNORECASE):
        table_name = match.group(1)
        table_start = match.start()
        
        # Find the opening parenthesis
        paren_start = content.find('(', table_start)
        if paren_start == -1:
            continue
        
        # Find matching closing parenthesis
        depth = 0
        paren_end = -1
        for i in range(paren_start, len(content)):
            if content[i] == '(':
                depth += 1
            elif content[i] == ')':
                depth -= 1
                if depth == 0:
                    paren_end = i
                    break
        
        if paren_end == -1:
            continue
        
        columns_block = content[paren_start + 1:paren_end]
        columns = set()
        
        # Split by comma, but handle nested parentheses (for complex types)
        column_defs = []
        depth = 0
        current = []
        in_string = False
        string_char = None
        
        for i, char in enumerate(columns_block):
            # Handle string literals
            if char in ("'", '"') and (i == 0 or columns_block[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
                current.append(char)
            elif not in_string:
                if char == '(':
                    depth += 1
                    current.append(char)
                elif char == ')':
                    depth -= 1
                    current.append(char)
                elif char == ',' and depth == 0:
                    col_def = ''.join(current).strip()
                    if col_def:
                        column_defs.append(col_def)
                    current = []
                else:
                    current.append(char)
            else:
                current.append(char)
        
        if current:
            col_def = ''.join(current).strip()
            if col_def:
                column_defs.append(col_def)
        
        # Extract column names (first identifier before type)
        for col_def in column_defs:
            col_def = col_def.strip()
            if not col_def:
                continue
            
            # Skip PRIMARY KEY constraints and other non-column definitions
            if col_def.upper().startswith('PRIMARY KEY'):
                continue
            
            # Column name is the first word (before the type)
            # Handle cases like "col_name type" or "col_name type constraint"
            # Also handle tabs and newlines
            col_def = re.sub(r'\s+', ' ', col_def)
            col_match = re.match(r'^(\w+)', col_def)
            if col_match:
                col_name = col_match.group(1)
                columns.add(col_name)
        
        if columns:
            all_schemas[table_name] = columns
    
    return all_schemas


def parse_all_schemas(schema_dir: Path) -> Dict[str, Set[str]]:
    """
    Parse all schema files in a directory.
    
    Args:
        schema_dir: Directory containing schema files
        
    Returns:
        Dictionary mapping table names to sets of column names
    """
    all_schemas = {}
    
    # Find all .sql files in the directory
    schema_files = sorted(schema_dir.glob("*.sql"))
    
    for schema_file in schema_files:
        schemas = parse_schema_file(schema_file)
        all_schemas.update(schemas)
        print(f"Parsed {schema_file.name}: {len(schemas.get(list(schemas.keys())[0], set()))} columns")
    
    return all_schemas

def save_schema_registry(schemas: Dict[str, Set[str]], output_file: Path):
    """
    Save schema registry to a JSON file.
    
    Args:
        schemas: Dictionary mapping table names to column sets
        output_file: Path to output JSON file
    """
    # Convert sets to lists for JSON serialization
    schemas_json = {table: sorted(columns) for table, columns in schemas.items()}
    
    with open(output_file, 'w') as f:
        json.dump(schemas_json, f, indent=2)
    
    print(f"\nSchema registry saved to: {output_file}")
    print(f"Total tables: {len(schemas)}")
    print(f"Total columns: {sum(len(cols) for cols in schemas.values())}")

def parse_schema(dataset="tpcds", schema_path=None, output_path="schema_registry.json"):
    if not schema_path and dataset not in ["tpch", "tpcds"]:
        raise ValueError("Either schema_path must be provided or dataset must be 'tpch' or 'tpcds'.")

    if not schema_path:
        if dataset == "tpch":
            schema_path = "tpch/tpch.sql"
            output_path = "tpch_schema_registry.json"
        else:  # TPCDS
            schema_path = "tpcds"
            output_path = "tpcds_schema_registry.json"

    sp = Path(schema_path)
    output_file = Path(output_path)
    if not sp.exists:
        print(f"Error: Provided schema path '{schema_path}' does not exist.")
        return

    if sp.is_dir():
        print(f"Parsing {dataset} schema files...")
        print("=" * 70)
        
        schemas = parse_all_schemas(sp)
        if schemas:
            save_schema_registry(schemas, output_file)
        else:
            print("No schemas found.")
    else:
        print(f"Parsing {dataset} schema file...")
        print("=" * 70)
        
        schemas = parse_schema_file(sp)
        
        if schemas:
            save_schema_registry(schemas, output_file)
        else:
            print("No schemas found.")

if __name__ == '__main__':
    parse_schema(output_path="tpcds_schema_registry.json")
