from __future__ import annotations
import json
from statistics import mean
from typing import Literal, Dict, Any, List

from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from app.config import get_settings

IntentLabel = Literal["SQL_DATA", "SQL_SCHEMA", "PROFILE", "CHITCHAT"]

settings = get_settings()
# Classification should be deterministic and terse
clf_llm = ChatOllama(model=settings.OLLAMA_MODEL, temperature=0)

# -- Zero-shot, definition-only prompt, no keyword hints --
# The model must return strict JSON on one line.
_INTENT_PROMPT = PromptTemplate(
    template="""
You are an intent classifier. Read the user's question and decide which ONE label applies.
Return ONLY a single-line JSON object with keys: label, confidence, rationale.

Labels (pick exactly one):
- SQL_DATA   : The user seeks an answer that requires reading ACTUAL DATA rows (facts, metrics, filters, aggregations, samples) from domain tables.
- SQL_SCHEMA : The user asks about the DATABASE STRUCTURE / METADATA (tables, columns, data types, relationships, counts of tables/columns) rather than domain data values.
- PROFILE    : The user requests a HIGH-LEVEL OVERVIEW of the entire dataset/database (themes, what it's about, where to start, key tables), not specific rows or schema minutiae.
- CHITCHAT   : The user engages in general conversation or MEMORY/meta questions (greetings, “do you remember…”, “who are you”), or general knowledge unrelated to executing SQL.

Rules:
- Do NOT infer based on keywords; decide based on the meaning.
- If the answer requires executing SELECTs over domain tables -> SQL_DATA.
- If the answer can be derived from catalog/metadata only -> SQL_SCHEMA.
- If the user wants a holistic description of the whole dataset -> PROFILE.
- If it's conversational or general knowledge -> CHITCHAT.
- Output strict JSON, one line, no code fences.

User question: {question}
JSON:
""".strip(),
    input_variables=["question"],
)

def _one_vote(question: str) -> Dict[str, Any]:
    """Ask the model once and parse its JSON."""
    resp = clf_llm.invoke(_INTENT_PROMPT.format(question=question))
    text = (resp.content or "").strip()
    # Be defensive about extra whitespace/newlines
    try:
        # sometimes models wrap with ```json ... ```
        if text.startswith("```"):
            text = text.strip("` \n")
            # drop 'json' language tag if present
            if text.lower().startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
    except Exception:
        # worst case: map anything to CHITCHAT so we fail safe
        data = {"label": "CHITCHAT", "confidence": 0.0, "rationale": "parse_error"}
    # normalize
    label = str(data.get("label", "CHITCHAT")).upper()
    if label not in {"SQL_DATA", "SQL_SCHEMA", "PROFILE", "CHITCHAT"}:
        label = "CHITCHAT"
    conf = data.get("confidence", 0.0)
    try:
        conf = float(conf)
    except Exception:
        conf = 0.0
    data["label"] = label
    data["confidence"] = max(0.0, min(1.0, conf))
    data["rationale"] = str(data.get("rationale", ""))[:500]
    return data

def classify_intent(question: str, votes: int = 5) -> IntentLabel:
    """
    Robust classification via self-consistency:
    - Run the zero-shot classifier multiple times (votes)
    - Return the majority label; ties broken by highest average confidence
    """
    # lightweight fast-path: empty or super-short -> CHITCHAT
    q = (question or "").strip()
    if len(q) < 3:
        return "CHITCHAT"

    results: List[Dict[str, Any]] = [_one_vote(question) for _ in range(max(1, votes))]
    # tally
    buckets: Dict[IntentLabel, List[float]] = {"SQL_DATA": [], "SQL_SCHEMA": [], "PROFILE": [], "CHITCHAT": []}
    for r in results:
        buckets[r["label"]].append(r["confidence"])

    # majority by count
    label_by_count = sorted(
        buckets.items(),
        key=lambda kv: (len(kv[1]), mean(kv[1]) if kv[1] else 0.0),
        reverse=True,
    )
    top_label, top_confs = label_by_count[0]
    # if there is a tie on count, the sort’s second key (mean confidence) breaks it

    return top_label  
