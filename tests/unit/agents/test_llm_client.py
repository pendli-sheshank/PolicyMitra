import httpx
import pytest

from agents.base import LLMNotConfiguredError
from agents.llm_client import (
    DEFAULT_GEMINI_MODEL,
    GeminiClient,
    NullLLMClient,
    get_llm_client,
)


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch):
    for var in ("LLM_PROVIDER", "GEMINI_API_KEY", "GEMINI_MODEL"):
        monkeypatch.delenv(var, raising=False)


def test_no_keys_returns_null_client():
    assert isinstance(get_llm_client(), NullLLMClient)


def test_null_client_raises_typed_error():
    with pytest.raises(LLMNotConfiguredError):
        NullLLMClient().complete(system="s", messages=[{"role": "user", "content": "hi"}])


def test_gemini_key_alone_selects_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = get_llm_client()
    assert isinstance(client, GeminiClient)


def test_explicit_provider_without_its_key_degrades_to_null(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    client = get_llm_client()
    assert isinstance(client, NullLLMClient)


def test_unknown_provider_value_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "made-up-provider")
    with pytest.raises(ValueError):
        get_llm_client()


def test_gemini_model_defaults_and_is_overridable(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = get_llm_client()
    assert client.model == DEFAULT_GEMINI_MODEL

    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    client = get_llm_client()
    assert client.model == "gemini-2.5-pro"


def test_gemini_complete_request_shape_and_response_parsing(monkeypatch):
    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return httpx.Response(
            status_code=200,
            request=httpx.Request("POST", url),
            json={
                "candidates": [
                    {"content": {"role": "model", "parts": [{"text": "Grounded "}, {"text": "answer."}]}}
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    client = GeminiClient(api_key="test-key", model="gemini-2.5-flash")
    response = client.complete(
        system="Answer only from context.",
        messages=[
            {"role": "user", "content": "What is the room-rent limit?"},
            {"role": "assistant", "content": "Earlier turn."},
            {"role": "user", "content": "And the co-pay?"},
        ],
        max_tokens=256,
    )

    assert response.text == "Grounded answer."
    assert captured["url"].endswith("/models/gemini-2.5-flash:generateContent")
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["json"]["systemInstruction"] == {"parts": [{"text": "Answer only from context."}]}
    assert captured["json"]["generationConfig"] == {"maxOutputTokens": 256}
    roles = [c["role"] for c in captured["json"]["contents"]]
    assert roles == ["user", "model", "user"]


def test_gemini_complete_raises_on_http_error(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(status_code=403, request=httpx.Request("POST", url), json={"error": "forbidden"})

    monkeypatch.setattr(httpx, "post", fake_post)

    client = GeminiClient(api_key="bad-key")
    with pytest.raises(httpx.HTTPStatusError):
        client.complete(system="s", messages=[{"role": "user", "content": "hi"}])
