import httpx
import pytest

from ingestion.embedding import get_default_embedder
from ingestion.embedding.local_hash_embedder import LocalHashEmbedder
from ingestion.embedding.openai_embedder import (
    OpenAIEmbedder,
    OpenAIEmbedderNotConfiguredError,
)


@pytest.fixture(autouse=True)
def _clear_embedder_env(monkeypatch):
    for var in ("OPENAI_API_KEY", "OPENAI_EMBED_MODEL"):
        monkeypatch.delenv(var, raising=False)


def test_missing_key_raises_typed_error():
    with pytest.raises(OpenAIEmbedderNotConfiguredError):
        OpenAIEmbedder()


def test_default_embedder_is_local_without_key():
    assert isinstance(get_default_embedder(), LocalHashEmbedder)


def test_default_embedder_is_openai_with_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    embedder = get_default_embedder()
    assert isinstance(embedder, OpenAIEmbedder)
    assert embedder.name == "text-embedding-3-small"
    assert embedder.dim == 1536


def test_embed_request_shape_and_order_preservation(monkeypatch):
    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        # Deliberately out of order: the client must sort by index.
        return httpx.Response(
            status_code=200,
            request=httpx.Request("POST", url),
            json={
                "data": [
                    {"index": 1, "embedding": [0.4, 0.5]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    embedder = OpenAIEmbedder(api_key="test-key")
    vectors = embedder.embed(["first text", "second text"])

    assert vectors == [[0.1, 0.2], [0.4, 0.5]]
    assert captured["url"] == "https://api.openai.com/v1/embeddings"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"] == {"input": ["first text", "second text"], "model": "text-embedding-3-small"}


def test_model_overridable_via_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
    embedder = OpenAIEmbedder()
    assert embedder.model == "text-embedding-3-large"
    assert embedder.name == "text-embedding-3-large"


def test_local_hash_embedder_matches_pgvector_column_dim():
    embedder = LocalHashEmbedder()
    assert embedder.dim == 1536
    (vec,) = embedder.embed(["room rent limit 2 percent"])
    assert len(vec) == 1536
