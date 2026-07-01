"""Pluggable LLM client: a real AnthropicClient when ANTHROPIC_API_KEY is
set, else a NullLLMClient that raises a typed error rather than crashing
(see docs/architecture.md #11)."""

from __future__ import annotations

import os

from agents.base import LLMNotConfiguredError, LLMResponse

DEFAULT_MODEL = "claude-sonnet-4-5"


class AnthropicClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
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


class NullLLMClient:
    def complete(self, system: str, messages: list[dict], max_tokens: int = 1024) -> LLMResponse:
        raise LLMNotConfiguredError(
            "ANTHROPIC_API_KEY is not set; this generative step is unavailable. "
            "Callers must degrade (e.g. keyword fallback) or surface a 503."
        )


def get_llm_client(model_env_var: str = "CLAUDE_MODEL"):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return NullLLMClient()
    model = os.environ.get(model_env_var, DEFAULT_MODEL)
    return AnthropicClient(api_key=api_key, model=model)
