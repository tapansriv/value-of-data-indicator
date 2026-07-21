import duckdb

columns = [x.upper() for x in ["l_quantity", "l_extendedprice", "l_discount",
                               "l_tax"]]



# Get column names
cols = duckdb.sql("DESCRIBE SELECT * FROM 'lineitem.parquet'").fetchall()
col_names = [col[0] for col in cols]

# Build SELECT part
select_clause = ',\n    '.join(
    f"{col}::DOUBLE AS {col}" if col in columns else col
    for col in col_names
)

# Final query
query = f"""
COPY (
    SELECT
        {select_clause}
    FROM 'lineitem.parquet'
) TO 'lineitem2.parquet' (FORMAT PARQUET)
"""
print(query)

duckdb.sql(query)


# qry = f'''
# COPY (
#   SELECT
#     *,  -- keep all columns
#     l_quantity::DOUBLE AS l_quantity,
#     l_extendedprice::DOUBLE AS l_extendedprice,
#     l_discount::DOUBLE AS l_discount,
#     l_tax::DOUBLE AS l_tax
#   FROM 'lineitem.parquet'
# ) TO 'lineitem2.parquet' (FORMAT PARQUET);
# '''
# duckdb.sql(qry)
