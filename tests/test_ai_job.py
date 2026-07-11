"""Finite AI-job state — the decision that replaced the indefinite
'AI analysis in progress' loop. Pure logic, no Redis."""
from app.services.ai_job import decide_ai_action


def test_fresh_result_is_ready_no_dispatch():
    assert decide_ai_action(True, False, None, 180) == ("ready", False)


def test_no_job_dispatches_exactly_once():
    # nothing in flight -> generating + should dispatch
    assert decide_ai_action(False, False, None, 180) == ("generating", True)


def test_active_job_within_timeout_dedupes():
    # a job already running must NOT trigger a second dispatch
    assert decide_ai_action(False, True, 30, 180) == ("generating", False)


def test_active_job_past_timeout_is_timed_out():
    assert decide_ai_action(False, True, 300, 180) == ("timed_out", False)


def test_never_dispatches_when_result_present_even_if_job_active():
    assert decide_ai_action(True, True, 9999, 180) == ("ready", False)


def test_timeout_boundary():
    assert decide_ai_action(False, True, 179, 180)[0] == "generating"
    assert decide_ai_action(False, True, 181, 180)[0] == "timed_out"
