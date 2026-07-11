"""Observability — secret redaction, error-ref generation, and that safe_read
degrades to its default shape with an error marker (never a raw exception)."""
from app.core.obs import redact, report_error, safe_read


def test_redact_scrubs_credentials():
    out = redact("leak sk-abcdef12345678 and Bearer eyJaaaaaaaaaaaaaaaaaaaaaa.bbb.ccc here")
    assert "sk-abcdef12345678" not in out
    assert "eyJ" not in out
    assert "[redacted]" in out


def test_redact_truncates_long_input():
    assert len(redact("x" * 5000)) <= 300


def test_report_error_returns_short_ref():
    ref = report_error("unit.op", ValueError("boom"), user_id="u1", entity="c1")
    assert isinstance(ref, str) and len(ref) == 8


def test_safe_read_returns_default_with_error_marker_on_exception():
    @safe_read("GET /thing", {"data": []})
    def endpoint(user_id=None):
        raise RuntimeError("kaboom")

    result = endpoint(user_id="u1")
    assert result["data"] == []
    assert result["error"] is True          # distinguishes failure-empty from legit-empty
    assert "ref" in result


def test_safe_read_passes_through_success():
    @safe_read("GET /thing", {"data": []})
    def endpoint(user_id=None):
        return {"data": [1, 2, 3]}

    assert endpoint(user_id="u1") == {"data": [1, 2, 3]}
