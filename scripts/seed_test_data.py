#!/usr/bin/env python3
"""
Seed test data for StoreScout QA.

Usage:
    python scripts/seed_test_data.py
    python scripts/seed_test_data.py --reset   # delete and recreate all seed users

Requires env vars:
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY

All seed users get password: SeedPass123!
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SERVICE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
    sys.exit(1)

SEED_PASSWORD = "SeedPass123!"
NOW = datetime.now(timezone.utc)

SEED_USERS = [
    {
        "email": "seed-empty@storescout.test",
        "tier": "free",
        "max_competitors": 1,
        "scan_interval_hours": 168,
        "competitors": [],
        "description": "Free — no competitors",
    },
    {
        "email": "seed-free@storescout.test",
        "tier": "free",
        "max_competitors": 1,
        "scan_interval_hours": 168,
        "competitors": [
            {
                "store_url": "https://allbirds.com",
                "hostname": "allbirds.com",
                "display_name": "Allbirds",
                "scan_status": "done",
                "product_count": 120,
                "snapshots": 1,
                "change_events": 0,
            }
        ],
        "description": "Free — 1 competitor, scan complete",
    },
    {
        "email": "seed-free-limit@storescout.test",
        "tier": "free",
        "max_competitors": 1,
        "scan_interval_hours": 168,
        "competitors": [
            {
                "store_url": "https://gymshark.com",
                "hostname": "gymshark.com",
                "display_name": "Gymshark",
                "scan_status": "done",
                "product_count": 250,
                "snapshots": 1,
                "change_events": 0,
            }
        ],
        "description": "Free — at limit (adding 2nd triggers upgrade modal)",
    },
    {
        "email": "seed-scanning@storescout.test",
        "tier": "free",
        "max_competitors": 1,
        "scan_interval_hours": 168,
        "competitors": [
            {
                "store_url": "https://fashionnova.com",
                "hostname": "fashionnova.com",
                "display_name": "Fashion Nova",
                "scan_status": "scanning",
                "product_count": None,
                "snapshots": 0,
                "change_events": 0,
            }
        ],
        "description": "Free — stuck scan (tests recovery flow)",
    },
    {
        "email": "seed-pro@storescout.test",
        "tier": "pro",
        "max_competitors": 10,
        "scan_interval_hours": 24,
        "competitors": [
            {
                "store_url": "https://allbirds.com",
                "hostname": "allbirds.com",
                "display_name": "Allbirds",
                "scan_status": "done",
                "product_count": 120,
                "snapshots": 3,
                "change_events": 2,
            },
            {
                "store_url": "https://gymshark.com",
                "hostname": "gymshark.com",
                "display_name": "Gymshark",
                "scan_status": "done",
                "product_count": 250,
                "snapshots": 3,
                "change_events": 2,
            },
            {
                "store_url": "https://carhartt.com",
                "hostname": "carhartt.com",
                "display_name": "Carhartt",
                "scan_status": "done",
                "product_count": 400,
                "snapshots": 2,
                "change_events": 1,
            },
        ],
        "description": "Pro — 3 competitors, all scanned, 5 change_events total",
    },
    {
        "email": "seed-pro-alerts@storescout.test",
        "tier": "pro",
        "max_competitors": 10,
        "scan_interval_hours": 24,
        "competitors": [
            {
                "store_url": "https://huckberry.com",
                "hostname": "huckberry.com",
                "display_name": "Huckberry",
                "scan_status": "done",
                "product_count": 600,
                "snapshots": 2,
                "change_events": 6,
            },
            {
                "store_url": "https://chubbies.com",
                "hostname": "chubbies.com",
                "display_name": "Chubbies",
                "scan_status": "done",
                "product_count": 150,
                "snapshots": 2,
                "change_events": 4,
            },
        ],
        "description": "Pro — 2 competitors, 10 unread change_events",
    },
    {
        "email": "seed-agency@storescout.test",
        "tier": "agency",
        "max_competitors": 50,
        "scan_interval_hours": 12,
        "competitors": [
            {
                "store_url": "https://allbirds.com",
                "hostname": "allbirds.com",
                "display_name": "Allbirds",
                "scan_status": "done",
                "product_count": 120,
                "snapshots": 5,
                "change_events": 2,
            },
            {
                "store_url": "https://gymshark.com",
                "hostname": "gymshark.com",
                "display_name": "Gymshark",
                "scan_status": "done",
                "product_count": 250,
                "snapshots": 5,
                "change_events": 1,
            },
            {
                "store_url": "https://carhartt.com",
                "hostname": "carhartt.com",
                "display_name": "Carhartt",
                "scan_status": "done",
                "product_count": 400,
                "snapshots": 4,
                "change_events": 1,
            },
            {
                "store_url": "https://huckberry.com",
                "hostname": "huckberry.com",
                "display_name": "Huckberry",
                "scan_status": "done",
                "product_count": 600,
                "snapshots": 4,
                "change_events": 0,
            },
            {
                "store_url": "https://chubbies.com",
                "hostname": "chubbies.com",
                "display_name": "Chubbies",
                "scan_status": "done",
                "product_count": 150,
                "snapshots": 3,
                "change_events": 0,
            },
        ],
        "description": "Agency — 5 competitors, AI summary present",
    },
    {
        "email": "seed-failed@storescout.test",
        "tier": "free",
        "max_competitors": 1,
        "scan_interval_hours": 168,
        "competitors": [
            {
                "store_url": "https://notashopifystore.example.com",
                "hostname": "notashopifystore.example.com",
                "display_name": "Bad Store",
                "scan_status": "error",
                "error_message": "Failed to fetch products: Connection refused",
                "product_count": None,
                "snapshots": 0,
                "change_events": 0,
            }
        ],
        "description": "Free — scan_status=error",
    },
]

FIXTURE_SNAPSHOT = {
    "total_products": 0,
    "median_price": 0,
    "price_min": 0,
    "price_max": 0,
    "p25": 0,
    "p75": 0,
    "promo_rate": 0,
    "median_discount_pct": 0,
    "new_30d": 0,
    "new_60d": 0,
    "new_90d": 0,
    "launch_velocity": [],
    "newest_products": [],
    "winning_products": [],
    "products_by_price_range": {},
    "bucket_counts": {},
    "vendor_count": 0,
    "tag_count": 0,
    "market_position": "budget",
    "positioning_scores": {
        "premium": 20,
        "discount_aggression": 30,
        "launch_velocity": 40,
        "catalog_depth": 50,
    },
}


def headers():
    return {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def pg_headers():
    return {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def admin_url(path: str) -> str:
    return f"{SUPABASE_URL}/auth/v1/admin/{path}"


def rest_url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


def create_auth_user(email: str) -> str:
    """Create Supabase auth user, return user_id."""
    resp = httpx.post(
        admin_url("users"),
        headers=headers(),
        json={
            "email": email,
            "password": SEED_PASSWORD,
            "email_confirm": True,
        },
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create auth user {email}: {resp.text}")
    return resp.json()["id"]


def list_auth_users() -> dict[str, str]:
    """Return {email: user_id} for all existing auth users."""
    resp = httpx.get(
        admin_url("users") + "?per_page=1000",
        headers=headers(),
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to list auth users: {resp.text}")
    users = resp.json().get("users", [])
    return {u["email"]: u["id"] for u in users}


def delete_auth_user(user_id: str):
    resp = httpx.delete(
        admin_url(f"users/{user_id}"),
        headers=headers(),
        timeout=30,
    )
    if resp.status_code not in (200, 204):
        print(f"  WARN: Could not delete auth user {user_id}: {resp.text}")


def upsert_profile(user_id: str, email: str, spec: dict):
    resp = httpx.post(
        rest_url("user_profiles"),
        headers={**headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
        json={
            "id": user_id,
            "email": email,
            "tier": spec["tier"],
            "max_competitors": spec["max_competitors"],
            "scan_interval_hours": spec["scan_interval_hours"],
            "subscription_status": "active" if spec["tier"] != "free" else "inactive",
        },
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to upsert profile for {email}: {resp.text}")


def delete_user_data(user_id: str):
    """Delete competitors (cascades to snapshots, change_events) and profile."""
    httpx.delete(
        rest_url("competitors") + f"?user_id=eq.{user_id}",
        headers=pg_headers(),
        timeout=30,
    )
    httpx.delete(
        rest_url("user_profiles") + f"?id=eq.{user_id}",
        headers=pg_headers(),
        timeout=30,
    )


def insert_competitor(user_id: str, c: dict) -> str:
    """Insert competitor row, return competitor_id."""
    now_str = NOW.isoformat()
    payload = {
        "user_id": user_id,
        "store_url": c["store_url"],
        "hostname": c["hostname"],
        "display_name": c.get("display_name"),
        "scan_status": c.get("scan_status", "pending"),
        "is_active": True,
        "last_scanned_at": now_str if c.get("scan_status") in ("done", "error") else None,
        "next_scan_at": (NOW + timedelta(hours=24)).isoformat(),
        "product_count": c.get("product_count"),
        "error_message": c.get("error_message"),
    }
    resp = httpx.post(
        rest_url("competitors"),
        headers=headers(),
        json=payload,
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to insert competitor {c['store_url']}: {resp.text}")
    return resp.json()[0]["id"]


def insert_snapshots(competitor_id: str, c: dict):
    count = c.get("snapshots", 0)
    if count == 0:
        return
    product_count = c.get("product_count") or 50
    for i in range(count):
        scanned_at = (NOW - timedelta(days=(count - 1 - i) * 7)).isoformat()
        snapshot = {
            **FIXTURE_SNAPSHOT,
            "total_products": product_count + (i * 2),
            "median_price": round(49.99 + i * 5, 2),
            "promo_rate": round(15.0 + i * 2, 2),
            "new_30d": i * 3,
        }
        resp = httpx.post(
            rest_url("scan_snapshots"),
            headers=headers(),
            json={
                "competitor_id": competitor_id,
                "scanned_at": scanned_at,
                "product_count": snapshot["total_products"],
                "median_price": snapshot["median_price"],
                "promo_rate": snapshot["promo_rate"],
                "new_30d": snapshot["new_30d"],
                "snapshot_data": json.dumps(snapshot),
            },
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to insert snapshot: {resp.text}")


def insert_change_events(competitor_id: str, c: dict):
    count = c.get("change_events", 0)
    if count == 0:
        return
    change_types = ["price_change", "new_product", "product_removed", "discount_start"]
    for i in range(count):
        ctype = change_types[i % len(change_types)]
        detected_at = (NOW - timedelta(hours=(count - i) * 6)).isoformat()
        old_price = round(49.99 + i * 3, 2)
        new_price = round(old_price * 0.85, 2)
        resp = httpx.post(
            rest_url("change_events"),
            headers=headers(),
            json={
                "competitor_id": competitor_id,
                "detected_at": detected_at,
                "change_type": ctype,
                "product_handle": f"product-{i + 1}",
                "product_title": f"Sample Product {i + 1}",
                "product_url": f"{c['store_url']}/products/product-{i + 1}",
                "old_value": {"price": old_price},
                "new_value": {"price": new_price},
                "delta_pct": round((new_price - old_price) / old_price * 100, 2),
                "severity": "warning" if ctype == "price_change" else "info",
                "alert_sent": False,
            },
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to insert change_event: {resp.text}")


def insert_ai_summary(competitor_id: str, hostname: str):
    resp = httpx.post(
        rest_url("ai_summaries"),
        headers=headers(),
        json={
            "competitor_id": competitor_id,
            "generated_at": NOW.isoformat(),
            "model": "claude-haiku-4-5",
            "summary_text": (
                f"{hostname} has maintained a stable catalog of ~250 products at a median "
                "price of $54.99. This week they reduced prices on 12 items by an average "
                "of 18%, likely a targeted promotion ahead of the summer season. Their "
                "launch velocity has slowed to 4 new products in the last 30 days — down "
                "from 11 the prior month — suggesting they're consolidating rather than "
                "expanding. Consider running a competing promotion on your overlap SKUs "
                "before their sale window closes."
            ),
            "summary_type": "weekly",
            "input_tokens": 800,
            "output_tokens": 120,
        },
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        print(f"  WARN: Failed to insert AI summary for {competitor_id}: {resp.text}")


def seed_user(spec: dict, existing_users: dict[str, str]) -> tuple[str, str]:
    email = spec["email"]
    status = "created"

    if email in existing_users:
        print(f"  SKIP (already exists): {email}")
        return email, "skipped"

    user_id = create_auth_user(email)
    upsert_profile(user_id, email, spec)

    for c in spec.get("competitors", []):
        comp_id = insert_competitor(user_id, c)
        insert_snapshots(comp_id, c)
        insert_change_events(comp_id, c)
        if spec["tier"] == "agency" and c.get("snapshots", 0) > 0:
            insert_ai_summary(comp_id, c["hostname"])

    return email, status


def reset_user(spec: dict, existing_users: dict[str, str]) -> tuple[str, str]:
    email = spec["email"]
    if email in existing_users:
        user_id = existing_users[email]
        print(f"  RESET: deleting {email} ({user_id})")
        delete_user_data(user_id)
        delete_auth_user(user_id)
    user_id = create_auth_user(email)
    upsert_profile(user_id, email, spec)

    for c in spec.get("competitors", []):
        comp_id = insert_competitor(user_id, c)
        insert_snapshots(comp_id, c)
        insert_change_events(comp_id, c)
        if spec["tier"] == "agency" and c.get("snapshots", 0) > 0:
            insert_ai_summary(comp_id, c["hostname"])

    return email, "reset"


def main():
    parser = argparse.ArgumentParser(description="Seed StoreScout test data")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate all seed users")
    args = parser.parse_args()

    print(f"StoreScout seed script — {'RESET' if args.reset else 'IDEMPOTENT'} mode\n")
    print(f"Target: {SUPABASE_URL}\n")

    print("Fetching existing auth users...")
    existing = list_auth_users()
    seed_emails = {s["email"] for s in SEED_USERS}
    existing_seeds = {e: uid for e, uid in existing.items() if e in seed_emails}
    print(f"Found {len(existing_seeds)} existing seed user(s).\n")

    results = []
    for spec in SEED_USERS:
        print(f"→ {spec['email']}  [{spec['description']}]")
        try:
            if args.reset:
                email, status = reset_user(spec, existing_seeds)
            else:
                email, status = seed_user(spec, existing_seeds)
            results.append((email, spec["tier"], spec["description"], status, "OK"))
        except Exception as exc:
            results.append((spec["email"], spec["tier"], spec["description"], "error", str(exc)))
            print(f"  ERROR: {exc}")

    print("\n" + "=" * 90)
    print(f"{'Email':<40} {'Tier':<8} {'Status':<8} {'Note'}")
    print("-" * 90)
    for email, tier, desc, status, note in results:
        marker = "✓" if note == "OK" else "✗"
        print(f"{marker} {email:<38} {tier:<8} {status:<8} {desc if note == 'OK' else note}")
    print("=" * 90)

    errors = [r for r in results if r[4] != "OK"]
    if errors:
        print(f"\n{len(errors)} error(s). Fix above issues and re-run.")
        sys.exit(1)
    else:
        print(f"\nAll {len(results)} seed users ready. Password: {SEED_PASSWORD}")


if __name__ == "__main__":
    main()
