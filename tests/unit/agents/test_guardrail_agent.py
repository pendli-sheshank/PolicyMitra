from agents.guardrail_agent import REDACTED_TEXT, GuardrailAgent


def test_guardrail_redacts_mismatch_without_llm():
    """No LLM configured -> no repair attempt -> straight to redaction. This
    is the safety-critical degrade path (docs/architecture.md #6)."""
    agent = GuardrailAgent(llm_client=None)
    text = "The waiting period for cataract is 18 months [CL-WAIT-PED-TABLE#Cataract]."
    chunk_lookup = {"CL-WAIT-PED-TABLE#Cataract": "Cataract — Waiting Period: 12 months; Sub-limit: ₹40,000."}

    result = agent.check(text, [], chunk_lookup)

    assert result.verdict == "blocked"
    assert REDACTED_TEXT in result.final_text
    assert "18 months" not in result.final_text


def test_guardrail_passes_verified_claim_unchanged():
    agent = GuardrailAgent(llm_client=None)
    text = "The waiting period for cataract is 12 months [CL-WAIT-PED-TABLE#Cataract]."
    chunk_lookup = {"CL-WAIT-PED-TABLE#Cataract": "Cataract — Waiting Period: 12 months; Sub-limit: ₹40,000."}

    result = agent.check(text, [], chunk_lookup)

    assert result.verdict == "pass"
    assert result.final_text == text


def test_guardrail_flags_and_strips_scope_drift_language():
    agent = GuardrailAgent(llm_client=None)
    text = "You should buy this plan today."

    result = agent.check(text, [], {})

    assert result.verdict == "repaired"
    assert "you should buy" not in result.final_text.lower()


def test_guardrail_never_silently_passes_a_failure():
    agent = GuardrailAgent(llm_client=None)
    text = "The sub-limit is ₹99,999 [CL-UNKNOWN]."

    result = agent.check(text, [], {})

    assert result.verdict == "blocked"
    assert len(result.detail) >= 1
