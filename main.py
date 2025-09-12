import os
import uuid
from typing import List, Tuple, Any

from app.intent import classify_intent
from app.pipeline import answer_question              # SQL path (planner + fixer + summarize)
from app.profile import profile_db                    # DB profiler path
from app.memory import log_turn, clear_session, log_sql
from app.prompts import PROFILE_SUMMARY_PROMPT
from app.config import get_settings
from app.chitchat import chitchat_answer

from langchain_ollama import ChatOllama
settings = get_settings()
summary_llm = ChatOllama(model=settings.OLLAMA_MODEL, temperature=0.2)

SESSION_ID = os.getenv("SESSION_ID") or str(uuid.uuid4())

HELP_TEXT = """Commands:
  exit | quit | q   -> leave the REPL
  reset             -> clear session memory (this run)
  profile           -> run the DB profiler and summarize the dataset
  help              -> show this help
"""

def _print_sql_result(res: dict):
    print("\n[Text Answer]\n", res.get("text") or "(no summary)")
    print("\n[Preview Rows]")
    cols: List[str] = res.get("columns", []) or []
    if cols:
        print(cols)
    for r in res.get("rows", [])[:10]:
        print(r)
    print("\n[SQL Used]\n", res.get("sql"))

def handle_profile():
    prof = profile_db()
    # format lists for the prompt
    tt = [f"{t}×{n}" for t, n in prof.get("top_terms", [])]
    top_tbl_lines = []
    for approx, s, t, coln in prof.get("top_tables", []):
        size = f"~{approx}" if approx else "unknown"
        cols = f"{coln} cols" if coln is not None else "cols ?"
        top_tbl_lines.append(f"- {s}.{t} ({size}, {cols})")
    # stringify tiny samples to keep prompt compact
    samples = {
        k: [tuple(map(str, row)) for row in v][:1]  # 1 row per table shown
        for k, v in prof.get("samples", {}).items()
    } or "(none)"

    resp = summary_llm.invoke(
        PROFILE_SUMMARY_PROMPT.format(
            dialect=prof.get("dialect"),
            num_tables=prof.get("num_tables"),
            top_terms=", ".join(tt) if tt else "(none)",
            top_tables="\n".join(top_tbl_lines) if top_tbl_lines else "(none)",
            samples=samples,
        )
    )
    text = (resp.content or "").strip()
    print("\n[Profile]\n", text)
    log_turn(SESSION_ID, "assistant", text)

def main():
    print("NL2SQL REPL. Type your question. (type 'help' for commands)")
    while True:
        try:
            q = input("\nAsk me a question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not q:
            continue

        low = q.lower()
        if low in ("exit", "quit", "q"):
            print("Bye!")
            break
        if low == "help":
            print(HELP_TEXT)
            continue
        if low == "reset":
            clear_session(SESSION_ID)
            print("✔ session memory cleared.")
            continue
        if low == "profile":
            # Log user turn, then run profiler branch
            log_turn(SESSION_ID, "user", q)
            handle_profile()
            continue

        # Log user turn first (so it's in memory for chitchat)
        log_turn(SESSION_ID, "user", q)

        intent = classify_intent(q)

        if intent == "PROFILE":
            handle_profile()
            continue

        if intent == "CHITCHAT":
            text = chitchat_answer(SESSION_ID, q)
            print("\n[Text Answer]\n", text)
            log_turn(SESSION_ID, "assistant", text)
            continue

        # SQL path for SQL_DATA or SQL_SCHEMA
        res = answer_question(q)
        if not res.get("ok"):
            print("\n[ERROR]", res.get("error"))
            print("\n[SQL Attempt]\n", res.get("sql"))
            log_turn(SESSION_ID, "assistant", f"ERROR: {res.get('error')}")
        else:
            _print_sql_result(res)
            # Log assistant text & the SQL used for audit
            log_turn(SESSION_ID, "assistant", res.get("text") or "")
            if res.get("sql"):
                log_sql(SESSION_ID, res["sql"], note="SQL used for last answer")

if __name__ == "__main__":
    main()
