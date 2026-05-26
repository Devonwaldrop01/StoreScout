from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_effective_user_id
from app.core.config import get_settings
from app.core.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])
settings = get_settings()


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    message: str = Field(..., min_length=5, max_length=2000)
    allow_testimonial: bool = False
    page: Optional[str] = None


class FeedbackItem(BaseModel):
    id: str
    rating: int
    message: str
    allow_testimonial: bool
    created_at: str
    initials: str


@router.post("")
async def submit_feedback(
    body: FeedbackRequest,
    user_id: str = Depends(get_effective_user_id),
):
    sb = get_supabase()

    # Get user email for notification
    try:
        profile = sb.table("user_profiles").select("email, tier").eq("id", user_id).single().execute()
        user_email = profile.data.get("email", "unknown") if profile.data else "unknown"
        user_tier = profile.data.get("tier", "free") if profile.data else "free"
    except Exception:
        user_email = "unknown"
        user_tier = "free"

    row = {
        "user_id": user_id,
        "rating": body.rating,
        "message": body.message,
        "allow_testimonial": body.allow_testimonial,
        "page": body.page,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        sb.table("feedback").insert(row).execute()
    except Exception as e:
        logger.error("Failed to save feedback: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save feedback")

    # Email the owner
    _notify_owner(body, user_email, user_tier)

    return {"ok": True}


@router.get("/public")
async def public_feedback():
    """Return approved testimonials visible to all visitors."""
    sb = get_supabase()
    try:
        res = (
            sb.table("feedback")
            .select("id, rating, message, created_at, initials")
            .eq("allow_testimonial", True)
            .gte("rating", 4)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        return {"data": res.data or []}
    except Exception:
        return {"data": []}


def _notify_owner(body: FeedbackRequest, user_email: str, user_tier: str) -> None:
    if not settings.resend_api_key:
        return
    try:
        import resend  # type: ignore
        owner_email = getattr(settings, "owner_email", "devonwaldrop0131@gmail.com")
        stars = "★" * body.rating + "☆" * (5 - body.rating)
        testimonial_note = " · <strong>Opted in to testimonial</strong>" if body.allow_testimonial else ""

        resend.api_key = settings.resend_api_key
        resend.Emails.send({
            "from": settings.resend_from,
            "to": [owner_email],
            "subject": f"[StoreScout Feedback] {stars} from {user_email}",
            "html": f"""
<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto;background:#0d1117;color:#e6edf3;padding:32px;border-radius:12px">
  <p style="color:#7d8590;font-size:12px;margin:0 0 16px">New feedback{testimonial_note}</p>
  <div style="font-size:24px;margin-bottom:12px">{stars}</div>
  <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;font-size:14px;line-height:1.6;color:#c9d1d9">
    {body.message}
  </div>
  <p style="font-size:12px;color:#7d8590;margin:16px 0 0">
    From: {user_email} ({user_tier}){f" · Page: {body.page}" if body.page else ""}
  </p>
</div>
""",
        })
    except Exception as e:
        logger.warning("Could not send feedback notification: %s", e)
