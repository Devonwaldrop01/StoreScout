"""Renewable, owner-checked stage leases. Redis failures stop new work."""
from contextvars import ContextVar
from threading import Event, Thread
from uuid import uuid4
import time

from app.core.redis_connection import coordination_redis
from app.core.index_hold import index_writes_held, require_index_writes

_RENEW = """if redis.call('get', KEYS[1]) == ARGV[1] then
return redis.call('expire', KEYS[1], ARGV[2]) else return 0 end"""
_RELEASE = """if redis.call('get', KEYS[1]) == ARGV[1] then
return redis.call('del', KEYS[1]) else return 0 end"""
current_lease = ContextVar("index_stage_lease", default=None)


class LeaseLost(RuntimeError):
    pass


class IndexLease:
    def __init__(self, client, key, ttl):
        self.client, self.key, self.ttl = client, key, ttl
        self.token = str(uuid4())
        self.lost, self.stop = Event(), Event()
        self.thread = None
        self.valid_until = 0

    def acquire(self):
        require_index_writes()
        started = time.monotonic()
        if not self.client.set(self.key, self.token, nx=True, ex=self.ttl):
            return False
        self.valid_until = started + self.ttl
        return True

    def renew(self):
        if index_writes_held():
            self.lost.set()
            return False
        started = time.monotonic()
        if self.lost.is_set() or started >= self.valid_until:
            self.lost.set()
            return False
        try:
            ok = self.client.eval(_RENEW, 1, self.key, self.token, self.ttl)
        except Exception:
            ok = False
        if not ok or time.monotonic() >= self.valid_until:
            self.lost.set()
            return False
        self.valid_until = started + self.ttl
        return True

    def require(self):
        require_index_writes()
        if not self.renew():
            raise LeaseLost("index stage lease lost; dispatch stopped")

    def start(self):
        def heartbeat():
            while not self.stop.wait(self.ttl / 3):
                if not self.renew():
                    break
        self.thread = Thread(target=heartbeat, daemon=True, name="index-lease")
        self.thread.start()

    def release(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=5)
        try:
            self.client.eval(_RELEASE, 1, self.key, self.token)
        finally:
            self.client.close()


def acquire_stage(stage, ttl):
    require_index_writes()
    client = coordination_redis()
    lease = IndexLease(client, f"lock:index:{stage}", ttl)
    try:
        if lease.acquire():
            return lease
    except Exception:
        client.close()
        raise
    client.close()
    return None
