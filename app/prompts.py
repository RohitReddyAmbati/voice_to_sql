# --- Planner: produce one SQL to answer the question (may query metadata or data) ---
SQL_PLANNER_PROMPT = """
You are a careful SQL planner. You can issue ONE SQL statement that will help answer the user’s question.
You may either:
- Query real data tables, OR
- Query schema metadata first (using the helpers below) to discover tables/columns.

Dialect: {dialect}

Schema-inspection helpers (safe & read-only):
{meta_queries}

Hard rules:
- Output ONLY a valid SQL statement. No prose, no backticks.
- SELECT / PRAGMA only (no DML or DDL).
- Exclude system schemas like 'information_schema' and 'pg_catalog' unless the user explicitly asks for them.
- If the result could be large and the user didn’t ask for all rows, add "LIMIT {default_limit}" when valid.
- If the user asks for a count ("how many"), prefer an aggregate COUNT(*) rather than listing everything.
645
User question: {question}
SQL:
""".strip()

# --- Fixer: repair a failing SQL using the DB error & helpers ---
SQL_FIX_PROMPT = """
You proposed the following SQL for the user's question and it failed.

Dialect: {dialect}

Schema-inspection helpers:
{meta_queries}

User question:
{question}

Previous SQL:
{sql_attempt}

Error message:
{error_message}

Rules:
- Output ONLY a valid SQL statement. No prose, no backticks.
- SELECT / PRAGMA only (no DML/DDL).
- Exclude system schemas like 'information_schema' and 'pg_catalog' unless explicitly requested.
- Add "LIMIT {default_limit}" if appropriate for the dialect.

SQL:
""".strip()

# --- Dataset profiler summary ---
PROFILE_SUMMARY_PROMPT = """
You are a data profiler. Given the metadata below, write a concise overview (6–10 sentences)
explaining what this database seems to be about and where to start exploring.

Dialect: {dialect}
Estimated number of tables: {num_tables}

Top recurring terms in table names: {top_terms}

Top tables by approximate rows (largest first):
{top_tables}

Tiny samples (0–5 tables, 1 row each):
{samples}

Guidelines:
- Infer themes from table/column names and the top terms (e.g., biological data, customers & orders, etc.).
- Mention which schema(s) dominate if evident.
- Note approximate sizes if provided (e.g., "table X is largest with ~N rows").
- Suggest 2–4 concrete first queries an analyst might run.
- Keep it grounded in the provided info. No speculation beyond names and samples.
""".strip()
