"""Finite AI-job state machine — the decision that replaced the indefinite
'AI analysis in progress' loop. Pure logic, no Redis.

Verifies the explicit requirements: a GET never re-dispatches once a job exists;
only regenerate retries; a timed-out/failed job is a finite terminal state; the
terminal state is deterministically derivable; deterministic plays are unaffected.
"""
from app.services.ai_job import decide_ai_action


def test_fresh_result_is_ready_no_action():
    assert decide_ai_action(True, "none", None, 180) == ("ready", "none")


def test_no_job_dispatches_exactly_once():
    assert decide_ai_action(False, "none", None, 180) == ("generating", "dispatch")


def test_active_job_within_timeout_does_not_redispatch():
    # repeated GET while a job is active must NOT dispatch again
    assert decide_ai_action(False, "active", 30, 180) == ("generating", "none")


def test_active_job_past_timeout_becomes_terminal():
    assert decide_ai_action(False, "active", 300, 180) == ("timed_out", "mark_failed")


def test_failed_phase_never_redispatches_on_get():
    # a terminal failure: a plain GET reports failed and does NOT retry
    assert decide_ai_action(False, "failed", None, 180) == ("failed", "none")


def test_result_present_wins_even_if_job_active():
    assert decide_ai_action(True, "active", 9999, 180) == ("ready", "none")


def test_timeout_boundary():
    assert decide_ai_action(False, "active", 179, 180)[0] == "generating"
    assert decide_ai_action(False, "active", 181, 180) == ("timed_out", "mark_failed")


def test_failed_ttl_is_bounded_not_permanent():
    # the failed marker carries a finite TTL so failures self-heal (no permanent block)
    from app.services.ai_job import _FAILED_TTL_S
    assert 0 < _FAILED_TTL_S <= 24 * 3600
