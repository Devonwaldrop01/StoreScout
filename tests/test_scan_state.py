"""Scan lifecycle derivation — normalized states + genuine timeout detection."""
from datetime import datetime, timezone, timedelta

from app.services.scan_state import derive_scan_state


def _ago(minutes):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def test_pending_is_queued():
    assert derive_scan_state("pending", _ago(0), None)["state"] == "queued"


def test_scanning_recent_is_running():
    out = derive_scan_state("scanning", _ago(2), None, timeout_minutes=15)
    assert out["state"] == "running"
    assert out["timed_out"] is False


def test_scanning_too_long_is_timed_out():
    out = derive_scan_state("scanning", _ago(30), None, timeout_minutes=15)
    assert out["state"] == "timed_out"
    assert out["timed_out"] is True


def test_done_is_completed():
    assert derive_scan_state("done", _ago(5), _ago(5))["state"] == "completed"


def test_error_is_failed():
    assert derive_scan_state("error", _ago(1), None)["state"] == "failed"


def test_unknown_is_idle():
    assert derive_scan_state(None, None, None)["state"] == "idle"


def test_running_seconds_reported():
    out = derive_scan_state("scanning", _ago(3), None)
    assert out["running_seconds"] is not None and out["running_seconds"] >= 170  # ~180s


def test_timeout_boundary_uses_configured_minutes():
    # 10 min old with a 5-min timeout -> timed out; with a 15-min timeout -> running
    assert derive_scan_state("scanning", _ago(10), None, timeout_minutes=5)["state"] == "timed_out"
    assert derive_scan_state("scanning", _ago(10), None, timeout_minutes=15)["state"] == "running"
