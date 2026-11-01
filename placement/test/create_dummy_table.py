#!/usr/bin/env python3
"""
Create a dummy table with 4 columns, split into separate parquet files.
Each column will be in its own parquet file to test column combination.
"""

import duckdb
from pathlib import Path

# Create output directory
output_dir = Path("test_data/dummy_table")
output_dir.mkdir(parents=True, exist_ok=True)

# Create a DuckDB connection
conn = duckdb.connect()

# Create a table with 4 columns and 30 rows
# Use unnest to convert the series to individual rows
conn.execute("""
    CREATE TABLE dummy_table AS
    SELECT 
        unnest(generate_series(1, 30)) AS id,
        'name_' || CAST(unnest(generate_series(1, 30)) AS VARCHAR) AS name,
        unnest(generate_series(100, 129)) AS value,
        (unnest(generate_series(1, 30))::DOUBLE * 1.5) AS score
""")

# Save each column as a separate parquet file
columns = ['id', 'name', 'value', 'score']

for col in columns:
    output_path = output_dir / f"{col}.parquet"
    query = f"""
    COPY (
        SELECT {col}
        FROM dummy_table
    ) TO '{output_path}' (FORMAT PARQUET)
    """
    conn.execute(query)
    print(f"Created {output_path}")

# Also create the full table for reference
full_table_path = output_dir / "full_table.parquet"
conn.execute(f"""
    COPY dummy_table TO '{full_table_path}' (FORMAT PARQUET)
""")
print(f"\nCreated full table at {full_table_path} for reference")

# Show what the data looks like
print("\nSample data from full table:")
result = conn.execute("SELECT * FROM dummy_table LIMIT 5").fetchall()
for row in result:
    print(row)

print(f"\nTotal rows: {conn.execute('SELECT COUNT(*) FROM dummy_table').fetchone()[0]}")

conn.close()
print(f"\nDone! Column files are in: {output_dir}")

