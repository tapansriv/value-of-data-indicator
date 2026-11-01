"""Parse the TPC-DS DDL (tools/tpcds.sql) into Spark schemas.

Type mapping: integer->IntegerType, bigint->LongType, decimal(p,s)->DecimalType(p,s),
date->DateType, char/varchar->StringType, time->StringType.
"""
import re

DDL = "/home/cc/DSGen-software-code-4.0.0/tools/tpcds.sql"

TABLES = [
    "call_center", "catalog_page", "catalog_returns", "catalog_sales", "customer",
    "customer_address", "customer_demographics", "date_dim", "household_demographics",
    "income_band", "inventory", "item", "promotion", "reason", "ship_mode", "store",
    "store_returns", "store_sales", "time_dim", "warehouse", "web_page", "web_returns",
    "web_sales", "web_site",
]


def parse_ddl(path=DDL):
    """Return {table: [(col, sqltype_lower), ...]} in DDL column order."""
    text = open(path).read()
    out = {}
    for m in re.finditer(r"create table (\w+)\s*\((.*?)\n\);", text, re.S):
        name, body = m.group(1), m.group(2)
        cols = []
        for line in body.splitlines():
            line = line.strip().rstrip(",").strip()
            if not line or line.startswith("primary key"):
                continue
            cm = re.match(r"(\w+)\s+(\w+(?:\s*\(\s*\d+\s*(?:,\s*\d+\s*)?\))?)", line)
            if not cm:
                raise ValueError(f"cannot parse column line in {name}: {line!r}")
            cols.append((cm.group(1), re.sub(r"\s+", "", cm.group(2).lower())))
        out[name] = cols
    return out


def spark_type(sqltype):
    from pyspark.sql import types as T
    if sqltype == "integer":
        return T.IntegerType()
    if sqltype == "bigint":
        return T.LongType()
    m = re.fullmatch(r"decimal\((\d+),(\d+)\)", sqltype)
    if m:
        return T.DecimalType(int(m.group(1)), int(m.group(2)))
    if sqltype == "date":
        return T.DateType()
    if sqltype == "time" or sqltype.startswith("char") or sqltype.startswith("varchar"):
        return T.StringType()
    raise ValueError(f"unmapped type {sqltype}")


TRAILING = "__trailing_delim"


def read_schema(table, ddl=None):
    """Schema for reading raw .dat: DDL columns + one extra string column for the trailing '|'."""
    from pyspark.sql import types as T
    ddl = ddl or parse_ddl()
    fields = [T.StructField(c, spark_type(t), True) for c, t in ddl[table]]
    fields.append(T.StructField(TRAILING, T.StringType(), True))
    return T.StructType(fields)


if __name__ == "__main__":
    d = parse_ddl()
    missing = [t for t in TABLES if t not in d]
    assert not missing, missing
    for t in TABLES:
        print(t, len(d[t]), sorted(set(x for _, x in d[t])))
