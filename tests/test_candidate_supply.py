"""Candidate-supply expansion — the index must grow broad enough to cover
almost any niche a user describes.

Three mechanisms:
  1. niche_queries(): a wide, deterministic niche list (seeds + taxonomy).
  2. stage_verification now drains BOTH 'discovered' and 'candidate' rows, so
     niche/related/demand candidates actually get verified (previously stranded).
  3. generate_candidates_rotating(): rotates through the niche list generating
     candidates a few at a time (gated + single-flight via the decorator).
"""
import app.tasks.store_index as si


# ── 1. Broad niche coverage ────────────────────────────────────────────────

def test_niche_queries_is_broad_and_clean():
    from app.services.store_index import niche_queries, SEED_QUERIES
    q = niche_queries()
    assert len(q) > 100                       # covers the whole taxonomy, not 10 seeds
    assert q[: len(SEED_QUERIES)] == SEED_QUERIES  # seeds first, order-stable
    assert len(q) == len(set(q))              # deduped
    assert all(isinstance(s, str) and s.strip() for s in q)


# ── 2. stage_verification drains 'candidate' too ───────────────────────────

class _FakeQuery:
    def __init__(self, rows, captured):
        self._rows, self._c = rows, captured
    def select(self, *_a, **_k): return self
    def eq(self, *_a, **_k): return self
    def in_(self, col, vals):
        self._c["status_filter"] = (col, list(vals)); return self
    def order(self, *_a, **_k): return self
    def limit(self, *_a, **_k): return self
    def execute(self):
        class _R: pass
        r = _R(); r.data = self._rows; return r


class _FakeDB:
    def __init__(self, rows, captured):
        self._rows, self._c = rows, captured
    def table(self, *_a, **_k):
        return _FakeQuery(self._rows, self._c)


def test_verification_query_includes_candidate_status(monkeypatch):
    captured = {}
    rows = [{"domain": "a.com", "source": "ai_niche_query", "source_query": "ashtrays"},
            {"domain": "b.com", "source": "shop_app", "source_query": None}]
    monkeypatch.setattr(si, "get_supabase", lambda: _FakeDB(rows, captured))
    monkeypatch.setattr(si, "_verify_via_web",
                        lambda d, s, q: {"outcome": "verified" if d == "a.com" else "rejected", "reason": "not_shopify"})
    monkeypatch.setattr(si, "normalize_domain", lambda d: d)

    out = si.stage_verification(force=True)
    # the fetch must target BOTH discovered and candidate
    col, vals = captured["status_filter"]
    assert col == "status" and set(vals) == {"discovered", "candidate"}
    # both rows attempted; the niche candidate a.com verified
    assert out["processed"] == 2
    assert out["verified"] == 1 and out["rejected"] == 1
    assert out["reverified"] == 0


def test_verification_empty_queue_is_clean(monkeypatch):
    monkeypatch.setattr(si, "get_supabase", lambda: _FakeDB([], {}))
    out = si.stage_verification(force=True)
    assert out["status"] == "ok" and out["processed"] == 0 and out.get("note") == "queue_empty"


# ── 3. Rotating candidate generation ───────────────────────────────────────

def test_rotating_generator_gated_off_by_default(monkeypatch):
    # disabled → no work, no AI calls
    monkeypatch.setattr("app.services.runtime_config.get_config",
                        lambda k, d=None: False if k == "shopify_index_enabled" else d)
    out = si.generate_candidates_rotating()
    assert out["status"] == "disabled"


def test_rotating_generator_cycles_niches_and_counts(monkeypatch):
    monkeypatch.setattr("app.services.runtime_config.get_config",
                        lambda k, d=None: 3 if k == "shopify_index_niche_per_run" else d)
    used = []
    monkeypatch.setattr(si, "generate_niche_candidates",
                        lambda q, *a, **k: (used.append(q) or {"status": "ok", "inserted": 5}))
    # no graph expansion rows
    monkeypatch.setattr(si, "get_supabase", lambda: _FakeDB([], {}))

    out = si.generate_candidates_rotating(force=True)
    assert out["status"] == "ok"
    assert len(used) == 3                      # per_run niches generated
    assert len(set(used)) == 3                 # distinct niches (cursor rotates)
    assert out["processed"] == 15              # 3 niches x 5 inserted (candidates added)
    from app.services.store_index import niche_queries
    assert all(u in niche_queries() for u in used)
