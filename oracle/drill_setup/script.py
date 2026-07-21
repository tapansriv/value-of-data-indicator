import duckdb

qry1 = "CREATE TABLE lineitem AS SELECT * FROM 'lineitem.parquet'"
qry2 = "ALTER TABLE lineitem ALTER L_QUANTITY TYPE DOUBLE"
qry3 = "ALTER TABLE lineitem ALTER L_EXTENDEDPRICE TYPE DOUBLE"
qry4 = "ALTER TABLE lineitem ALTER L_DISCOUNT TYPE DOUBLE"
qry5 = "ALTER TABLE lineitem ALTER L_TAX TYPE DOUBLE"
qry6 = "COPY lineitem TO 'lineitem2.parquet' (FORMAT parquet)"



con = duckdb.connect('hi')

print("reading in ")
con.execute(qry1)
print("altering quantity")
con.execute(qry2)
print("altering extendedprice")
con.execute(qry3)
print("altering discount")
con.execute(qry4)
print("altering tax")
con.execute(qry5)
print("copying back out")
con.execute(qry6)
print('done')

