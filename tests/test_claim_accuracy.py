"""Intelligence-claim accuracy — deterministic generators must not assert things
StoreScout hasn't measured (unmet demand as fact, SKU overlap without the user's
catalog, SEO/review weakness, customer behavior/intent/margin as fact)."""
import os
import re

from app.services.insights import compute_quick_wins

_ROOT = os.path.dirname(os.path.dirname(__file__))

# Phrases that assert something the scan does not observe.
_FORBIDDEN = [
    r"demand they can'?t fulfil",        # unmet demand as fact (stockout; matches fulfil/fulfill)
    r"overlapping SKUs?",                 # SKU overlap without the user's catalog
    r"top \d+ overlapping",
    r"weak SEO", r"poor SEO", r"strong SEO",
    r"sparse reviews", r"few reviews", r"no reviews",
]
_FORBIDDEN_RE = re.compile("|".join(_FORBIDDEN), re.I)


def _snap(**over):
    base = {
        "catalog": {"total_products": 200, "out_of_stock_pct": 0, "out_of_stock_count": 0, "in_stock_pct": 100},
        "pricing": {"median": 60, "p25": 40, "p75": 90, "min": 20, "max": 150},
        "discounts": {"discounted_pct": 0, "avg_discount_pct": 0},
        "launch_timeline": {"launch_counts": {"30d": {"count": 0}}},
    }
    for k, v in over.items():
        base.setdefault(k, {}).update(v) if isinstance(v, dict) else base.__setitem__(k, v)
    return base


def _all_text(wins):
    return " ".join(f"{w.get('title','')} {w.get('detail','')}" for w in wins)


def test_stockout_win_does_not_assert_unmet_demand_as_fact():
    wins = compute_quick_wins(_snap(catalog={"total_products": 200, "out_of_stock_pct": 20, "out_of_stock_count": 40, "in_stock_pct": 80}))
    text = _all_text(wins)
    assert not _FORBIDDEN_RE.search(text), f"forbidden claim in stockout copy: {text}"
    # still decisive + hedged
    assert ("likely opening" in text) or ("Whether" in text) or ("if you" in text.lower())


def test_high_discount_scenario_has_no_forbidden_claims():
    wins = compute_quick_wins(_snap(discounts={"discounted_pct": 55, "avg_discount_pct": 40}))
    assert not _FORBIDDEN_RE.search(_all_text(wins))


def test_launch_burst_scenario_has_no_forbidden_claims():
    wins = compute_quick_wins(_snap(launch_timeline={"launch_counts": {"30d": {"count": 35}}}))
    assert not _FORBIDDEN_RE.search(_all_text(wins))


def test_competitor_only_data_never_claims_own_catalog_overlap():
    # With no own-store catalog provided, any overlap mention must be conditional.
    wins = compute_quick_wins(_snap(catalog={"total_products": 200, "out_of_stock_pct": 12, "out_of_stock_count": 24, "in_stock_pct": 88}))
    text = _all_text(wins).lower()
    if "overlap" in text or "comparable" in text:
        assert ("if you" in text) or ("comparable" in text)  # conditional, not asserted


def test_deterministic_copy_sources_have_no_unsupported_claims():
    # Source-level regression guard across the deterministic copy modules.
    files = [
        "app/services/insights.py",
        "app/services/playbook_intelligence.py",
        "app/services/action_templates.py",
        "frontend/lib/market.ts",
        "frontend/lib/signals.ts",
    ]
    hits = []
    for rel in files:
        p = os.path.join(_ROOT, rel)
        if not os.path.exists(p):
            continue
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            if _FORBIDDEN_RE.search(line):
                hits.append(f"{rel}:{i}: {line.strip()}")
    assert not hits, "unsupported claims found:\n" + "\n".join(hits)
