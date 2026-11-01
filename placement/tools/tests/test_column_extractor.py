import unittest
from tools.column_extractor.column_extractor import ColumnExtractor

class TestColumnExtractor(unittest.TestCase):
    def test_extract(self):
        sql = "SELECT dt.d_year, item.i_brand_id, ss.ss_ext_sales_price FROM date_dim dt JOIN store_sales ss ON dt.d_date_sk = ss.ss_sold_date_sk JOIN item ON ss.ss_item_sk = item.i_item_sk"
        ce = ColumnExtractor()
        cols = ce.extract_columns_per_table(sql)
        # Expect keys: dt, ss, item or base table names
        self.assertIn('dt', cols or {})
        self.assertIn('ss', cols or {})
        # the columns should be found
        self.assertIn('d_year', set().union(*cols.values()))
        self.assertIn('ss_ext_sales_price', set().union(*cols.values()))

if __name__ == "__main__":
    unittest.main()
