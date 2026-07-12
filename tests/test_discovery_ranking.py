"""Discovery ranking precision for NICHE product descriptions.

Production smoke-test: "I sell cheap handmade ashtrays" (→ Home & Living) put
sneakers / apparel / nail-product stores above plausible home-accessory stores.
Root cause: Claude-suggested candidates were appended in the model's order with
no category-contradiction guard (only index rows were re-ranked).

These lock the deterministic classifier + `rank_discovery_candidates` used to
demote hard product-type contradictions below plausible picks. No ashtray or
specific domain is hardcoded — the store's category is Home & Living and the
rule is category-cluster contradiction.
"""
from app.services.store_index import classify_text_rules, rank_discovery_candidates
from app.services.store_dna import category_relation

USER_CATEGORY = "Home & Living"

# The production result set (reason text mirrors what discovery shows), labeled.
# label: "plausible" (home / adjacent / unknown) vs "contradiction" (wrong type)
POOL = [
    ("contradiction", {"domain": "greats.com", "reason": "premium leather sneakers, minimalist design"}),
    ("contradiction", {"domain": "wildfang.com", "reason": "tomboy apparel and clothing for women"}),
    ("contradiction", {"domain": "thenailest.com", "reason": "press-on nail and manicure products"}),
    ("plausible",     {"domain": "snowehome.com", "reason": "home decor and ceramic tableware"}),
    ("plausible",     {"domain": "elysian-collective.com", "reason": "handmade ceramic and pottery home accessories"}),
    ("plausible",     {"domain": "trinket-shop.com", "reason": "quirky trinket dishes and small home decor gifts"}),
    ("plausible",     {"domain": "claycraft.com", "reason": "handmade ceramic mug and vase homeware"}),
]


def test_classifier_catches_wrong_product_types():
    assert category_relation(classify_text_rules("premium leather sneakers"), USER_CATEGORY) == "contradiction"
    assert category_relation(classify_text_rules("press-on nail and manicure"), USER_CATEGORY) == "contradiction"
    assert category_relation(classify_text_rules("tomboy apparel clothing"), USER_CATEGORY) == "contradiction"


def test_classifier_keeps_home_accessories_plausible():
    for text in ("home decor and ceramic tableware", "handmade ceramic pottery accessories",
                 "ceramic mug and vase homeware"):
        rel = category_relation(classify_text_rules(text), USER_CATEGORY)
        assert rel in ("same", "adjacent", "unknown"), f"{text} → {rel}"


def _order(pool):
    ranked = rank_discovery_candidates([c for _, c in pool], USER_CATEGORY)
    domains = [c["domain"] for c in ranked]
    labels = {c["domain"]: lbl for lbl, c in pool}
    return domains, labels


def test_before_no_contradiction_guard_puts_wrong_types_on_top():
    # BEFORE (no user category → no re-rank): production order is preserved,
    # wrong-product-type stores lead.
    unranked = rank_discovery_candidates([c for _, c in POOL], None)
    top3 = [c["domain"] for c in unranked[:3]]
    assert top3 == ["greats.com", "wildfang.com", "thenailest.com"]


def test_after_contradictions_sink_below_plausible():
    domains, labels = _order(POOL)
    # No contradiction may appear above any plausible candidate.
    first_contradiction = next(i for i, d in enumerate(domains) if labels[d] == "contradiction")
    last_plausible = max(i for i, d in enumerate(domains) if labels[d] == "plausible")
    assert first_contradiction > last_plausible, domains
    # precision@4 (the visible top slots) — all plausible now.
    top4 = domains[:4]
    assert all(labels[d] == "plausible" for d in top4), top4


def test_rerank_is_stable_for_same_class():
    # Plausible candidates keep their original relative order (stable sort).
    domains, _ = _order(POOL)
    plausible_order = [d for d in domains if d in
                       ("snowehome.com", "elysian-collective.com", "trinket-shop.com", "claycraft.com")]
    assert plausible_order == ["snowehome.com", "elysian-collective.com", "trinket-shop.com", "claycraft.com"]


def test_explicit_category_on_row_is_respected():
    # An index row carrying a classified category is demoted on that, not the reason text.
    cands = [
        {"domain": "a.com", "reason": "lovely things", "category": "Fashion"},       # contradiction
        {"domain": "b.com", "reason": "lovely things", "category": "Home & Living"}, # same
    ]
    ranked = rank_discovery_candidates(cands, USER_CATEGORY)
    assert ranked[0]["domain"] == "b.com"


def test_no_user_category_is_noop():
    cands = [{"domain": "x.com", "reason": "sneakers"}]
    assert rank_discovery_candidates(cands, None) == cands
