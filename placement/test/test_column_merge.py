#!/usr/bin/env python3
"""
Test script to demonstrate querying separate column parquet files.
This helps understand the overhead of merging vs. using DuckDB's native combination.
"""

import duckdb
from pathlib import Path
import time

# Paths to the separate column files
base_dir = Path("test_data/dummy_table")
col_files = {
    'id': base_dir / "id.parquet",
    'name': base_dir / "name.parquet",
    'value': base_dir / "value.parquet",
    'score': base_dir / "score.parquet"
}

# Full table for comparison
full_table = base_dir / "full_table.parquet"

conn = duckdb.connect()

print("=" * 60)
print("Test 1: Query from separate column files (no merging)")
print("=" * 60)

# Method 1: Use DuckDB to combine columns on-the-fly
# This reads all column files and combines them without creating a merged file
start = time.time()
query1 = f"""
SELECT id, name, value, score
FROM (
    SELECT id FROM read_parquet('{col_files['id']}') AS t1
    JOIN (SELECT name FROM read_parquet('{col_files['name']}') AS t2) USING (rowid)
    JOIN (SELECT value FROM read_parquet('{col_files['value']}') AS t3) USING (rowid)
    JOIN (SELECT score FROM read_parquet('{col_files['score']}') AS t4) USING (rowid)
)
"""
# Actually, DuckDB can do this more elegantly - let me try a better approach
query1_better = f"""
SELECT 
    t1.id,
    t2.name,
    t3.value,
    t4.score
FROM read_parquet('{col_files['id']}') t1
JOIN read_parquet('{col_files['name']}') t2 ON t1.rowid = t2.rowid
JOIN read_parquet('{col_files['value']}') t3 ON t1.rowid = t3.rowid
JOIN read_parquet('{col_files['score']}') t4 ON t1.rowid = t4.rowid
"""

try:
    result1 = conn.execute(query1_better).fetchall()
    elapsed1 = time.time() - start
    print(f"Query executed in {elapsed1:.4f} seconds")
    print(f"Rows returned: {len(result1)}")
    print("First 5 rows:")
    for row in result1[:5]:
        print(f"  {row}")
except Exception as e:
    print(f"Error with JOIN approach: {e}")
    print("\nTrying alternative: Create a view that combines columns")
    # Alternative: Use a CTE or view
    query1_alt = f"""
    WITH 
        ids AS (SELECT unnest(id) AS id, rowid FROM read_parquet('{col_files['id']}')),
        names AS (SELECT unnest(name) AS name, rowid FROM read_parquet('{col_files['name']}')),
        values AS (SELECT unnest(value) AS value, rowid FROM read_parquet('{col_files['value']}')),
        scores AS (SELECT unnest(score) AS score, rowid FROM read_parquet('{col_files['score']}'))
    SELECT ids.id, names.name, values.value, scores.score
    FROM ids
    JOIN names ON ids.rowid = names.rowid
    JOIN values ON ids.rowid = values.rowid
    JOIN scores ON ids.rowid = scores.rowid
    """
    try:
        result1 = conn.execute(query1_alt).fetchall()
        elapsed1 = time.time() - start
        print(f"Query executed in {elapsed1:.4f} seconds")
        print(f"Rows returned: {len(result1)}")
        print("First 5 rows:")
        for row in result1[:5]:
            print(f"  {row}")
    except Exception as e2:
        print(f"Error with CTE approach: {e2}")

print("\n" + "=" * 60)
print("Test 2: Query from merged/combined file")
print("=" * 60)

# Method 2: Merge columns into a single file first, then query
start = time.time()
merged_file = base_dir / "merged_table.parquet"

# Create merged file
merge_query = f"""
COPY (
    SELECT 
        t1.id,
        t2.name,
        t3.value,
        t4.score
    FROM read_parquet('{col_files['id']}') t1
    JOIN read_parquet('{col_files['name']}') t2 ON t1.rowid = t2.rowid
    JOIN read_parquet('{col_files['value']}') t3 ON t1.rowid = t3.rowid
    JOIN read_parquet('{col_files['score']}') t4 ON t1.rowid = t4.rowid
) TO '{merged_file}' (FORMAT PARQUET)
"""
try:
    conn.execute(merge_query)
    merge_time = time.time() - start
    print(f"Merged file created in {merge_time:.4f} seconds")
    print(f"Merged file size: {merged_file.stat().st_size / 1024:.2f} KB")
    
    # Now query from merged file
    start2 = time.time()
    query2 = f"SELECT id, name, value, score FROM read_parquet('{merged_file}')"
    result2 = conn.execute(query2).fetchall()
    query_time = time.time() - start2
    print(f"Query from merged file executed in {query_time:.4f} seconds")
    print(f"Rows returned: {len(result2)}")
    print("First 5 rows:")
    for row in result2[:5]:
        print(f"  {row}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
print("Test 3: Query from original full table (baseline)")
print("=" * 60)

start = time.time()
query3 = f"SELECT id, name, value, score FROM read_parquet('{full_table}')"
result3 = conn.execute(query3).fetchall()
elapsed3 = time.time() - start
print(f"Query executed in {elapsed3:.4f} seconds")
print(f"Rows returned: {len(result3)}")
print("First 5 rows:")
for row in result3[:5]:
    print(f"  {row}")

print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
print("This demonstrates:")
print("1. DuckDB can combine columns from separate files on-the-fly")
print("2. Merging creates a single file but has upfront cost")
print("3. For small datasets, the difference may be negligible")
print("4. For large datasets, merging may be worth it for repeated queries")

conn.close()

