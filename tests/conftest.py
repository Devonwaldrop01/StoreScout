"""Pytest bootstrap — ensure the repo root is importable so `import app.*`
works when pytest is run from anywhere, and keep tests hermetic (no network,
no real Redis/Anthropic). Fixtures here provide the small fakes the unit tests
need."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Tests must never reach out. Empty AI key → the AI layer returns ok=False
# (its no-key path) instead of attempting a call.
os.environ.setdefault("ANTHROPIC_API_KEY", "")
