"""Guard: the deterministic playbook must not reassert the production claims
that overstated buyer behavior, competitor margin/brand-equity, catalog
overlap, or guaranteed outcomes from discount data alone."""
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[1] / "app" / "services" / "playbook_intelligence.py"


def test_no_unsupported_claim_phrases():
    text = SRC.read_text()
    banned = [
        "teaches their buyers to never pay full price",   # asserts buyer behavior
        "training away their own margin and brand equity",  # asserts competitor margin/brand damage
        "On products you both carry",                      # implies catalog overlap (not computed)
        "while keeping margin intact",                     # guarantees an outcome
        "competitors erode theirs",                        # asserts competitor outcome as fact
    ]
    hits = [p for p in banned if p in text]
    assert not hits, f"unsupported claim phrase(s) reintroduced: {hits}"


def test_conditional_language_present():
    # the rewritten copy hedges instead of asserting
    text = SRC.read_text()
    assert "Aims to" in text
    assert "can condition" in text or "often points to" in text
