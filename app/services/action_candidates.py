"""Grounded Playbook candidates shared by synchronous fallback and AI prioritisation.
Public facts support investigation, not claims about sales, intent or profitability.
No network, generated metrics, integration requirement or price-position inference.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import math
from app.services.discovery_quality import tokens
from app.services.playbook_intelligence import _rec

VERSION = 1

def fresh(stamp, now):
    try:
        age = now - datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        return timedelta(0) <= age <= timedelta(days=8)
    except (ValueError, TypeError, AttributeError):
        return False


def pct(value):
    """Snapshot and change-event percentages use the explicit 0–100 contract."""
    try:
        n = float(value)
        return n if math.isfinite(n) and 0 <= n <= 100 else None
    except (TypeError, ValueError):
        return None


def build_candidates(rows, changes=(), business=None, own_snap=None, now=None):
    now = now or datetime.now(timezone.utc)
    business = business or {}
    own_snap = own_snap or {}
    own_fresh = fresh(own_snap.get('scanned_at'), now)
    own_index = ((own_snap.get('snapshot_data') or {}).get('_product_index') or {}) if own_fresh else {}
    focus = business.get('sells') or business.get('description') or ''
    context = f'Your stated business: {str(focus)[:180]}. ' if focus else 'Your product focus is not yet recorded. '
    valid = {r['competitor_id']: r for r in rows}
    out = []
    for row in rows:
        cid, host, snap = row['competitor_id'], row['hostname'], row['snap']
        stamp = snap.get('scanned_at')
        sd = snap.get('snapshot_data') or {}
        index = sd.get('_product_index') or {}
        complete = sd.get('catalog_complete') is True and not sd.get('catalog_truncated')
        names = [str(p.get('title') or h) for h,p in list(index.items())[:3] if isinstance(p, dict)]
        if not fresh(stamp, now):
            observed = f'{host} has no snapshot verified as fresh within the last eight days.'
            title = f'Refresh the evidence for {host}'
            action = 'Open the competitor and request a fresh scan before making a pricing or promotion decision.'
            status, priority, category = 'Investigate', 'medium', 'Operations'
        else:
            rate = pct(snap.get('promo_rate'))
            count = snap.get('product_count')
            observed = f'{host}: {count if count is not None else "unknown number of"} products in the observed catalog sample on {stamp[:10]}.'
            if rate is not None:
                observed += f' {rate:g}% of sampled products have a same-variant compare-at discount.'
            if names:
                observed += ' Examples: ' + ', '.join(names) + '.'
            title = f'Review comparable offers at {host}' if rate and rate >= 45 else f'Establish product comparability with {host}'
            action = ('Select the closest comparable product from this sample and your catalog; compare size, materials, '
                      'variant, delivery cost and currency. Record whether it serves the same buyer before responding.')
            if rate and rate >= 45:
                action += ' If the offer matters to your customers, assess a short bundle or shipping offer against your margin before matching a discount.'
            status, priority, category = 'Investigate' if rate and rate >= 45 else 'Watch', 'medium' if rate and rate >= 45 else 'low', 'Pricing'
        evidence = [observed, 'Coverage: ' + ('complete pagination reported by scanner' if complete else 'partial or unknown; not a whole-market conclusion')]
        missing = ['confirmed equivalent products', 'unit economics and margin', 'current inventory', 'sales and conversion performance']
        avoid = 'Do not infer competitor sales, intent or customer response. Do not change a price from a catalog-wide average or a single observation.'
        why = context + 'This is a tracked competitor; commercial overlap still needs confirmation.'
        p = _rec(f'baseline-{cid}', cid, host, category, title, observed, why,
                 'A catalog observation is a review starting point, not evidence that a response is needed.',
                 'Decide whether there is a comparable offer worth monitoring.',
                 [{'surface':'Product Pages','action':action}],
                 'A documented comparison may prevent an unnecessary promotion; no sales lift is predicted.',
                 evidence, confidence='estimated', priority=priority)
        p.update(decision=status, avoid=avoid, additional_data=missing, observed_at=stamp,
                 fact_ids=[f'snapshot:{cid}:{stamp}'], engine_version=VERSION,
                 fact_confidence='observed' if fresh(stamp, now) else 'stale')
        p['section'] = 'watch' if status == 'Watch' else 'right_now'
        out.append(p)

    for ch in changes:
        cid = ch.get('competitor_id')
        if cid not in valid or not fresh(ch.get('detected_at'), now):
            continue
        if ch.get('change_type') not in ('price_change','new_product','product_removed','availability_change','discount_start','discount_end'):
            continue
        row = valid[cid]
        title = ch.get('product_title') or ch.get('product_handle') or 'catalog item'
        event = ch['change_type'].replace('_',' ')
        observed = f'{row["hostname"]}: {event} recorded for {title} on {ch["detected_at"][:10]}.'
        old, new = ch.get('old_value'), ch.get('new_value')
        if old is not None or new is not None:
            observed += f' Recorded values: {old} → {new}.'
        overlap = []
        target = tokens(title)
        for handle, product in own_index.items():
            if not isinstance(product, dict):
                continue
            pt = tokens(product.get('title') or handle)
            if len(target & pt) >= 2:
                overlap.append(product.get('title') or handle)
        relevance = 'Possible own-catalog wording matches: ' + ', '.join(overlap[:3]) + '. These are not confirmed equivalents.' if overlap else 'No equivalent product in your own catalog has been established.'
        action = f'Open the recorded change for {title} and verify the current variant, price and availability. Compare the closest equivalent in your own catalog before deciding whether to respond.'
        evidence = [observed, relevance]
        key = ch.get('id') or hashlib.sha256((str(cid)+observed).encode()).hexdigest()[:16]
        p = _rec(f'event-{key}', cid, row['hostname'], 'Competitive Defense', f'Investigate {event}: {title}',
                 observed, context + relevance, 'The change may affect a comparable offer; demand and impact are unknown.',
                 'Confirm the change and decide whether it affects a product you sell.',
                 [{'surface':'Product Pages','action':action}],
                 'Focus review effort on a documented change; no revenue or conversion benefit is assumed.',
                 evidence, confidence='estimated', priority='high' if overlap else 'medium')
        p.update(decision='Investigate', avoid='Do not match a discount before checking product equivalence, stock and margin. A changed minimum price may reflect a variant change.',
                 additional_data=['confirmed variant equivalence','inventory for the affected product','margin','sales or conversion trend'],
                 observed_at=ch['detected_at'], fact_ids=[f'change:{key}'], engine_version=VERSION, fact_confidence='recorded change')
        # Urgency follows recorded magnitude, recency, and possible product relevance.
        p['source'] = 'change_event'
        p['priority'] = 40 + (20 if overlap else 0)
        if (now - datetime.fromisoformat(ch['detected_at'].replace('Z', '+00:00'))) <= timedelta(hours=48):
            p['priority'] += 10
        try:
            magnitude = abs(float(ch.get('delta_pct')))
            if math.isfinite(magnitude) and magnitude >= 10:
                p['priority'] += 10
        except (ValueError, TypeError):
            pass
        p['priority_label'] = 'high' if p['priority'] >= 70 else 'medium'
        out.append(p)
    # One baseline per competitor, at most two event reviews; a changed item outranks its baseline.
    event_counts, result = {}, []
    for p in sorted(out, key=lambda p:(p['priority'], p['id'].startswith('event-'), p.get('observed_at') or ''), reverse=True):
        cid = p['competitor_id']
        if p['id'].startswith('event-'):
            if event_counts.get(cid,0) >= 2:
                continue
            event_counts[cid] = event_counts.get(cid,0)+1
        elif event_counts.get(cid):
            continue
        result.append(p)
    return result[:8]


def load_context(db, user_id, competitors):
    """Read only public snapshots and user-supplied context; no provider calls."""
    business, own, rows = {}, {}, []
    try:
        res = db.table('business_profiles').select('*').eq('user_id', user_id).maybe_single().execute()
        business = (res.data or {}) if res else {}
    except Exception:
        pass
    for comp in competitors:
        res = db.table('scan_snapshots').select('product_count, median_price, promo_rate, snapshot_data, scanned_at').eq('competitor_id', comp['id']).order('scanned_at', desc=True).limit(1).maybe_single().execute()
        snap = (res.data or {}) if res else {}
        if comp.get('is_my_store'):
            own = snap
        else:
            rows.append({'competitor_id':comp['id'], 'hostname':comp['hostname'], 'snap':snap})
    ids = [r['competitor_id'] for r in rows]
    changes = []
    if ids:
        res = db.table('change_events').select('*').in_('competitor_id',ids).gte('detected_at',(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()).order('detected_at',desc=True).limit(150).execute()
        changes = res.data or []
    return build_candidates(rows, changes, business, own)


def prioritise_candidates(candidates, model_choices):
    """Model can select/reorder known actions only, never replace facts or invent advice."""
    known = {p['id']:p for p in candidates}
    chosen = []
    for entry in model_choices if isinstance(model_choices, list) else []:
        key = entry.get('candidate_id') if isinstance(entry, dict) else None
        if key in known and key not in chosen:
            chosen.append(key)
    order = {key:i for i,key in enumerate(chosen)}
    # AI may break ties but cannot demote grounded urgency or fabricate confidence.
    return sorted(candidates, key=lambda p:(-p['priority'], order.get(p['id'],len(chosen))))
