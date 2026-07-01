import pytest

from agents.numeric_extraction import (
    Verdict,
    extract_sentences_with_claims,
    normalize_numeric_token,
    verify_claim,
)


def test_normalize_currency_variants_are_equal():
    assert normalize_numeric_token("₹1,00,000") == normalize_numeric_token("Rs. 100000")
    assert normalize_numeric_token("₹1,00,000") == normalize_numeric_token("INR 1,00,000")


def test_normalize_duration_grammar_variants_are_equal():
    assert normalize_numeric_token("24 months") == normalize_numeric_token("24 month")


def test_normalize_percent():
    claim = normalize_numeric_token("10%")
    assert claim.kind == "percent"
    assert claim.value == "10"


CASES = [
    (
        "The waiting period for cataract is 12 months [CL-WAIT-PED-TABLE#Cataract].",
        {"CL-WAIT-PED-TABLE#Cataract": "Cataract — Waiting Period: 12 months; Sub-limit: ₹40,000."},
        Verdict.PASS,
    ),
    (
        "The waiting period for cataract is 18 months [CL-WAIT-PED-TABLE#Cataract].",
        {"CL-WAIT-PED-TABLE#Cataract": "Cataract — Waiting Period: 12 months; Sub-limit: ₹40,000."},
        Verdict.FAIL_MISMATCH,
    ),
    (
        "The waiting period for cataract is 12 months.",
        {"CL-WAIT-PED-TABLE#Cataract": "Cataract — Waiting Period: 12 months; Sub-limit: ₹40,000."},
        Verdict.FAIL_UNCITED,
    ),
    (
        "The waiting period for cataract is 12 months [CL-DOES-NOT-EXIST].",
        {"CL-WAIT-PED-TABLE#Cataract": "Cataract — Waiting Period: 12 months; Sub-limit: ₹40,000."},
        Verdict.FAIL_HALLUCINATED_CITATION,
    ),
    (
        # differently formatted in source ("Rs. 40000" vs "₹40,000") — must still match
        "The sub-limit for cataract is ₹40,000 [CL-WAIT-PED-TABLE#Cataract].",
        {"CL-WAIT-PED-TABLE#Cataract": "Cataract — Waiting Period: 12 months; Sub-limit: Rs. 40000."},
        Verdict.PASS,
    ),
    (
        "Cosmetic surgery is not covered [CL-EXCL-COSMETIC].",
        {"CL-EXCL-COSMETIC": "Cosmetic surgery is excluded."},
        Verdict.PASS,  # no numeric claim at all -> always passes
    ),
]


@pytest.mark.parametrize("sentence,chunk_lookup,expected_verdict", CASES)
def test_verify_claim_table(sentence, chunk_lookup, expected_verdict):
    claim = extract_sentences_with_claims(sentence)[0]
    result = verify_claim(claim, chunk_lookup)
    assert result.verdict == expected_verdict
