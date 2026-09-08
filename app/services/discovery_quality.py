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
    from app.services.product_intent import product_intent_check
    intent = product_intent_check(row,user)
    return {'score': round(max(0, score), 2), 'matched_terms': sorted(overlap),
            'intent':intent,
            'product_evidence': observed, 'query_coverage': round(coverage, 3),
            'assessment': 'candidate for review' if overlap else 'insufficient product evidence'}


def is_classification_usable(row, minimum=55, now=None):
    from app.services.verification_lifecycle import timestamp
    score = row.get('category_confidence')
    if score is not None and score < minimum:
        return False
    obs = row.get('catalog_observation') or {}
    if obs.get('classification_state') == 'provisional':
        until = timestamp(obs.get('classification_valid_until'))
        return bool(until and (now or datetime.now(timezone.utc)) < until)
    return obs.get('classification_state') not in ('pending','uncertain')


def is_recent_verified(row, minimum=60, now=None):
    """A prior verification is reusable for 60 days, not indefinitely."""
    from app.services.verification_lifecycle import timestamp
    now = now or datetime.now(timezone.utc)
    observation = row.get('catalog_observation')
    if observation is not None:
        if (not isinstance(observation, dict) or observation.get('version') != 1
                or observation.get('state') != 'readable'
                or not isinstance(observation.get('sample_count'), int)
                or observation['sample_count'] <= 0):
            return False
        stamp = timestamp(observation.get('observed_at'))
    else:
        # No retrospective promotion of historical "Actively scanned" rows.
        # They need a new successful observation through the shared contract.
        stamp = timestamp(row.get('last_verified_at'))
        if 'Product catalog accessible' not in (row.get('verification_signals') or []):
            return False
    try:
        return bool(stamp and row.get('status') == 'verified'
                    and row.get('verification_state') in (None, 'verified_shopify')
                    and float(row.get('verification_confidence') or 0) >= minimum
                    and timedelta(0) <= now - stamp <= timedelta(days=60))
    except (ValueError, TypeError):
        return False
