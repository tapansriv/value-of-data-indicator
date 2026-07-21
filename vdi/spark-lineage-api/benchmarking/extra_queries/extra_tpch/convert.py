import re

pattern = "'(\w+).parquet'"
repl = r"\1"

for i in range(23, 39):
    f = open(f"{i}.sql")
    qry = "".join(f.readlines())
    outqry = re.sub(pattern, repl, qry)
    fout = open(f"spark/{i}.sql", 'w')
    fout.write(outqry)
    fout.close()
    f.close()





