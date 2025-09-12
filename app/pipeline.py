from typing import List, Tuple, Any
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate

from app.config import get_settings
from app.db import run_query, dialect_name, dialect_meta_queries
from app.prompts import SQL_PLANNER_PROMPT, SQL_FIX_PROMPT
from summarizer import SUMMARY_PROMPT  

settings = get_settings()

sql_llm = ChatOllama(model=settings.OLLAMA_MODEL, temperature=settings.TEMPERATURE)
summary_llm = sql_llm

planner_prompt = PromptTemplate(
    template=SQL_PLANNER_PROMPT,
    input_variables=["dialect", "meta_queries", "default_limit", "question"],
)
fix_prompt = PromptTemplate(
    template=SQL_FIX_PROMPT,
    input_variables=["dialect", "meta_queries", "default_limit", "question", "sql_attempt", "error_message"],
)
summary_prompt = PromptTemplate(
    template=SUMMARY_PROMPT, input_variables=["question", "columns", "rows"]
)

def _gen_sql(question: str) -> str:
    resp = sql_llm.invoke(
        planner_prompt.format(
            dialect=dialect_name(),
            meta_queries=dialect_meta_queries(),
            default_limit=settings.DEFAULT_LIMIT,
            question=question,
        )
    )
    sql = (resp.content or "").strip()
    if sql.startswith("```"):
        sql = sql.strip("`").strip()
    return sql

def _fix_sql(question: str, sql_attempt: str, error_message: str) -> str:
    resp = sql_llm.invoke(
        fix_prompt.format(
            dialect=dialect_name(),
            meta_queries=dialect_meta_queries(),
            default_limit=settings.DEFAULT_LIMIT,
            question=question,
            sql_attempt=sql_attempt,
            error_message=error_message,
        )
    )
    sql = (resp.content or "").strip()
    if sql.startswith("```"):
        sql = sql.strip("`").strip()
    return sql

def _summarize(question: str, columns: List[str], rows: List[Tuple[Any, ...]]) -> str:
    preview = [list(r) for r in rows[:min(len(rows), 50)]] 
    resp = summary_llm.invoke(
        summary_prompt.format(question=question, columns=columns, rows=preview)
    )
    return (resp.content or "").strip()

def answer_question(question: str):
    # Step 1: plan
    sql = _gen_sql(question)

    # Step 2: execute (with one repair attempt)
    try:
        cols, rows = run_query(sql)
    except Exception as e:
        # Try one fixer pass
        try:
            sql2 = _fix_sql(question, sql_attempt=sql, error_message=str(e))
            cols, rows = run_query(sql2)
            sql = sql2
        except Exception as e2:
            return {"ok": False, "sql": sql, "error": f"{type(e2).__name__}: {e2}"}

    # Step 3: summarize grounded on rows
    text = _summarize(question, cols, rows)
    return {"ok": True, "sql": sql, "columns": cols, "rows": rows, "text": text}
