"""Shared Anthropic layer — JSON parsing / fence cleanup / no-key fallback.
No network: these exercise the pure helpers and the graceful no-key path."""
from app.services.ai import parse_json, strip_code_fences, call_claude, AIResult


def test_strip_code_fences_json_block():
    assert strip_code_fences('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_code_fences_plain_passthrough():
    assert strip_code_fences('{"a": 1}') == '{"a": 1}'


def test_parse_json_from_fenced_block():
    assert parse_json('```json\n{"a": 1, "b": [2,3]}\n```') == {"a": 1, "b": [2, 3]}


def test_parse_json_bad_input_returns_default():
    assert parse_json("not json at all", default={"x": 0}) == {"x": 0}
    assert parse_json("", default=None) is None


def test_call_claude_without_api_key_returns_not_ok():
    # conftest sets ANTHROPIC_API_KEY="" → the layer must fall back, never raise.
    res = call_claude("unit_test", "hello", model="claude-haiku-4-5-20251001", max_tokens=10)
    assert isinstance(res, AIResult)
    assert res.ok is False
    assert res.feature == "unit_test"
    assert res.text == ""
