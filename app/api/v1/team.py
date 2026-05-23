from __future__ import annotations
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

import resend
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.config import get_settings
from app.core.database import get_supabase

router = APIRouter(prefix="/team", tags=["team"])
logger = logging.getLogger(__name__)

SEAT_LIMIT = 2


class InviteRequest(BaseModel):
    email: str


# ── helpers ───────────────────────────────────────────────────────────────────

def _assert_agency(db, user_id: str) -> None:
    user = db.table("user_profiles").select("tier").eq("id", user_id).maybe_single().execute()
    if (user.data or {}).get("tier") != "agency":
        raise HTTPException(403, "Team seats require the Agency plan")


def _invite_html(from_email: str, invite_url: str, settings) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;padding:0;background:#060d18;"
        "font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif'>"
        "<div style='max-width:520px;margin:0 auto;padding:40px 20px'>"
        "<div style='margin-bottom:24px'>"
        "<span style='color:#a3f000;font-weight:700;font-size:16px'>StoreScout</span>"
        "</div>"
        "<div style='background:#0e1d35;border:1px solid #1e3a5f;border-radius:12px;padding:28px'>"
        f"<h2 style='color:#eef3fa;font-size:18px;font-weight:700;margin:0 0 10px'>"
        f"You've been invited to a StoreScout team</h2>"
        f"<p style='color:#6b7fa3;font-size:14px;line-height:1.6;margin:0 0 20px'>"
        f"<strong style='color:#c8d8f0'>{from_email}</strong> invited you to access their "
        f"competitor intelligence dashboard — prices, launches, discounts, and AI insights "
        f"across all their tracked stores.</p>"
        f"<a href='{invite_url}' style='display:inline-block;background:#a3f000;color:#060d18;"
        f"padding:13px 24px;border-radius:10px;text-decoration:none;font-weight:700;font-size:14px'>"
        f"Accept invite →</a>"
        f"<p style='color:#3a5068;font-size:12px;margin:20px 0 0'>"
        f"Or copy this link: <span style='color:#6b7fa3;word-break:break-all'>{invite_url}</span></p>"
        "</div>"
        "<p style='color:#1e3a5f;font-size:11px;text-align:center;margin-top:24px'>"
        "StoreScout &nbsp;·&nbsp; Shopify competitor intelligence</p>"
        "</div></body></html>"
    )


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/members")
def list_members(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    _assert_agency(db, user_id)
    result = db.table("team_members")\
        .select("id, invited_email, status, invited_at, accepted_at")\
        .eq("owner_id", user_id)\
        .neq("status", "removed")\
        .order("invited_at")\
        .execute()
    return {"data": result.data or []}


@router.post("/invite")
def invite_member(body: InviteRequest, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    settings = get_settings()
    _assert_agency(db, user_id)

    active = db.table("team_members")\
        .select("id", count="exact")\
        .eq("owner_id", user_id)\
        .in_("status", ["pending", "active"])\
        .execute()
    if (active.count or 0) >= SEAT_LIMIT:
        raise HTTPException(
            400,
            f"Agency plan includes {SEAT_LIMIT} team seats. Remove an existing member to invite someone new."
        )

    email = body.email.strip().lower()

    existing = db.table("team_members")\
        .select("id, status")\
        .eq("owner_id", user_id)\
        .eq("invited_email", email)\
        .maybe_single()\
        .execute()

    if existing and existing.data:
        s = existing.data["status"]
        if s == "active":
            raise HTTPException(400, "This person is already a team member.")
        if s == "pending":
            raise HTTPException(400, "An invite is already pending for this email.")

    token = secrets.token_urlsafe(32)
    db.table("team_members").insert({
        "owner_id": user_id,
        "invited_email": email,
        "status": "pending",
        "invite_token": token,
        "invited_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    owner = db.table("user_profiles").select("email").eq("id", user_id).maybe_single().execute()
    owner_email = (owner.data or {}).get("email") or "your team"

    invite_url = f"{settings.public_base_url}/invite/{token}"
    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from,
            "to": email,
            "subject": f"{owner_email} invited you to their StoreScout team",
            "html": _invite_html(owner_email, invite_url, settings),
        })
    except Exception as exc:
        logger.error("Invite email failed: %s", exc)

    return {"status": "invited"}


@router.delete("/members/{member_id}", status_code=204)
def remove_member(member_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    row = db.table("team_members")\
        .select("id")\
        .eq("id", member_id)\
        .eq("owner_id", user_id)\
        .maybe_single()\
        .execute()
    if not row or not row.data:
        raise HTTPException(404, "Member not found")
    db.table("team_members").update({"status": "removed"}).eq("id", member_id).execute()


@router.get("/invite/{token}")
def get_invite_details(token: str):
    """Public — returns context for the invite accept page."""
    db = get_supabase()
    row = db.table("team_members")\
        .select("invited_email, status, owner_id")\
        .eq("invite_token", token)\
        .maybe_single()\
        .execute()
    if not row or not row.data:
        raise HTTPException(404, "Invite not found or expired")
    if row.data["status"] != "pending":
        raise HTTPException(400, "This invite has already been used or was removed")
    owner = db.table("user_profiles").select("email")\
        .eq("id", row.data["owner_id"]).maybe_single().execute()
    return {"data": {
        "invited_email": row.data["invited_email"],
        "owner_email": (owner.data or {}).get("email") or "",
    }}


@router.post("/accept")
def accept_invite(body: dict, user_id: str = Depends(get_current_user_id)):
    token = (body.get("token") or "").strip()
    if not token:
        raise HTTPException(400, "Missing token")

    db = get_supabase()
    row = db.table("team_members")\
        .select("id, invited_email, status, owner_id")\
        .eq("invite_token", token)\
        .maybe_single()\
        .execute()
    if not row or not row.data:
        raise HTTPException(404, "Invite not found or expired")
    if row.data["status"] != "pending":
        raise HTTPException(400, "This invite has already been used")

    # Verify the accepting user's email matches the invite
    try:
        auth_user = db.auth.admin.get_user_by_id(user_id)
        user_email = (auth_user.user.email or "").strip().lower() if auth_user.user else ""
    except Exception:
        user_email = ""

    if user_email != row.data["invited_email"]:
        raise HTTPException(
            403,
            f"This invite was sent to {row.data['invited_email']}. "
            f"Please sign in with that email address to accept."
        )

    db.table("team_members").update({
        "status": "active",
        "member_id": user_id,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", row.data["id"]).execute()

    return {"status": "accepted"}
