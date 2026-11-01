# ColumnCache (the original, DuckDB-based harness) is imported lazily so that the Spark
# placement path (placement_cache, vdi_store, spark_session) never loads DuckDB.
# `from column_cache import ColumnCache` works as before.
# from .schema_parser import parse_schema_file, parse_all_schemas,save_schema_registry, parse_single_schema_file, parse_schema

__all__ = ['ColumnCache']


def __getattr__(name):
    if name == "ColumnCache":
        from .column_cache import ColumnCache
        return ColumnCache
    raise AttributeError(name)
