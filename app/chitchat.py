from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from app.config import get_settings
from app.memory import recent_dialog, search_memory, last_user_question

settings = get_settings()
chat_llm = ChatOllama(model=settings.OLLAMA_MODEL, temperature=0.2)

_CHAT_PROMPT = PromptTemplate(
    template="""
You are a concise, helpful assistant with access to a small session memory.

Use the context below to answer:
- If the user asks about PAST CONVERSATION (e.g., "what did I ask before", "what did you answer", "what SQL did you run"),
  consult the memory snippets to retrieve the relevant fact verbatim when possible.
- If the user asks about GENERAL SQL KNOWLEDGE (e.g., joins, indexes, ACID, normalization),
  provide a short, accurate explanation with a tiny example if helpful.
- If memory does not contain the requested fact, say briefly that you don't have it.

Rules:
- Keep answers 2–6 sentences.
- Do NOT invent memory that isn't present.
- If you reference memory, cite it briefly ("earlier you said: …") based on the snippets.

Recent dialog (most recent last):
{history}

Relevant memory snippets (oldest→newest):
{mem_snippets}

User: {question}
Assistant:
""".strip(),
    input_variables=["history","mem_snippets","question"]
)

def _format_snippets(snips):
    if not snips:
        return "(none)"
    lines = []
    for role, text in snips:
        role2 = "USER" if role == "user" else ("ASSISTANT" if role == "assistant" else "SQL")
        lines.append(f"[{role2}] {text}")
    # limit to keep prompt small
    return "\n".join(lines[-20:])

def chitchat_answer(session: str, question: str) -> str:
    # Build short history + search memory by tokens from the question
    hist = "\n".join(f"{r}: {t}" for r,t in recent_dialog(session, limit=8)) or "(no prior turns)"
    mem = search_memory(session, question, limit=25)
    mem_text = _format_snippets(mem)
    resp = chat_llm.invoke(_CHAT_PROMPT.format(history=hist, mem_snippets=mem_text, question=question))
    return (resp.content or "").strip()
