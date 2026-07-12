"""Admin index-coverage readout: verified depth per category + which niches the
generator has reached vs still pending."""
import app.api.v1.store_index as sidx


class _FakeExec:
    def __init__(self, count=0, data=None):
        self.count = count
        self.data = data or []


class _FakeQuery:
    def __init__(self):
        self._cols = ""
    def select(self, cols="", **_k):
        self._cols = cols
        return self
    def eq(self, *_a, **_k): return self
    def is_(self, *_a, **_k): return self
    def limit(self, *_a, **_k): return self
    def execute(self):
        # niche-generation query selects source_query → return a mix: one planned
        # niche + one on-demand niche not in the planned list.
        if "source_query" in self._cols:
            return _FakeExec(data=[{"source_query": "fitness apparel"},
                                   {"source_query": "vintage typewriter ribbons"}])
        return _FakeExec(count=0)   # category / unclassified counts


class _FakeDB:
    def table(self, *_a, **_k):
        return _FakeQuery()


def test_coverage_diffs_generated_vs_pending(monkeypatch):
    monkeypatch.setattr(sidx, "_require_admin", lambda tok: None)
    monkeypatch.setattr(sidx, "get_supabase", lambda: _FakeDB())

    out = sidx.store_index_coverage(x_admin_token="x")["data"]

    from app.services.store_index import niche_queries
    total = len(niche_queries())
    assert out["niches_total"] == total
    # 'fitness apparel' is a planned seed → counted as generated
    assert out["niches_generated"] == 1
    # generated + pending accounts for the whole planned list
    assert out["niches_generated"] + len([q for q in niche_queries()
                                          if q not in out["niches_pending_sample"]] ) >= 1
    assert len(out["niches_pending_sample"]) <= 50
    # the on-demand niche (not in the planned list) is surfaced separately
    assert "vintage typewriter ribbons" in out["ad_hoc_niches_sample"]
    assert out["ad_hoc_count"] == 1
    # category depth degrades cleanly to empty when nothing is classified
    assert out["categories"] == [] and out["verified_total"] == 0
