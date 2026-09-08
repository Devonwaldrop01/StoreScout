"""Pytest bootstrap — ensure the repo root is importable so `import app.*`
works when pytest is run from anywhere, and keep tests hermetic (no network,
no real Redis/Anthropic). Fixtures here provide the small fakes the unit tests
need."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Tests must never reach out. Empty AI key → the AI layer returns ok=False
# (its no-key path) instead of attempting a call.
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["REDIS_URL"] = "redis://offline.invalid:6379/0"
os.environ["SUPABASE_URL"] = "https://offline.invalid"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "offline-test-key"
os.environ["API_INTERNAL_URL"] = "https://offline.invalid"
os.environ["STORE_INDEX_DEPLOYMENT_HOLD"] = "false"

import pytest


@pytest.fixture(autouse=True)
def no_live_network(monkeypatch):
    import socket
    import httpx
    def blocked(*args, **kwargs):
        raise RuntimeError("live network forbidden in offline tests")
    async def blocked_async(*args, **kwargs):
        blocked()
    connect = socket.socket.connect
    def local_only(sock, address):
        # Windows asyncio builds its internal wakeup pipe with loopback TCP.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return connect(sock, address)
        blocked()
    monkeypatch.setattr(socket.socket, "connect", local_only)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked_async)
    from curl_cffi.requests import Session
    monkeypatch.setattr(Session, "request", blocked)
