"""Pluggable LLM client: a real GeminiClient when GEMINI_API_KEY is
configured, else a NullLLMClient that raises a typed error rather than
crashing (see docs/architecture.md #11).

Provider selection (docs/architecture.md #12, superseded by #14):
- Google Gemini is the only chat provider. LLM_PROVIDER may be set to
  "gemini" explicitly (any other value is a hard error); if unset, the
  client is selected purely by the presence of GEMINI_API_KEY.

Gemini is called over its REST API via httpx — same pattern as the
OpenAI embedder — so no provider SDK dependency is needed. The agents
only ever see the LLMClient protocol (system + messages -> LLMResponse);
Gemini's systemInstruction/contents shape is mapped here and nowhere else.
"""

from __future__ import annotations

import os

from agents.base import LLMNotConfiguredError, LLMResponse

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient:
    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL):
        self.api_key = api_key
        self.model = model

    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> LLMResponse:
        import httpx

        # Gemini's chat roles are "user" and "model"; the agents speak the
        # OpenAI-style "user"/"assistant" convention, so map here.
        contents = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
        ]
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        response = httpx.post(
            f"{GEMINI_API_BASE}/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        parts = data["candidates"][0]["content"].get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        return LLMResponse(text=text, raw=data)


class NullLLMClient:
    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> LLMResponse:
        raise LLMNotConfiguredError(
            "No LLM provider is configured (set GEMINI_API_KEY in the environment or .env); "
            "this generative step is unavailable. Callers must degrade (e.g. keyword fallback) "
            "or surface a 503."
        )


def _resolve_provider() -> str | None:
    """Returns "gemini" or None (nothing usable configured). Raises ValueError
    only for a garbage LLM_PROVIDER value — a genuine misconfiguration the
    caller should see immediately, not silently degrade."""
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if explicit == "gemini":
        return explicit
    if explicit:
        raise ValueError(f"Unknown LLM_PROVIDER: {explicit!r}. Use 'gemini'.")

    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return None


def get_llm_client():
    provider = _resolve_provider()

    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return NullLLMClient()
        model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        return GeminiClient(api_key=api_key, model=model)

    return NullLLMClient()
