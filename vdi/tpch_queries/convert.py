import re

pattern = "'(\w+).parquet'"
repl = r"dfs.`tmp/\1.parquet` \1"

for i in range(23,39):
    with open(f"{i}.sql") as fin: 
        with open(f"{i}_drill.sql", 'w') as fout:
            lines = fin.readlines() 
            for line in lines: 
                outline = re.sub(pattern, repl, line)
                fout.write(outline)

prefix = {
        "c_": "customer",
        "l_": "lineitem",
        "n_": "nation",
        "o_": "orders",
        "p_": "part",
        "ps_": "partsupp",
        "r_": "region",
        "s_": "supplier",
}

f = open("../oracle/data/column_names.csv")
columns = [x.strip() for x in f.readlines()]

for i in range(23,39):
    with open(f"{i}_drill.sql") as fin: 
        with open(f"{i}_drill2.sql", 'w') as fout:
            qry = fin.read()
            out = qry 
            for col in columns: 
                pattern = col
                sw = [prefix[p] for p in prefix if col.startswith(p)]
                assert len(sw) == 1, f"{sw}, {col}"
                repl = f"{sw[0]}.{col}"
                out = re.sub(pattern, repl, out)
            fout.write(out)


