# Example SQL Queries for Testing

This directory contains example SQL queries to test the query parsing functionality.

## Usage

Run the test script with any of these query files:

```bash
# Parse all tables in the query
python ../test_query_parser.py simple_query.sql

# Parse for a specific table
python ../test_query_parser.py query_with_alias.sql users
```

## Query Files

- **simple_query.sql**: Basic SELECT query with WHERE and LIMIT
- **query_with_alias.sql**: Query with table aliases and JOIN
- **query_with_cte.sql**: Query with WITH clause (Common Table Expressions)
- **complex_query.sql**: Complex query with multiple CTEs, JOINs, and aggregations

## Creating Your Own Test Query

1. Create a new `.sql` file in this directory
2. Write your SQL query
3. Run: `python ../test_query_parser.py your_query.sql [table_name]`

The parser will output:
- Which columns are needed for each table
- Table-to-column mapping
- Results saved to `your_query_parsed.txt`

