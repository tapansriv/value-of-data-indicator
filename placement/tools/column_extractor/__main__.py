"""
Demo: python -m tools.column_extractor "SELECT item.i_brand, ss.ss_ext_sales_price FROM item JOIN store_sales ss ON item.i_item_sk=ss.ss_item_sk"
"""
import sys
from .column_extractor import ColumnExtractor
if __name__ == "__main__":
    sql = " ".join(sys.argv[1:]) or "<no-sql-provided>"
    ce = ColumnExtractor()
    print(ce.extract_columns_per_table(sql))
