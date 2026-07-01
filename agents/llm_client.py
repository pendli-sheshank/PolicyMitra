"""Pluggable LLM client: a real provider client (Anthropic or OpenRouter)
when its API key is configured, else a NullLLMClient that raises a typed
error rather than crashing (see docs/architecture.md #11).

Provider selection (docs/architecture.md #12):
- LLM_PROVIDER env var explicitly picks "anthropic" or "openrouter".
- If unset, auto-detects: ANTHROPIC_API_KEY wins if both are set (keeps the
  original default behavior unchanged for existing users), else
  OPENROUTER_API_KEY, else no provider at all.

OpenRouter (https://openrouter.ai) fronts an OpenAI-compatible chat
completions API for many providers' models (OpenAI, Google, Meta, Mistral,
Anthropic itself, and others) behind one API key — this is what lets a user
choose a different LLM without changing any agent code, just .env.
"""

from __future__ import annotations

import os

from agents.base import LLMNotConfiguredError, LLMResponse

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class AnthropicClient:
    def __init__(self, api_key: str, model: str = DEFAULT_ANTHROPIC_MODEL):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> LLMResponse:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResponse(text=text, raw=response.model_dump())


class OpenRouterClient:
    def __init__(self, api_key: str, model: str = DEFAULT_OPENROUTER_MODEL):
        self.api_key = api_key
        self.model = model

    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> LLMResponse:
        import httpx

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, *messages],
        }
        response = httpx.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                # Optional attribution headers OpenRouter uses for its public
                # rankings/rate-limit context — harmless if left as defaults.
                "HTTP-Referer": os.environ.get("OPENROUTER_SITE_URL", "https://policymitra.local"),
                "X-Title": "PolicyMitra",
            },
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return LLMResponse(text=text, raw=data)


class NullLLMClient:
    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> LLMResponse:
        raise LLMNotConfiguredError(
            "No LLM provider is configured (set ANTHROPIC_API_KEY or OPENROUTER_API_KEY in .env); "
            "this generative step is unavailable. Callers must degrade (e.g. keyword fallback) "
            "or surface a 503."
        )


def _resolve_provider() -> str | None:
    """Returns "anthropic", "openrouter", or None (nothing usable configured).
    Raises ValueError only for a garbage LLM_PROVIDER value — a genuine
    misconfiguration the caller should see immediately, not silently degrade."""
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if explicit in ("anthropic", "openrouter"):
        return explicit
    if explicit:
        raise ValueError(f"Unknown LLM_PROVIDER: {explicit!r}. Use 'anthropic' or 'openrouter'.")

    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    return None


def get_llm_client():
    provider = _resolve_provider()

    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return NullLLMClient()
        model = os.environ.get("CLAUDE_MODEL", DEFAULT_ANTHROPIC_MODEL)
        return AnthropicClient(api_key=api_key, model=model)

    if provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return NullLLMClient()
        model = os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        return OpenRouterClient(api_key=api_key, model=model)

    return NullLLMClient()
