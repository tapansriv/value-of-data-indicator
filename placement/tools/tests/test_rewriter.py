import unittest
from tools.query_rewriter.rewriter import QueryRewriter

class TestRewriter(unittest.TestCase):
    def test_basic_rewrite(self):
        sql = """
        SELECT dt.d_year, item.i_brand, sum(ss.ss_ext_sales_price) sum_agg
        FROM date_dim dt, store_sales ss, item
        WHERE dt.d_date_sk = ss.ss_sold_date_sk
          AND ss.ss_item_sk = item.i_item_sk
        GROUP BY dt.d_year, item.i_brand
        """
        mapping = {
            "date_dim": "/tmp/cache/date_dim.parquet",
            "store_sales": "/tmp/cache/store_sales.parquet",
            "item": "/tmp/cache/item.parquet",
        }
        r = QueryRewriter()
        modified = r.rewrite_query(sql, mapping)
        # Basic assertions: read_parquet must appear for each mapped table
        self.assertIn("read_parquet('/tmp/cache/date_dim.parquet')", modified)
        self.assertIn("read_parquet('/tmp/cache/store_sales.parquet')", modified)
        self.assertIn("read_parquet('/tmp/cache/item.parquet')", modified)
        # aliases present
        self.assertIn(" AS dt", modified) or self.assertIn(" dt", modified)

if __name__ == "__main__":
    unittest.main()
