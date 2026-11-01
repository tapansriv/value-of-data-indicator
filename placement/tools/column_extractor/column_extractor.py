"""
ColumnExtractor prototype using sqlglot.

Goal:
- Parse SQL with sqlglot
- Return a mapping: table_name -> set(column_names) for columns explicitly referenced
  with a qualifier (table.column or alias.column).
- For unqualified columns, we attempt to map them conservatively:
    * If there's exactly one base table in the top-level FROM, map them to that table.
    * Else, put them under a special key None to indicate ambiguity.

Notes:
- This is a prototype to demonstrate using sqlglot to find exp.Column nodes.
- More advanced resolution can be added: using schema info, resolving aliases -> base tables, etc.
"""

from typing import Dict, Set, Optional
import sqlglot
from sqlglot import expressions as exp
import logging

logger = logging.getLogger("column_extractor")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class ColumnExtractor:
    def __init__(self, dialect: str = "duckdb"):
        self.dialect = dialect

    def _collect_top_level_tables(self, tree: exp.Expression) -> Dict[str, Optional[str]]:
        """
        Returns a mapping alias_or_table_name -> base_table_name (or None for derived/unknown).
        For a Table node, if it has an explicit alias, the key is the alias; otherwise the base table.
        Keys are returned in lower-case to ease matching with column qualifiers.
        """
        result = {}
        for table_node in tree.find_all(exp.Table):
            try:
                base = table_node.this
                base_name = base.this if isinstance(base, exp.Identifier) else str(base)
                print(base_name)
                alias_node = table_node.alias
                if alias_node and isinstance(alias_node.this, exp.Identifier):
                    alias = alias_node.this.this
                    result[alias.lower()] = base_name
                else:
                    print(base_name)
                    result[base_name.lower()] = base_name
            except Exception as e:
                print(e)
                continue
        return result

    def extract_columns_per_table(self, sql: str) -> Dict[Optional[str], Set[str]]:
        """
        Parse SQL and return {table_or_alias_or_None: set(columns)}.
        - If column is qualified with table/alias, we put it in that bucket (normalized lower-case).
        - If unqualified, and the top-level FROM has exactly one table, map it to that table;
          otherwise map unqualified columns under key None (ambiguous).
        """
        try:
            tree = sqlglot.parse_one(sql, read=self.dialect)
        except Exception as e:
            logger.warning(f"Failed to parse SQL: {e}. Returning empty mapping.")
            return {}

        tables = self._collect_top_level_tables(tree)  # alias_or_base -> base_table
        print(tables)

        # set for clarified columns
        mapping: Dict[Optional[str], Set[str]] = {}

        # collect all Column nodes
        for col in tree.find_all(exp.Column):
            try:
                # col parts: table (maybe None), column name (Identifier)
                table_part = None
                if col.table:
                    # table can be Identifier, or a more complex expression
                    if isinstance(col.table, exp.Identifier):
                        table_part = col.table.this.lower()
                    else:
                        table_part = str(col.table).lower()
                column_name = None
                # column name might be in col.name or col.this
                if hasattr(col, "name") and col.name:
                    column_name = col.name
                elif isinstance(col.this, exp.Identifier):
                    column_name = col.this.this
                else:
                    column_name = str(col.this)

                column_name = str(column_name)

                if table_part:
                    mapping.setdefault(table_part, set()).add(column_name)
                else:
                    # unqualified column; resolve if exactly one top-level table
                    if len(tables) == 1:
                        sole = next(iter(tables.keys()))
                        mapping.setdefault(sole, set()).add(column_name)
                    else:
                        mapping.setdefault(None, set()).add(column_name)
            except Exception:
                continue

        # Normalize mapping keys: convert None stays None, others lowercase
        normalized = {}
        for k, v in mapping.items():
            if k is None:
                normalized[None] = v
            else:
                normalized[k.lower()] = v

        return normalized


# Quick demo function:
def demo_extract(sql: str):
    ce = ColumnExtractor()
    return ce.extract_columns_per_table(sql)

f = open("../../test/example_queries/tpcds/03.sql")
sql = f.read()
print(demo_extract(sql))



