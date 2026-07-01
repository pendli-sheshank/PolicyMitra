from agents.llm_client import NullLLMClient
from agents.qa_agent import NOT_FOUND_MESSAGE, QAAgent
from retrieval.models import RetrievalResult


def test_empty_retrieval_returns_not_found_without_calling_llm():
    agent = QAAgent(NullLLMClient())
    result = agent.answer("What is the waiting period?", RetrievalResult(query="x", chunks=[]))
    assert result.output == NOT_FOUND_MESSAGE
    assert result.chunk_ids_used == []
