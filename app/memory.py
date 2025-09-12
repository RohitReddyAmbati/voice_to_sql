"""
Very simple conversation memory.
Stores (question, answer) pairs in a list.
You can later replace this with a database, Redis, or vector store.
"""

from typing import List, Tuple

_memory: List[Tuple[str, str]] = []

def add_memory(question: str, answer: str):
    """Save a (question, answer) pair into memory."""
    _memory.append((question.strip(), answer.strip() if answer else ""))

def recall_memory(query: str) -> str:
    """
    Return something relevant from memory for a query.
    Right now: 
      - if user asks 'what was my last question?', return last question
      - if user asks 'what was my last answer?', return last answer
      - else echo the last Q/A pair
    """
    if not _memory:
        return "I don’t have any memory yet."

    q_lower = query.lower()
    if "last question" in q_lower:
        return f"Your last question was: {_memory[-1][0]}"
    elif "last answer" in q_lower:
        return f"My last answer was: {_memory[-1][1]}"
    else:
        last_q, last_a = _memory[-1]
        return f"Earlier you asked: '{last_q}' and I answered: '{last_a}'"

def all_memory() -> List[Tuple[str, str]]:
    """Return the full conversation history."""
    return list(_memory)
