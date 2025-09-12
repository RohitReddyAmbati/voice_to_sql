from __future__ import annotations
import re
from collections import Counter
from typing import Dict, List, Tuple, Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.db import get_engine, dialect_name

def _pg_profile(schema_exclude=("pg_catalog","information_schema"), max_tables:int=30):
    eng = get_engine()
    with eng.connect() as c:
        tables = c.execute(text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
            AND table_schema NOT IN ('pg_catalog','information_schema')
            ORDER BY 1,2
            LIMIT :limit
        """), {"limit": max_tables}).fetchall()

        approx = c.execute(text("""
            SELECT n.nspname AS table_schema, c.relname AS table_name, c.reltuples::bigint AS approx_rows
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind='r'
            AND n.nspname NOT IN ('pg_catalog','information_schema')
        """)).fetchall()

        cols = c.execute(text("""
            SELECT table_schema, table_name, COUNT(*) AS col_count
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog','information_schema')
            GROUP BY 1,2
        """)).fetchall()

        # sample 1 row from a few largest tables (by approx_rows)
        approx_map = {(r[0], r[1]): r[2] for r in approx}
        top = sorted([(approx_map.get((s,t),0), s, t) for s,t in [(r[0],r[1]) for r in tables]], reverse=True)[:5]
        samples: Dict[Tuple[str,str], List[Tuple[Any,...]]] = {}
        for _, s, t in top:
            try:
                rows = c.execute(text(f'SELECT * FROM "{s}"."{t}" LIMIT 1')).fetchall()
                samples[(s,t)] = rows
            except SQLAlchemyError:
                pass

    return {
        "tables": tables,
        "approx": approx,
        "cols": cols,
        "samples": samples,
    }

def _generic_profile(max_tables:int=30):
    eng = get_engine()
    d = dialect_name()
    with eng.connect() as c:
        if d == "sqlite":
            tables = c.execute(text("SELECT name AS table_name FROM sqlite_master WHERE type='table' ORDER BY 1 LIMIT :limit"), {"limit": max_tables}).fetchall()
            cols = []
            for (t,) in tables:
                info = c.execute(text(f'PRAGMA table_info("{t}")')).fetchall()
                cols.append(("main", t, len(info)))
            return {"tables": [("main", t[0]) for t in tables], "approx": [], "cols": cols, "samples": {}}
        else:
            tables = c.execute(text("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_type='BASE TABLE'
                ORDER BY 1,2
                LIMIT :limit
            """), {"limit": max_tables}).fetchall()
            cols = c.execute(text("""
                SELECT table_schema, table_name, COUNT(*) AS col_count
                FROM information_schema.columns
                GROUP BY 1,2
            """)).fetchall()
            return {"tables": tables, "approx": [], "cols": cols, "samples": {}}

def _tokenize(names: List[str]) -> List[str]:
    toks=[]
    for n in names:
        n = n.replace("_"," ").lower()
        toks += re.findall(r"[a-z0-9]+", n)
    # drop very short tokens
    return [t for t in toks if len(t) > 2]

def profile_db() -> Dict[str, Any]:
    d = dialect_name()
    if d == "postgresql":
        data = _pg_profile()
    else:
        data = _generic_profile()
    # derive quick analytics
    table_names = [f"{s}.{t}" for s,t in data["tables"]]
    col_counts = { (s,t): n for s,t,n in data["cols"] }
    approx_rows = { (s,t): r for s,t,r in data["approx"] } if data["approx"] else {}

    # keyword extraction from table/column names
    name_tokens = _tokenize([tn.split(".",1)[-1] for tn in table_names])
    top_terms = Counter(name_tokens).most_common(12)

    # build a compact dict for the summarizer
    top_tables = sorted([(approx_rows.get((s,t),0), s, t, col_counts.get((s,t),None)) for s,t in [(r[0],r[1]) for r in data["tables"]]], reverse=True)[:8]
    samples = { f"{s}.{t}": rows for (s,t), rows in data["samples"].items() }

    return {
        "dialect": d,
        "num_tables": len(table_names),
        "top_terms": top_terms,
        "top_tables": top_tables,  # list of (approx_rows, schema, table, col_count)
        "samples": samples,        # { "schema.table": [ (row...), ... ] }
    }
