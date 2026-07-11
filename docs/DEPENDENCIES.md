# Managing backend Python dependencies

StoreScout's backend dependencies are **pinned to exact versions** in
`requirements.txt`. This makes every build reproducible: local dev, the Railway
API service, the Celery worker, and the Celery Beat scheduler all install the
same `requirements.txt` (via the `Dockerfile`, which every Railway target
shares), so a fresh deploy can never silently pull a new — possibly
breaking — version.

## Why pinned

Unpinned dependencies mean a rebuild months from now resolves to whatever is
"latest" that day. A single major bump (FastAPI, Pydantic, the Anthropic SDK,
Supabase client…) can break production with no code change on our side. Pinning
freezes a known-good set; upgrades become deliberate, reviewable events.

## Hard constraints

- **Python 3.12** — the Dockerfile base image
  (`mcr.microsoft.com/playwright/python:v1.58.0-noble` = Ubuntu 24.04). The pins
  are verified on 3.12 and 3.11; CI runs 3.12 to match production.
- **`playwright==1.58.0`** must match the Dockerfile base image
  (`mcr.microsoft.com/playwright/python:v1.58.0-noble`). The browsers are
  pre-baked into that image; a different playwright version won't match them.
  If you bump playwright, bump the base image tag in the same commit.

## Intentionally updating a dependency

Do this deliberately, one change at a time — never a blanket "upgrade
everything":

1. **Edit the pin** in `requirements.txt` (change one, or a small related set).
2. **Rebuild a clean venv** and install:
   ```bash
   python -m venv /tmp/ss-venv
   PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 /tmp/ss-venv/bin/pip install -r requirements.txt
   ```
3. **Verify the app still imports** (catches API-breaking changes fast):
   ```bash
   /tmp/ss-venv/bin/python -c "import app.main; print('ok')"
   ```
4. **Run the tests:**
   ```bash
   /tmp/ss-venv/bin/pip install pytest
   /tmp/ss-venv/bin/python -m pytest -q
   ```
5. **Check for a major-version jump.** If the new version crosses a major
   boundary (e.g. `2.x → 3.x`), read that library's changelog before merging —
   majors are where breakage lives.
6. **Commit the `requirements.txt` change on its own** (plus the base-image bump
   if playwright moved), so a dependency update is easy to identify and revert.

CI (`.github/workflows/ci.yml`) installs `requirements.txt` and runs the import
check + tests on every PR, so an incompatible pin is caught before deploy.

## Adding a new dependency

Add it **with an exact pin** (`package==X.Y.Z`) to the correct section of
`requirements.txt`, then follow steps 2–6 above. Only add direct dependencies we
actually import; let pip resolve transitive ones.
