"""
QueryRewriter

Rewrites SQL queries so that tables referenced in the top-level FROM (and JOINs)
are replaced by read_parquet('/path/to/cached/table.parquet') AS <alias>

- Uses sqlglot to parse the SQL into an AST, so replacements are structure-aware.
- Skips rewriting for names introduced as CTEs.
- Preserves explicit aliases. If a table has no alias, uses the base table name as alias.
- Does not globally replace bare table name occurrences — only rewrites the table node itself.

Notes:
- Requires: sqlglot (pip install sqlglot)
- This module takes a mapping of base_table_name -> local_parquet_path. It will only
  rewrite tables that are present in that mapping.
"""

from typing import Dict, Set, Optional
import sqlglot
from sqlglot import expressions as exp
import logging

logger = logging.getLogger("query_rewriter")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class QueryRewriter:
    def __init__(self, dialect: str = "duckdb"):
        """
        dialect: passed to sqlglot.parse to help with parsing dialect specifics
        """
        self.dialect = dialect

    def _collect_cte_names(self, tree: exp.Expression) -> Set[str]:
        """
        Return the set of CTE names (WITH aliases) defined in the query AST.
        """
        ctes = set()
        with_node = tree.find(exp.With)
        if with_node:
            for cte in with_node.expressions:
                ctes.add(cte.alias.lower())
        return ctes

    def rewrite_query(
        self,
        sql: str,
        table_to_local_path: Dict[str, str]
    ) -> str:
        """
        Main entrypoint.

        Args:
            sql: SQL query string to rewrite
            table_to_local_path: mapping base_table_name -> local parquet path (string)
                base_table_name matching is case-insensitive.
            rewrite_subqueries: if False, will only rewrite tables in the top-level SELECT
                (safer in some contexts).

        Returns:
            modified SQL string (or original SQL if parse/rewrite fails)
        """
        try:
            tree = sqlglot.parse_one(sql, read=self.dialect)
        except Exception as e:
            logger.warning(f"Failed to parse SQL with sqlglot: {e}. Returning original SQL.")
            return sql

        # Collect CTE names so we don't rewrite those references
        cte_names = self._collect_cte_names(tree)

        # Track aliases used so we can avoid duplicate aliasing
        used_aliases = set()

        # Normalize mapping for case-insensitive lookup
        mapping = {k.lower(): v for k, v in table_to_local_path.items()}

        # Walk table nodes and replace where appropriate
        for table_node in list(tree.find_all(exp.Table)):
            base_node = table_node.this
            if isinstance(base_node, exp.Identifier):
                base_name = base_node.this
            else:
                base_name = str(base_node)

            print(type(base_name))
            alias = table_node.alias
            local_path = mapping[base_name.lower()]

            if base_name.lower() in cte_names:
                continue
            if base_name.lower() not in mapping: 
                continue
            if not alias:
                alias = base_name
            if alias.lower() in used_aliases or alias.lower() in cte_names:
                raise ValueError(f"Alias conflict for table {base_name} with alias {alias}")

            used_aliases.add(alias.lower)
            func = exp.Anonymous(
                this="read_parquet",
                expressions=[exp.Literal.string(local_path)],
            )
            alias_expr = exp.Alias(this=func, alias=exp.to_identifier(alias))
            table_node.replace(alias_expr)

        modified_sql = tree.sql(dialect=self.dialect)
        return modified_sql

# Small demonstration function you can call to integrate into your pipeline:
def rewrite_for_execution(sql: str, table_to_local_path: Dict[str, str]):
    rewriter = QueryRewriter()
    return rewriter.rewrite_query(sql, table_to_local_path)


