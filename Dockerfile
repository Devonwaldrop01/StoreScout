# ──────────────────────────────────────────────────
# Base: Python with Playwright (kept for legacy PDF support)
# ──────────────────────────────────────────────────
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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