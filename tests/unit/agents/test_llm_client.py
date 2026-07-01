import pytest

from agents.llm_client import (
    AnthropicClient,
    NullLLMClient,
    OpenRouterClient,
    get_llm_client,
)


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch):
    for var in ("LLM_PROVIDER", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "CLAUDE_MODEL", "OPENROUTER_MODEL"):
        monkeypatch.delenv(var, raising=False)


def test_no_keys_returns_null_client():
    assert isinstance(get_llm_client(), NullLLMClient)


def test_anthropic_key_alone_selects_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    client = get_llm_client()
    assert isinstance(client, AnthropicClient)


def test_openrouter_key_alone_selects_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = get_llm_client()
    assert isinstance(client, OpenRouterClient)


def test_anthropic_key_wins_when_both_set_and_no_explicit_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = get_llm_client()
    assert isinstance(client, AnthropicClient)


def test_explicit_provider_overrides_auto_detection(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    client = get_llm_client()
    assert isinstance(client, OpenRouterClient)


def test_explicit_provider_without_its_key_degrades_to_null(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    client = get_llm_client()
    assert isinstance(client, NullLLMClient)


def test_unknown_provider_value_raises():
    import os

    os.environ["LLM_PROVIDER"] = "made-up-provider"
    try:
        with pytest.raises(ValueError):
            get_llm_client()
    finally:
        del os.environ["LLM_PROVIDER"]


def test_openrouter_model_defaults_and_is_overridable(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    client = get_llm_client()
    assert client.model == "openai/gpt-4o-mini"

    monkeypatch.setenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
    client = get_llm_client()
    assert client.model == "meta-llama/llama-3.1-8b-instruct"
