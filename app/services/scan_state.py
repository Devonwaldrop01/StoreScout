"""
Scan lifecycle — a single, testable mapping from the persisted competitor row
to a normalized, pollable lifecycle state, including real timeout detection.

The scan task sets `scan_status='scanning'` + `updated_at=now()` when it starts
(and a DB trigger keeps `updated_at` current), so a scan still 'scanning' long
after `updated_at` is a stalled/dead job — reported as `timed_out` rather than
spinning forever. No fabricated progress percentages: only genuine states.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

# The lifecycle the frontend renders. queued/running/completed/failed/timed_out
# come from the row; already_in_progress/rate_limited/unavailable are returned by
# the rescan POST itself (409/429/503).
STATES = ("idle", "queued", "running", "completed", "failed", "timed_out")


def _age_seconds(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:
        return None


def derive_scan_state(
    scan_status: Optional[str],
    updated_at: Optional[str],
    last_scanned_at: Optional[str],
    timeout_minutes: int = 15,
) -> Dict[str, Any]:
    """
    Pure derivation of the normalized scan lifecycle from the persisted row.
    Returns {state, scan_status, since, last_scanned_at, running_seconds,
    timed_out}. `state` is one of STATES.
    """
    running_seconds = _age_seconds(updated_at)
    timed_out = False
    status = (scan_status or "").lower()

    if status == "scanning":
        if running_seconds is not None and running_seconds > timeout_minutes * 60:
            state = "timed_out"
            timed_out = True
        else:
            state = "running"
    elif status == "done":
        state = "completed"
    elif status == "error":
        state = "failed"
    elif status == "pending":
        state = "queued"
    else:
        state = "idle"

    return {
        "state": state,
        "scan_status": scan_status,
        "since": updated_at,
        "last_scanned_at": last_scanned_at,
        "running_seconds": int(running_seconds) if running_seconds is not None else None,
        "timed_out": timed_out,
    }
