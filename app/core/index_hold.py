"""Deployment interlock, independent of mutable app_config and canary flags.

Every process starts held unless explicitly configured false. This is a
process-local interlock: old processes must still be drained before migration.
Changing configuration takes effect only in processes that receive it.
"""
import os


class IndexDeploymentHeld(RuntimeError):
    pass


def index_writes_held():
    try:
        return os.environ.get("STORE_INDEX_DEPLOYMENT_HOLD") != "false"
    except Exception:
        return True


def require_index_writes():
    if index_writes_held():
        raise IndexDeploymentHeld("StoreScout index writers are held for deployment")


INDEX_TABLES = frozenset({
    "shopify_store_index", "discovery_queue", "discovery_cursors",
    "store_index_runs", "competitor_edges",
})
_MUTATIONS = frozenset({"insert", "upsert", "update", "delete"})


class GuardedQuery:
    """Check at execution too: a prepared request is not write authorization."""
    def __init__(self, query, mutating=False):
        self._query, self._mutating = query, mutating

    def __getattr__(self, name):
        target = getattr(self._query, name)
        if not callable(target):
            return GuardedQuery(target, self._mutating) if name == "not_" else target

        def call(*args, **kwargs):
            mutating = self._mutating or name in _MUTATIONS
            if mutating:
                require_index_writes()
            result = target(*args, **kwargs)
            return result if name == "execute" else GuardedQuery(result, mutating)
        return call


class GuardedDatabase:
    def __init__(self, client):
        self._client = client

    def table(self, name):
        query = self._client.table(name)
        return GuardedQuery(query) if name in INDEX_TABLES else query

    from_ = table

    def schema(self, name):
        return GuardedDatabase(self._client.schema(name))

    def __getattr__(self, name):
        return getattr(self._client, name)
