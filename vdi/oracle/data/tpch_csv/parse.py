f = open('foo')
out = open('column_names.csv', 'w')

lines = f.readlines()
for line in lines:
    vals = line.split(",")
    for v in vals:
        out.write(f"{v.lower()}\n")
