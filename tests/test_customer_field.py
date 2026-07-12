"""Removing the onboarding 'Who's your customer?' question — backend
compatibility: the field stays optional, existing values are preserved, and
Store DNA / matching work when it is absent."""
from app.api.v1.user import BusinessProfileRequest
from app.services.store_dna import _fallback_dna, dna_match_score, generate_store_dna


def test_business_profile_accepts_payload_without_target_customer():
    # onboarding now omits target_customer — the request model must still validate
    req = BusinessProfileRequest(category="Apparel & Fashion", price_range="mid", primary_goal="pricing")
    assert req.target_customer is None
    # and the persisted payload (non-None only) excludes it → existing value untouched
    persisted = {k: v for k, v in req.model_dump().items() if v is not None}
    assert "target_customer" not in persisted


def test_business_profile_still_accepts_target_customer_for_compatibility():
    # existing accounts / API clients may still send it
    req = BusinessProfileRequest(target_customer="small dog owners")
    persisted = {k: v for k, v in req.model_dump().items() if v is not None}
    assert persisted["target_customer"] == "small dog owners"


def test_store_dna_fallback_defaults_audience_without_target_customer():
    dna = _fallback_dna({"category": "Apparel & Fashion", "subcategory": "Streetwear",
                         "product_types": ["hoodie", "tee"], "pricing_tier": "mid-market"})
    assert dna["audience"]  # never empty — a safe default, not an invented persona
    assert dna["audience"] == "general online shoppers"


def test_generate_store_dna_without_key_uses_fallback_no_target_customer(monkeypatch):
    # no API key → heuristic fallback path; must not require target_customer
    dna = generate_store_dna({"category": "Apparel & Fashion", "subcategory": "Streetwear",
                              "product_types": ["graphic tee"], "product_titles": ["Oversized graphic tee"]})
    assert dna is not None and dna["keywords"]


def test_dna_match_score_works_without_target_customer():
    a = {"category": "Apparel & Fashion", "pricing_tier": "mid-market",
         "dna_keywords": ["graphic", "tee", "hoodie", "streetwear"]}
    b = {"category": "Apparel & Fashion", "pricing_tier": "mid-market",
         "dna_keywords": ["graphic", "tee", "hoodie", "oversized"]}
    # neither has target_customer — must not crash and still score on keywords/category
    score = dna_match_score(a, b)
    assert score >= 60
