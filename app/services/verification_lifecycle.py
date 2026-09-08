"""Evidence and retry policy shared by tracked scans and index verification.

No network or database calls: an attempt is never a successful observation.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json

STATES = frozenset({"verified_shopify", "probable_shopify", "temporarily_unreachable",
                    "dead_domain", "blocked", "password_protected", "no_readable_catalog",
                    "non_shopify", "ambiguous", "storefront_unavailable"})
TERMINAL = frozenset({"dead_domain", "non_shopify"})
RENEW_AFTER = timedelta(days=53)  # seven days of headroom before eligibility expires


def timestamp(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp if stamp.tzinfo is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def valid_products(products):
    """A partial nonempty sample is sufficient; malformed entries are not evidence."""
    return (isinstance(products, list) and bool(products)
            and all(isinstance(p, dict) and p.get("id")
                    and isinstance(p.get("handle"), str) and p["handle"].strip()
                    and isinstance(p.get("title"), str) and p["title"].strip()
                    and isinstance(p.get("variants"), list) and bool(p["variants"])
                    and all(isinstance(v, dict) and v.get("id") for v in p["variants"])
                    for p in products))


def successful_catalog(products, now, source):
    if not valid_products(products):
        raise ValueError("A readable Shopify product sample is required")
    # Ignore price/stock changes here. Knowledge describes identity/products.
    facts = sorted((str(p["id"]), p["handle"], p.get("title"), p.get("product_type"))
                   for p in products[:40])
    return {"version": 1, "state": "readable", "observed_at": now.isoformat(),
            "source": source, "sample_count": len(products),
            "signature": hashlib.sha256(json.dumps(facts, ensure_ascii=False).encode()).hexdigest()}


def successful_fields(observation, confidence=100, signals=None):
    stamp = timestamp(observation.get("observed_at"))
    if (observation.get("version") != 1 or observation.get("state") != "readable" or not stamp
            or not isinstance(observation.get("sample_count"), int) or observation["sample_count"] <= 0):
        raise ValueError("Invalid successful catalog observation")
    return {"status": "verified", "verification_state": "verified_shopify",
            "catalog_observation": observation, "verification_confidence": confidence,
            "verification_signals": list(dict.fromkeys([*(signals or []), "Product catalog accessible"])),
            "last_verified_at": stamp.isoformat(), "verified_at": stamp.isoformat(),
            "last_light_scanned_at": stamp.isoformat(), "last_attempted_at": stamp.isoformat(),
            "next_verification_at": (stamp + RENEW_AFTER).isoformat(),
            "verification_attempts": 0, "verification_token": None,
            "failure_reason": None, "rejection_reason": None}


def classify_probe(result, minimum=60):
    state = result.get("access_state")
    if state in STATES - {"verified_shopify", "probable_shopify"}:
        return state
    if result.get("monitorable") and result.get("catalog_observation"):
        return "verified_shopify" if result.get("confidence", 0) >= minimum else "probable_shopify"
    if not result.get("reachable"):
        return "temporarily_unreachable"
    if any("Shopify" in s or "Storefront API" in s for s in result.get("signals", [])):
        return "probable_shopify"
    return "ambiguous"


def retry_fields(row, state, now):
    """Preserve past successful facts, but withdraw current discovery eligibility."""
    attempts = max(0, int(row.get("verification_attempts") or 0)) + 1
    base = 24 if state in {"blocked", "password_protected", "no_readable_catalog", "storefront_unavailable"} else 1
    hours = min(168, base * 2 ** min(attempts - 1, 8))
    if state in TERMINAL:
        hours = 30 * 24  # evidence can change; even definitive outcomes can be revisited
    jitter = int(hashlib.sha256(row["domain"].encode()).hexdigest()[:4], 16) % 601
    return {"status": "rejected" if state in TERMINAL else "failed", "verification_state": state,
            "last_attempted_at": now.isoformat(), "verification_attempts": attempts,
            "next_verification_at": (now + timedelta(hours=hours, seconds=jitter)).isoformat(),
            "verification_token": None, "failure_reason": state,
            "rejection_reason": state if state in TERMINAL else None}


def due_at(row):
    explicit = timestamp(row.get("next_verification_at"))
    if explicit:
        return explicit
    if row.get("status") == "verified":
        observed = timestamp((row.get("catalog_observation") or {}).get("observed_at"))
        observed = observed or timestamp(row.get("last_verified_at"))
        if observed:
            return observed + RENEW_AFTER
    return timestamp(row.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)


def plan_verification(rows, now, limit=100):
    """Bounded round-robin across lifecycle lanes; oldest work first per lane.

    With small batches rotate lanes per 15-minute slot, matching the existing
    schedule. This avoids a permanent discovered/candidate/retry/renewal priority.
    """
    lanes = [[], [], [], []]
    for row in rows:
        if row.get("status") not in {"discovered", "candidate", "failed", "rejected", "verified"}:
            continue
        if due_at(row) > now:
            continue
        lane = {"discovered": 0, "candidate": 1, "verified": 3}.get(row.get("status"), 2)
        lanes[lane].append(row)
    for lane in lanes:
        lane.sort(key=lambda r: (due_at(r), r["domain"]))
    start = int(now.timestamp() // 900) % 4
    work, seen = [], set()
    while any(lanes) and len(work) < max(1, min(limit, 200)):
        for i in range(4):
            lane = lanes[(i + start) % 4]
            if lane:
                row = lane.pop(0)
                if row["domain"] not in seen:
                    work.append(row)
                    seen.add(row["domain"])
                if len(work) >= max(1, min(limit, 200)):
                    break
    return work
