"""Competitor-ranking precision — a labeled eval set over the deterministic
core (`dna_match_score` + `category_relation`). No network, no AI: these
assert the ranking properties the discovery pipeline relies on.

The scenario is a mid-market streetwear / graphic-tee apparel store (the same
example category the product spec calls out) ranked against a pool of labeled
candidates:

  direct        — real rivals: streetwear / graphic-tee apparel, mid price
  adjacent      — same apparel cluster, different category (footwear, bags)
  price_mismatch— same category, far price tier (luxury designer apparel)
  contradiction — wrong product type entirely (furniture, beauty, pets, tech)

Reported/asserted: precision@5, hard contradictions in top 5, and the
direct > adjacent > contradiction ordering.
"""
from app.services.store_dna import category_relation, dna_match_score

USER = {
    "category": "Fashion", "subcategory": "Streetwear", "pricing_tier": "mid-market",
    "dna_keywords": ["graphic", "tee", "t-shirt", "hoodie", "streetwear",
                     "oversized", "cotton", "print", "unisex", "apparel"],
}

# label, store
POOL = [
    ("direct", {"category": "Fashion", "subcategory": "Streetwear", "pricing_tier": "mid-market",
                "dna_keywords": ["graphic", "tee", "hoodie", "streetwear", "oversized", "print", "unisex", "cotton"]}),
    ("direct", {"category": "Fashion", "subcategory": "Streetwear", "pricing_tier": "mid-market",
                "dna_keywords": ["tee", "t-shirt", "hoodie", "streetwear", "cotton", "apparel", "print", "graphic"]}),
    ("direct", {"category": "Fashion", "subcategory": "Menswear", "pricing_tier": "mid-market",
                "dna_keywords": ["graphic", "tee", "hoodie", "apparel", "cotton", "casual", "print", "unisex"]}),
    ("direct", {"category": "Fashion", "subcategory": "Streetwear", "pricing_tier": "budget",
                "dna_keywords": ["tee", "graphic", "streetwear", "print", "cotton", "oversized", "apparel"]}),

    ("price_mismatch", {"category": "Fashion", "subcategory": "Streetwear", "pricing_tier": "luxury",
                        "dna_keywords": ["designer", "tee", "streetwear", "logo", "cotton", "runway"]}),

    ("adjacent", {"category": "Footwear", "subcategory": "Sneakers", "pricing_tier": "mid-market",
                  "dna_keywords": ["sneaker", "shoe", "streetwear", "unisex", "canvas", "lace"]}),
    ("adjacent", {"category": "Accessories", "subcategory": "Bags", "pricing_tier": "mid-market",
                  "dna_keywords": ["backpack", "tote", "canvas", "streetwear", "unisex", "bag"]}),

    ("contradiction", {"category": "Home & Living", "subcategory": "Furniture", "pricing_tier": "mid-market",
                       "category_confidence": 80,
                       "dna_keywords": ["sofa", "table", "oak", "cotton", "print", "oversized", "modern"]}),
    ("contradiction", {"category": "Beauty", "subcategory": "Skincare", "pricing_tier": "mid-market",
                       "category_confidence": 80,
                       "dna_keywords": ["serum", "cream", "cotton", "unisex", "glow", "print"]}),
    ("contradiction", {"category": "Pets", "subcategory": "Pet Accessories", "pricing_tier": "mid-market",
                       "category_confidence": 80,
                       "dna_keywords": ["dog", "collar", "cotton", "print", "leash", "unisex"]}),
    ("contradiction", {"category": "Electronics & Gadgets", "subcategory": "Audio", "pricing_tier": "mid-market",
                       "category_confidence": 80,
                       "dna_keywords": ["headphone", "speaker", "wireless", "print", "cotton"]}),
]


def _ranked():
    scored = [(label, s, dna_match_score(s, USER)) for label, s in POOL]
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored


def test_no_hard_contradiction_in_top_5():
    top5 = _ranked()[:5]
    contradictions = [l for l, _, _ in top5 if l == "contradiction"]
    assert not contradictions, f"wrong-product-type store(s) reached top 5: {top5}"


def test_precision_at_5_is_high():
    top5 = _ranked()[:5]
    directs = sum(1 for l, _, _ in top5 if l == "direct")
    # 4 direct rivals exist; a precise ranker surfaces them ahead of the pool.
    assert directs >= 4, f"precision@5 too low — only {directs}/5 direct: {[l for l,_,_ in top5]}"


def test_direct_outranks_every_contradiction():
    scored = _ranked()
    direct_scores = [sc for l, _, sc in scored if l == "direct"]
    contra_scores = [sc for l, _, sc in scored if l == "contradiction"]
    assert min(direct_scores) > max(contra_scores), (
        f"a contradiction scored >= a direct rival: "
        f"direct min {min(direct_scores)} vs contradiction max {max(contra_scores)}")


def test_adjacent_ranks_below_direct_and_at_or_above_contradiction():
    scored = _ranked()
    direct_scores = [sc for l, _, sc in scored if l == "direct"]
    adj_scores = [sc for l, _, sc in scored if l == "adjacent"]
    contra_scores = [sc for l, _, sc in scored if l == "contradiction"]
    # adjacent (same cluster) sits between direct rivals and wrong-product-type
    assert max(adj_scores) < max(direct_scores)
    assert min(adj_scores) >= max(contra_scores)


def test_category_relation_taxonomy():
    assert category_relation("Fashion", "Fashion") == "same"
    assert category_relation("Fashion", "Footwear") == "adjacent"       # apparel cluster
    assert category_relation("Fashion", "Home & Living") == "contradiction"
    assert category_relation("Beauty", "Supplements") == "adjacent"     # beauty_health cluster
    assert category_relation("Fashion", "Other") == "unknown"           # never penalize unknown
    assert category_relation("Fashion", None) == "unknown"


def test_contradiction_penalty_is_applied():
    # identical incidental keyword overlap, but a contradicting category must
    # score below a neutral (unknown-category) store with the same overlap.
    overlap = {"dna_keywords": ["cotton", "print", "oversized", "unisex"]}
    neutral = {**overlap}                                    # no category → no penalty
    furniture = {**overlap, "category": "Home & Living"}     # hard contradiction
    assert dna_match_score(furniture, USER) < dna_match_score(neutral, USER)
