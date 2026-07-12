"""Anthropic insufficient-credit (a 400 BadRequestError) must resolve AI jobs to
a FINITE state — never leave Playbook/brand-decode stuck on 'AI analysis in
progress'. Deterministic content stays available with Retry.

These lock the existing guarantees on main so a regression can't reintroduce the
hang:
  · call_claude never retries a 400 (retry can't fix insufficient credit) → fast ok=False
  · brand-decode returns None synchronously on ok=False (no pending state at all)
  · the Playbook AI state machine promotes a timed-out/failed job to a terminal
    state and never reports 'generating' forever
"""
from app.services.ai import AIResult, _is_transient
from app.services.ai_job import decide_ai_action


def test_call_claude_does_not_retry_bad_request():
    import anthropic
    # A 400 (what an insufficient-credit error is) is NOT transient → no retry,
    # so call_claude returns ok=False immediately instead of blocking on retries.
    exc = anthropic.BadRequestError.__new__(anthropic.BadRequestError)
    assert _is_transient(exc) is False


def test_brand_decode_returns_none_on_ai_failure(monkeypatch):
    import app.services.ai as ai_mod
    monkeypatch.setattr(
        ai_mod, "call_claude",
        lambda *a, **k: AIResult(ok=False, feature="brand_decode", meta={"reason": "insufficient_credit"}),
    )
    from app.services.brand_decode import generate_brand_decode
    out = generate_brand_decode({"hostname": "x.com", "category": "Beauty", "median_price": 40})
    assert out is None  # finite, synchronous — never a pending/in-progress state


def test_ai_job_never_generating_forever():
    # A job that has run past its timeout is promoted to a terminal failure...
    state, action = decide_ai_action(has_fresh_result=False, phase="active", age_s=999, timeout_s=120)
    assert (state, action) == ("timed_out", "mark_failed")
    # ...and once failed, a GET reports failed and does NOT re-dispatch (no loop).
    assert decide_ai_action(False, "failed", None, 120) == ("failed", "none")
    # within timeout it may still be generating (that's fine — it's bounded)
    assert decide_ai_action(False, "active", 5, 120) == ("generating", "none")


def test_fresh_result_is_ready_even_after_a_prior_failure():
    # deterministic/rule content is always servable; a fresh AI result is 'ready'
    assert decide_ai_action(has_fresh_result=True, phase="failed", age_s=None, timeout_s=120) == ("ready", "none")
