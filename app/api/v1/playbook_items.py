"""
Playbook items — persisted user tasks created from recommendations anywhere
in the app ("Save to Playbook"). Server-side status/outcome/notes close the
action loop: detect → explain → recommend → save → act → track outcome.

Saves are idempotent: the same recommendation saved twice returns the
existing row (dedupe_key = source_type:source_ref:title).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.core.auth import get_effective_user_id
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playbook-items", tags=["playbook-items"])

SOURCE_TYPES = {"signal", "gap", "winning_product", "pricing", "brief", "pro_analysis", "manual"}
STATUSES = {"pending", "done", "dismissed"}
OUTCOMES = {"worked", "too_early", "not_relevant"}
PRIORITIES = {"high", "medium", "low"}

_FIELDS = (
    "id, source_type, source_ref, competitor_id, hostname, title, reason, evidence, "
    "priority, due_at, status, outcome, notes, created_at, updated_at, completed_at"
)


class CreateItem(BaseModel):
    source_type: str
    title: str
    source_ref: Optional[str] = None
    competitor_id: Optional[str] = None
    hostname: Optional[str] = None
    reason: Optional[str] = None
    evidence: Optional[str] = None
    priority: str = "medium"
    due_at: Optional[str] = None

    @field_validator("source_type")
    @classmethod
    def _valid_source(cls, v: str) -> str:
        if v not in SOURCE_TYPES:
            raise ValueError(f"source_type must be one of {sorted(SOURCE_TYPES)}")
        return v

    @field_validator("priority")
    @classmethod
    def _valid_priority(cls, v: str) -> str:
        return v if v in PRIORITIES else "medium"

    @field_validator("title")
    @classmethod
    def _valid_title(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("title required")
        return v[:200]


@router.post("")
def create_item(body: CreateItem, user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    dedupe = hashlib.sha1(
        f"{body.source_type}:{body.source_ref or ''}:{body.title.lower()}".encode()
    ).hexdigest()[:32]

    # Idempotent: saving the same recommendation twice returns the existing row
    try:
        existing = db.table("playbook_items")\
            .select(_FIELDS)\
            .eq("user_id", user_id)\
            .eq("dedupe_key", dedupe)\
            .maybe_single()\
            .execute()
        if existing and existing.data:
            return {"data": existing.data, "created": False}
    except Exception:
        pass

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "user_id": user_id,
        "source_type": body.source_type,
        "source_ref": (body.source_ref or "")[:200] or None,
        "competitor_id": body.competitor_id,
        "hostname": (body.hostname or "")[:120] or None,
        "title": body.title,
        "reason": (body.reason or "")[:500] or None,
        "evidence": (body.evidence or "")[:500] or None,
        "priority": body.priority,
        "due_at": body.due_at,
        "status": "pending",
        "dedupe_key": dedupe,
        "created_at": now,
        "updated_at": now,
    }
    try:
        res = db.table("playbook_items").insert(row).execute()
    except Exception as exc:
        logger.error("playbook item insert failed for user %s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Could not save — apply migration 010 if this persists")
    return {"data": (res.data or [row])[0], "created": True}


@router.get("")
def list_items(status: str = "", user_id: str = Depends(get_effective_user_id)):
    db = get_supabase()
    try:
        q = db.table("playbook_items")\
            .select(_FIELDS)\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(200)
        if status and status in STATUSES:
            q = q.eq("status", status)
        res = q.execute()
        return {"data": res.data or []}
    except Exception as exc:
        # Table missing (pre-migration) → empty list, not a 500
        logger.warning("playbook items list failed: %s", exc)
        return {"data": []}


class UpdateItem(BaseModel):
    status: Optional[str] = None
    outcome: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[str] = None
    due_at: Optional[str] = None


@router.patch("/{item_id}")
def update_item(item_id: str, body: UpdateItem, user_id: str = Depends(get_effective_user_id)):
    if body.status is not None and body.status not in STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(STATUSES)}")
    if body.outcome is not None and body.outcome not in OUTCOMES:
        raise HTTPException(status_code=422, detail=f"outcome must be one of {sorted(OUTCOMES)}")
    if body.priority is not None and body.priority not in PRIORITIES:
        raise HTTPException(status_code=422, detail=f"priority must be one of {sorted(PRIORITIES)}")

    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=422, detail="nothing to update")
    now = datetime.now(timezone.utc).isoformat()
    fields["updated_at"] = now
    if body.status == "done":
        fields["completed_at"] = now
    elif body.status == "pending":
        fields["completed_at"] = None

    db = get_supabase()
    res = db.table("playbook_items").update(fields)\
        .eq("id", item_id).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="item not found")
    return {"data": res.data[0]}
