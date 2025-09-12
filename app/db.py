from __future__ import annotations
from typing import List, Tuple, Any, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import SQLAlchemyError
from app.config import get_settings

settings = get_settings()
_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return _engine

def dialect_name() -> str:
    return get_engine().dialect.name  # 'sqlite' | 'postgresql' | 'mysql' | 'mssql' ...

def run_query(sql: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    s = sql.strip().lower()
    if not (s.startswith("select") or s.startswith("pragma")):
        raise ValueError("Only SELECT/PRAGMA statements are allowed.")
    with get_engine().connect() as conn:
        result = conn.execution_options(stream_results=True).execute(text(sql))
        rows = list(result.fetchall())
        cols = list(result.keys())
    return cols, rows

def snapshot_schema(max_tables: int = 25, max_cols_per_table: int = 30) -> str:
    """
    Create a compact, LLM-friendly schema snapshot from SQLAlchemy inspector.
    """
    eng = get_engine()
    insp = inspect(eng)
    dialect = eng.dialect.name
    out: List[str] = [f"-- DIALECT: {dialect}"]
    try:
        # Prefer current/default schema if available; fall back to all schemas
        schemas = []
        if hasattr(insp, "default_schema_name") and insp.default_schema_name:
            schemas = [insp.default_schema_name]
        else:
            # For SQLite there is no concept of schemas; return tables() only
            try:
                schemas = insp.get_schema_names()
            except Exception:
                schemas = []

        tables_added = 0
        def add_table(tbl_schema: str | None, tbl_name: str):
            nonlocal tables_added
            if tables_added >= max_tables:
                return
            cols = insp.get_columns(tbl_name, schema=tbl_schema)
            col_lines = []
            for c in cols[:max_cols_per_table]:
                tname = getattr(c.get("type"), "__class__", type("t", (), {})).__name__
                nullable = "NULL" if c.get("nullable", True) else "NOT NULL"
                col_lines.append(f"  {c['name']} {tname} {nullable}")
            fq = f"{tbl_schema+'.' if tbl_schema else ''}{tbl_name}"
            out.append(f"\n-- {fq}")
            out.append(f"CREATE TABLE {fq} (\n" + ",\n".join(col_lines) + "\n);")
            tables_added += 1

        if dialect == "sqlite":
            for tbl in insp.get_table_names():
                add_table(None, tbl)
        else:
            # Add tables from default schema first
            seen = set()
            for s in (schemas or [None]):
                for tbl in insp.get_table_names(schema=s):
                    if (s, tbl) not in seen:
                        add_table(s, tbl)
                        seen.add((s, tbl))
            # If room remains, add from other schemas as a sample
            if tables_added < max_tables:
                for s in insp.get_schema_names():
                    if s in (schemas or []):
                        continue
                    for tbl in insp.get_table_names(schema=s):
                        if tables_added >= max_tables:
                            break
                        if (s, tbl) not in seen:
                            add_table(s, tbl)
                            seen.add((s, tbl))
    except SQLAlchemyError as e:
        out.append(f"-- Schema introspection error: {e}")
    return "\n".join(out)

def dialect_meta_queries() -> str:
    """
    Give the LLM safe ways to inspect schema via SQL for the current dialect.
    """
    d = dialect_name()
    if d == "sqlite":
        return (
            "List tables: SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;\n"
            "Describe columns: PRAGMA table_info(<table_name>);\n"
        )
    if d in ("postgresql",):
        return (
            "List tables: SELECT table_schema, table_name "
            "FROM information_schema.tables WHERE table_type='BASE TABLE' "
            "AND table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2;\n"
            "Describe columns: SELECT table_schema, table_name, column_name, data_type "
            "FROM information_schema.columns WHERE table_name = '<table_name>' ORDER BY ordinal_position;\n"
        )
    if d in ("mysql",):
        return (
            "List tables: SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' AND table_schema NOT IN ('mysql','sys','information_schema','performance_schema') ORDER BY 1,2;\n"
            "Describe columns: SELECT table_schema, table_name, column_name, data_type "
            "FROM information_schema.columns WHERE table_name = '<table_name>' ORDER BY ordinal_position;\n"
        )
    if d in ("mssql",):
        return (
            "List tables: SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE='BASE TABLE' ORDER BY 1,2;\n"
            "Describe columns: SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE "
            "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '<table_name>' ORDER BY ORDINAL_POSITION;\n"
        )
    return ""
