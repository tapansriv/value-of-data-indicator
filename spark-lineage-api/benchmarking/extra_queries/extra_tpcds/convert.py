import re

pattern = "'(\w+).parquet'"
repl = r"\1"

for i in range(100, 132):
    f = open(f"{i}.sql")
    qry = "".join(f.readlines())
    outqry = re.sub(pattern, repl, qry)
    fout = open(f"spark/query{i}.sql", 'w')
    fout.write(outqry)
    fout.close()
    f.close()





