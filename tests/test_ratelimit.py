"""Rate limiting + single-flight — limiting behavior and fail-open safety,
exercised against a tiny in-memory fake Redis (no real Redis in tests)."""
import time
import pytest

from app.core import ratelimit


class FakeRedis:
    def __init__(self):
        self.store = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, ttl):
        return True

    def ttl(self, key):
        return 3600

    def set(self, key, val, nx=False, ex=None):
        if nx and key in self.store:
            return False
        self.store[key] = val
        return True

    def delete(self, key):
        self.store.pop(key, None)


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(ratelimit, "_redis", lambda: fake)
    return fake


def test_rate_limit_allows_up_to_limit_then_blocks(fake_redis):
    ident = f"u-{time.time()}"
    for _ in range(3):
        allowed, _ = ratelimit.check_rate_limit("bucket", ident, limit=3, window_s=3600)
        assert allowed is True
    allowed, retry_after = ratelimit.check_rate_limit("bucket", ident, limit=3, window_s=3600)
    assert allowed is False
    assert retry_after > 0


def test_rate_limit_zero_limit_disables(fake_redis):
    allowed, _ = ratelimit.check_rate_limit("bucket", "u", limit=0, window_s=3600)
    assert allowed is True


def test_rate_limit_fails_open_when_redis_unavailable(monkeypatch):
    def boom():
        raise RuntimeError("redis down")
    monkeypatch.setattr(ratelimit, "_redis", boom)
    allowed, retry_after = ratelimit.check_rate_limit("bucket", "u", limit=1, window_s=3600)
    assert allowed is True and retry_after == 0


def test_single_flight_collapses_duplicate(fake_redis):
    key = ratelimit.dedupe_key("user", "same-input")
    with ratelimit.single_flight("ask", key, ttl_s=30) as first:
        assert first is True
        # a second, simultaneous acquire for the same key must be rejected
        with ratelimit.single_flight("ask", key, ttl_s=30) as second:
            assert second is False
    # released on exit → available again
    with ratelimit.single_flight("ask", key, ttl_s=30) as third:
        assert third is True


def test_single_flight_fails_open_when_redis_unavailable(monkeypatch):
    monkeypatch.setattr(ratelimit, "_redis", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    with ratelimit.single_flight("ask", "k") as acquired:
        assert acquired is True
