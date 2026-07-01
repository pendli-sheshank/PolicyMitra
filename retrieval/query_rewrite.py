"""Optional LLM-assisted query rewrite for vague questions (e.g. "what about
the room thing" -> "what is the room rent cap"). Only invoked by
RetrievalAgent when the Router's slot extraction leaves the query
under-specified AND a real LLM client is configured; otherwise retrieval
just searches with the original query text."""

from __future__ import annotations

from typing import Any

REWRITE_SYSTEM_PROMPT = (
    "Rewrite the user's question into a precise, self-contained search query for a health "
    "insurance policy document search engine. Use any known context (insurer, ailment) given. "
    "Respond with ONLY the rewritten query text, no preamble."
)


def rewrite_query(llm_client: Any, message: str, known_slots: dict) -> str:
    context = ", ".join(f"{k}={v}" for k, v in known_slots.items() if v) or "none"
    user_content = f"Question: {message}\nKnown context: {context}"
    response = llm_client.complete(system=REWRITE_SYSTEM_PROMPT, messages=[{"role": "user", "content": user_content}])
    rewritten = response.text.strip()
    return rewritten or message
