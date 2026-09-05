"""Bounded, inspectable relevance scoring. Platform certainty is an eligibility gate.
Scores are ranking heuristics, never probabilities. Missing evidence stays unknown.
"""
from datetime import datetime, timezone, timedelta
from app.services.store_dna import normalize_keywords, category_relation

# Small spelling/product vocabulary; not a model or a category catalogue.
_ALIASES = {'trainers': 'shoe', 'trainer': 'shoe', 'sneaker': 'shoe',
            'sneakers': 'shoe', 'shoes': 'shoe', 'moisturiser': 'moisturizer',
            'sleepsuit': 'sleepwear'}

def tokens(value):
    out = set()
    for t in normalize_keywords(value, limit=160):
        t = _ALIASES.get(t, t)
        if len(t) > 4 and t.endswith('s') and not t.endswith(('ss', 'us')):
            t = t[:-1]
        out.add(t)
    return out


def relevance(row, user):
    user = user or {}
    query = tokens([user.get('dna_keywords'), user.get('sells'), user.get('description')])
    # Prefer observed products; fall back to metadata, with lower confidence.
    product = tokens([row.get('product_types'), row.get('product_titles')])
    observed = bool(product)
    if not product:
        product = tokens([row.get('dna_keywords'), (row.get('store_dna') or {}).get('keywords'),
                          row.get('subcategory'), row.get('description')])
    overlap = query & product
    coverage = len(overlap) / max(1, len(query))
    precision = len(overlap) / max(1, len(product))
    score = 65 * coverage + 15 * precision
    if not observed:
        score *= .8
    relation = category_relation(row.get('category'), user.get('category'))
    if relation == 'same':
        score += 5
    elif relation == 'contradiction' and coverage < .75:
        score -= 15
    audience = tokens(user.get('target_customer'))
    other_audience = tokens(row.get('target_customer'))
    # Absence of common audience words is uncertainty, not proof of incompatibility.
    if audience and other_audience:
        score += 10 * len(audience & other_audience) / len(audience | other_audience)
    tiers = ['budget', 'mid-market', 'premium', 'luxury']
    a, b = row.get('pricing_tier'), user.get('pricing_tier')
    if a in tiers and b in tiers:
        score += 5 - 5 * abs(tiers.index(a) - tiers.index(b))
    return {'score': round(max(0, score), 2), 'matched_terms': sorted(overlap),
            'product_evidence': observed, 'query_coverage': round(coverage, 3),
            'assessment': 'candidate for review' if overlap else 'insufficient product evidence'}


def is_recent_verified(row, minimum=60, now=None):
    """A prior verification is reusable for 60 days, not indefinitely."""
    try:
        stamp = datetime.fromisoformat(row.get('last_verified_at', '').replace('Z', '+00:00'))
        now = now or datetime.now(timezone.utc)
        age = now - stamp
        return (row.get('status') == 'verified'
                and float(row.get('verification_confidence') or 0) >= minimum
                and timedelta(0) <= age <= timedelta(days=60)
                and 'Product catalog accessible' in (row.get('verification_signals') or []))
    except (ValueError, TypeError):
        return False
