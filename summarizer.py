SUMMARY_PROMPT = """
You are a helpful assistant. 
The user asked: "{question}"

Here are the SQL query results (columns + rows):

Columns: {columns}
Rows: {rows}

Write a short natural language answer (2–3 sentences max) 
that explains the result clearly.
"""