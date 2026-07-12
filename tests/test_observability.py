"""Production error visibility — report_error records a grouped, redacted,
correlation-tagged summary without leaking secrets."""
import app.core.obs as obs
from app.core.obs import report_error, recent_error_summary, redact


def _clear():
    obs._recent_errors.clear()


def test_report_error_returns_correlation_ref_and_records():
    _clear()
    ref = report_error("test.op", ValueError("boom"), user_id="u1", entity="c1")
    assert isinstance(ref, str) and len(ref) == 8
    groups = recent_error_summary()
    assert any(g["operation"] == "test.op" and g["exc_class"] == "ValueError" for g in groups)
    g = next(g for g in groups if g["operation"] == "test.op")
    assert g["count"] == 1 and g["last_ref"] == ref and "last_seen_iso" in g


def test_summary_groups_repeated_errors_with_count():
    _clear()
    for _ in range(3):
        report_error("test.repeat", RuntimeError("db down"))
    g = next(x for x in recent_error_summary() if x["operation"] == "test.repeat")
    assert g["count"] == 3


def test_summary_never_contains_secrets():
    _clear()
    report_error("test.secret", RuntimeError("failed with key sk-abcdef123456 and Bearer eyJabcdefghijklmnop.q.r"))
    sample = next(x for x in recent_error_summary() if x["operation"] == "test.secret")["sample"]
    assert "sk-abcdef123456" not in sample
    assert "eyJ" not in sample
    assert "[redacted]" in sample


def test_degraded_flag_recorded():
    _clear()
    report_error("test.deg", ValueError("x"), degraded=True)
    assert next(x for x in recent_error_summary() if x["operation"] == "test.deg")["degraded"] is True


def test_redact_helper_scrubs_and_truncates():
    assert "[redacted]" in redact("token=abcdef12345 secret")
    assert len(redact("x" * 5000)) <= 300


def test_summary_bounded_and_newest_first():
    _clear()
    report_error("test.a", ValueError("1"))
    report_error("test.b", ValueError("2"))
    groups = recent_error_summary()
    # newest (test.b) should sort before test.a
    ops = [g["operation"] for g in groups if g["operation"] in ("test.a", "test.b")]
    assert ops[0] == "test.b"
