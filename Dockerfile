# ──────────────────────────────────────────────────
# Base: Python with Playwright (kept for legacy PDF support)
# ──────────────────────────────────────────────────
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble@sha256:678457c4c323b981d8b4befc57b95366bb1bb6aa30057b1269f6b171e8d9975a AS base

WORKDIR /app

# Record packages inherited from the immutable base separately from app deps.
RUN python -c "import json,importlib.metadata as m; json.dump({d.metadata['Name']:d.version for d in m.distributions()},open('/opt/storescout-base-packages.json','w'),sort_keys=True)"

COPY requirements.txt requirements-release-constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements-release-constraints.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# ──────────────────────────────────────────────────
# API server target
# ──────────────────────────────────────────────────
FROM base AS api
EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]

# ──────────────────────────────────────────────────
# Celery worker target
# ──────────────────────────────────────────────────
FROM base AS worker
CMD ["celery", "-A", "app.tasks.celery_app.celery", "worker", "--loglevel=info", "-Q", "default,priority", "--concurrency=2"]

# ──────────────────────────────────────────────────
# Celery Beat scheduler target
# ──────────────────────────────────────────────────
FROM base AS scheduler
CMD ["celery", "-A", "app.tasks.celery_app.celery", "beat", "--loglevel=info"]
