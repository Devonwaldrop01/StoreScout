"""Disabled-by-default, exact-manifest verification. No acquisition or AI."""
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

from fastapi import HTTPException

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "config/verification-canary.json"
probe_context = ContextVar("canary_probe", default=None)


def validate_manifest(manifest):
    entries = manifest.get("stores", [])
    if manifest.get("version") != 1 or len(entries) != 12:
        raise ValueError("canary requires exactly 12 entries")
    domains = [entry.get("domain", "") for entry in entries]
    if len(set(domains)) != 12 or any(not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", d) for d in domains):
        raise ValueError("canary domains must be unique exact lowercase hostnames")
    for entry in entries:
        stamp = datetime.fromisoformat(entry["expected_updated_at"])
        if stamp.tzinfo is None:
            raise ValueError("canary timestamp must include timezone")
    return manifest


def load_manifest(settings, *, require_enabled=True):
    raw = MANIFEST_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    manifest = validate_manifest(json.loads(raw))
    if require_enabled:
        if not getattr(settings, "store_index_canary_enabled", False):
            raise HTTPException(403, "canary disabled")
        if getattr(settings, "store_index_canary_manifest_sha256", "") != digest:
            raise HTTPException(409, "canary manifest digest mismatch")
        if manifest.get("live_rows_confirmed") is not True:
            raise HTTPException(409, "canary live row preflight incomplete")
        expires = datetime.fromisoformat(manifest["expires_at"])
        if expires.tzinfo is None or datetime.now(timezone.utc) >= expires:
            raise HTTPException(409, "canary manifest expired")
    return manifest, digest


def same_row_version(row, entry):
    if not row or row.get("domain") != entry["domain"]:
        return False
    try:
        return datetime.fromisoformat(row["updated_at"]) == datetime.fromisoformat(entry["expected_updated_at"])
    except (KeyError, ValueError, TypeError):
        return False


def ledger_key(digest):
    return f"canary:verification:{digest}"


class ProbeGuard:
    """Four fixed HTTPS endpoints, no redirects/retries, halt on protection."""
    def __init__(self, domain):
        self.domain, self.requests = domain, []
        self.deadline = time.monotonic() + 50
        self.stop_state = None
        self.stop_reason = None
        self.urls = {f"https://{domain}{path}" for path in (
            "/", "/cart.js", "/products.json?limit=250", "/collections.json?limit=50")}

    def get(self, client, url, timeout, use_curl):
        if self.stop_reason:
            raise RuntimeError("canary probe halted")
        remaining = self.deadline - time.monotonic()
        if url not in self.urls or url in {r["url"] for r in self.requests} or len(self.requests) >= 4 or remaining <= 0:
            self.stop_state, self.stop_reason = "temporarily_unreachable", "request_budget_or_scope"
            raise RuntimeError("canary request refused")
        event = {"url": url, "started": time.monotonic()}
        self.requests.append(event)
        try:
            kwargs = {"allow_redirects": False} if use_curl else {"follow_redirects": False}
            response = client.get(url, timeout=min(timeout, remaining), **kwargs)
            event.update(status=response.status_code, seconds=time.monotonic()-event.pop("started"))
            body = response.content
            if len(body) > 8 * 1024 * 1024:
                self.stop_state, self.stop_reason = "temporarily_unreachable", "body_limit"
                raise RuntimeError("canary body limit")
            lower = body[:400_000].lower()
            password = b'shopify-section-main-password' in lower or b'action="/password"' in lower
            challenged = (response.status_code in {401, 403, 429, 430} or
                          b'cf-chl-' in lower or b'challenge-platform' in lower or b'verifying your connection' in lower)
            if password:
                self.stop_state, self.stop_reason = "password_protected", "merchant_protection"
            elif challenged:
                self.stop_state, self.stop_reason = "blocked", "merchant_protection"
            elif response.status_code == 402:
                self.stop_state, self.stop_reason = "storefront_unavailable", "merchant_unavailable"
            elif 300 <= response.status_code < 400:
                self.stop_state, self.stop_reason = "ambiguous", "redirect_not_followed"
            event["bytes"] = len(body)
            return response
        except Exception:
            event.pop("started", None)
            self.stop_state = self.stop_state or "temporarily_unreachable"
            self.stop_reason = self.stop_reason or "transport_failure"
            raise


def verify_canary(body, settings, db_factory):
    # Validate authorization, immutable membership and order BEFORE DB/fetches.
    from app.core.index_hold import require_index_writes
    require_index_writes()
    manifest, digest = load_manifest(settings)
    if set(body) != {"domain", "manifest_sha256"} or body["manifest_sha256"] != digest:
        raise HTTPException(422, "exact domain and manifest digest required")
    entries = {e["domain"]: e for e in manifest["stores"]}
    domain = body["domain"]
    if domain not in entries:
        raise HTTPException(403, "domain outside canary manifest")

    from app.services.index_lease import acquire_stage
    try:
        lease = acquire_stage("stage_verification", 1500)
    except Exception as exc:
        raise HTTPException(503, "canary coordination unavailable") from exc
    if lease is None:
        raise HTTPException(409, "verification stage busy")
    try:
        lease.start()
        lease.require()
        client = lease.client
        key = ledger_key(digest)
        saved = client.get(key)
        if not saved:
            raise HTTPException(409, "canary ledger not armed")
        ledger = json.loads(saved)
        completed = ledger.get("completed", [])
        ordered = [e["domain"] for e in manifest["stores"]]
        if (ledger.get("manifest_sha256") != digest or ledger.get("state") != "ready" or
                not isinstance(completed, list) or completed != ordered[:len(completed)] or
                len(completed) >= 12 or ordered[len(completed)] != domain):
            raise HTTPException(409, "canary stopped, already attempted, or out of order")
        # Missing/evicted ledger is never implicitly re-created. Ambiguous
        # delivery remains inflight until explicit operator reconciliation.
        ledger.update(state="inflight", domain=domain)
        if not client.set(key, json.dumps(ledger), xx=True):
            raise HTTPException(503, "canary ledger lost")
        db = db_factory()
        guard = ProbeGuard(domain)
        context = probe_context.set(guard)
        try:
            from app.services.store_index import verify_and_store
            result = verify_and_store(db, domain, "controlled_canary", expected_row=entries[domain])
        finally:
            probe_context.reset(context)
        lease.require()
        completed = [*completed, domain]
        # An ordinary classified access outcome (e.g. no readable catalog)
        # belongs in the sample. Lost preconditions/ownership stop the run.
        stop = guard.stop_reason or ("verification_skipped_or_unknown" if result.get("outcome") not in {"verified", "failed", "rejected"} else None)
        # Three sentinels require an explicit operator checkpoint before the
        # remaining nine. It cannot auto-advance through that boundary.
        state = "stopped" if stop else "checkpoint" if len(completed) == 3 else "complete" if len(completed) == 12 else "ready"
        evidence = {**result, "requests": guard.requests, "request_count": len(guard.requests), "stop_reason": stop}
        ledger.update(state=state, completed=completed, reason=stop,
                      outcomes=[*ledger.get("outcomes", []), evidence])
        if not client.set(key, json.dumps(ledger), xx=True):
            raise HTTPException(503, "canary result delivery unknown")
        return {**result, "manifest_sha256": digest, "canary_state": state,
                "requests": guard.requests, "request_count": len(guard.requests), "stop_reason": stop}
    finally:
        lease.release()
