"""Store DNA — keyword normalization + direct-competitor match scoring.
These power onboarding/discovery competitor matching, so their behavior is
load-bearing."""
from app.services.store_dna import normalize_keywords, dna_match_score


def test_normalize_keywords_lowercases_dedups_and_drops_stopwords():
    kw = normalize_keywords(["Gold Necklace", "the shop", "QUALITY", "18k-gold", {"title": "Earrings"}])
    assert "gold" in kw and "necklace" in kw and "earrings" in kw
    # generic/stopwords are stripped so overlap reflects real similarity
    assert "the" not in kw and "shop" not in kw and "quality" not in kw
    # deduped
    assert len(kw) == len(set(kw))


def test_normalize_keywords_handles_none_and_nested():
    assert normalize_keywords(None) == []
    assert "dog" in normalize_keywords([None, ["Dog Leash"], {"title": None}])


# Fixtures modeled on the real jewelry example the matcher was tuned against.
_USER = {"category": "Jewelry", "pricing_tier": "premium",
         "dna_keywords": ["gold", "necklace", "minimalist", "dainty", "everyday", "rings"]}
_STRONG = {"category": "Jewelry", "subcategory": "Fine Jewelry", "pricing_tier": "premium",
           "dna_keywords": ["gold", "necklace", "earrings", "minimalist", "everyday", "18k", "plated"]}
_WEAK_SAME_CAT = {"category": "Jewelry", "subcategory": "Costume", "pricing_tier": "budget",
                  "dna_keywords": ["chunky", "statement", "resin", "colorful", "festival", "plastic"]}
_UNRELATED = {"category": "Pets", "pricing_tier": "mid-market",
              "dna_keywords": ["dog", "leash", "collar", "treats"]}


def test_strong_direct_match_scores_high():
    assert dna_match_score(_STRONG, _USER) >= 60


def test_same_category_weak_semantic_scores_low():
    weak = dna_match_score(_WEAK_SAME_CAT, _USER)
    assert weak < 40
    # and a true rival must outrank a same-category-but-different-style store
    assert dna_match_score(_STRONG, _USER) > weak


def test_unrelated_store_scores_very_low():
    assert dna_match_score(_UNRELATED, _USER) < 20


def test_price_tier_influences_score():
    kws = ["gold", "necklace", "minimalist", "everyday"]
    same_tier = {"category": "Jewelry", "pricing_tier": "premium", "dna_keywords": kws}
    far_tier = {"category": "Jewelry", "pricing_tier": "budget", "dna_keywords": kws}
    user = {"category": "Jewelry", "pricing_tier": "premium", "dna_keywords": kws}
    # identical keywords/category; the closer price lane must score at least as high
    assert dna_match_score(same_tier, user) >= dna_match_score(far_tier, user)


def test_empty_rows_do_not_crash():
    assert dna_match_score({}, {}) == 0
