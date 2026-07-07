"""
Internal lead-pipeline API (growth tooling — never customer-facing).

All endpoints live under /api/v1/admin/leads and require X-Admin-Token ==
ADMIN_TOKEN; while that env var is empty the whole surface is hard-disabled.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/leads", tags=["leads"])

PIPELINE_STAGES = [
    "discovered", "qualified", "research_complete", "ready", "contacted",
    "replied", "demo_scheduled", "trial_started", "customer", "lost", "never_contact",
]

_LIST_FIELDS = (
    "id, domain, brand_name, category, subcategory, business_stage, pricing_tier, "
    "lead_score, qualification_score, score_reasons, disqualifiers, outreach_status, "
    "research_status, competitors_found, generated_insights, recommended_angle, "
    "suggested_subject, suggested_email, notes, assigned_to, created_at, updated_at"
)


def _require_admin(token: Optional[str]) -> None:
    settings = get_settings()
    if not settings.admin_token or token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("")
def list_leads(
    status: str = "",
    category: str = "",
    q: str = "",
    limit: int = 100,
    x_admin_token: Optional[str] = Header(default=None),
):
    _require_admin(x_admin_token)
    db = get_supabase()
    limit = max(1, min(limit, 200))

    rows = []
    try:
        query = db.table("lead_prospects")\
            .select(_LIST_FIELDS)\
            .order("lead_score", desc=True)\
            .order("created_at", desc=True)\
            .limit(limit)
        if status:
            query = query.eq("outreach_status", status)
        if category:
            query = query.eq("category", category)
        if q:
            query = query.or_(f"domain.ilike.%{q}%,brand_name.ilike.%{q}%")
        rows = query.execute().data or []
    except Exception as exc:
        logger.warning("leads list failed (migration 009 applied?): %s", exc)

    # Pipeline summary + today's count
    counts: dict = {}
    new_today = 0
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
        agg = db.table("lead_prospects").select("outreach_status, created_at").limit(5000).execute()
        for r in agg.data or []:
            counts[r["outreach_status"]] = counts.get(r["outreach_status"], 0) + 1
            if (r.get("created_at") or "") >= today:
                new_today += 1
    except Exception:
        pass

    return {"data": {"rows": rows, "counts": counts, "new_today": new_today, "stages": PIPELINE_STAGES}}


class LeadUpdate(BaseModel):
    outreach_status: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


@router.patch("/{lead_id}")
def update_lead(lead_id: str, body: LeadUpdate, x_admin_token: Optional[str] = Header(default=None)):
    _require_admin(x_admin_token)
    if body.outreach_status is not None and body.outreach_status not in PIPELINE_STAGES:
        raise HTTPException(status_code=422, detail=f"outreach_status must be one of {PIPELINE_STAGES}")

    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=422, detail="nothing to update")
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    db = get_supabase()
    res = db.table("lead_prospects").update(fields).eq("id", lead_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="lead not found")
    return {"data": res.data[0]}


class RunBody(BaseModel):
    limit: int = 5


@router.post("/run")
def run_lead_discovery(body: RunBody, x_admin_token: Optional[str] = Header(default=None)):
    """Small manual discovery run for testing. Bypasses LEAD_ENGINE_ENABLED;
    the quality threshold and target cap still apply."""
    _require_admin(x_admin_token)
    limit = max(1, min(body.limit, 50))

    from app.tasks.lead_engine import discover_leads_daily
    try:
        task = discover_leads_daily.delay(limit_override=limit, force=True)
        return {"status": "queued", "task_id": str(task.id), "limit": limit}
    except Exception as exc:
        logger.warning("leads run: Celery unavailable (%s) — running inline", exc)
        result = discover_leads_daily(limit_override=limit, force=True)
        return {"status": "completed_inline", "result": result, "limit": limit}
