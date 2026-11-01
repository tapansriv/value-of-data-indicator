import sqlglot
from sqlglot import exp
import sys

filename = sys.argv[1]
with open(filename, 'r') as file:
    sql = file.read()

parsed = sqlglot.parse_one(sql, read="duckdb")
for table in parsed.find_all(exp.Table):
    print(table.parts)
    print(f"Table: {table.this}")
    print(f"Alias: {table.alias}")
    print(f"DB: {table.catalog}")

for column in parsed.find_all(exp.Column):
    print(column.parts)
