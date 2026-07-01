from agents.llm_client import NullLLMClient
from agents.router_agent import RouterAgent


def _router() -> RouterAgent:
    return RouterAgent(NullLLMClient())


def test_keyword_fallback_routes_comparison():
    result = _router().route("Can you compare Arogya Shield and Suraksha Health?", [], {})
    assert result.intent == "comparison"
    assert result.degraded is True


def test_keyword_fallback_routes_recommendation():
    result = _router().route("Which plan do you recommend for me?", [], {})
    assert result.intent == "recommendation"


def test_keyword_fallback_routes_drafting():
    result = _router().route("Please draft a WhatsApp message for my client", [], {})
    assert result.intent == "drafting"


def test_keyword_fallback_defaults_to_faq_claims():
    result = _router().route("What is the waiting period for cataract?", [], {})
    assert result.intent == "faq_claims"


def test_keyword_fallback_extracts_insurer_slot():
    result = _router().route("What is the waiting period for cataract under Arogya Shield?", [], {})
    assert result.slots.get("insurer") == "Arogya Shield General Insurance"
