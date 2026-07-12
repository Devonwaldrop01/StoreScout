"""
Migration / schema health check.

Verifies the live database actually has the columns and tables the current code
depends on — especially recent, optional feature migrations (Brand Decode,
business-profile enrichment, Store DNA, intent signals). Surfaced at
`GET /admin/migration-health` so an operator can confirm a deploy's migrations
landed before turning features on, instead of discovering it via a 500.

Design:
  - `probe_column` / `probe_table` do the (guarded) DB I/O and classify the
    outcome as present / missing / db_error, using the same "column/relation
    does not exist" detection the store-index upserts use.
  - `summarize` is a PURE function over the probe results, so the status logic
    is unit-tested without a database.

A missing OPTIONAL feature migration reports `degraded` (with the exact
feature/table/column named) — it never crashes unrelated pages. A missing
REQUIRED core table reports `unhealthy`. A DB that can't be reached at all
reports `db_unavailable`.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("storescout.schema")

# The newest migration this code expects to be applied.
LATEST_EXPECTED_MIGRATION = "022"

# (migration, feature, table, column-or-None-for-table-existence, required)
# `required` = core schema the app can't run without; the rest are feature
# migrations that should degrade gracefully when absent.
CHECKS: List[Dict[str, Any]] = [
    {"migration": "001", "feature": "Core competitors",         "table": "competitors",          "column": None,           "required": True},
    {"migration": "001", "feature": "Scan snapshots",           "table": "scan_snapshots",       "column": None,           "required": True},
    {"migration": "001", "feature": "Change events (alerts)",   "table": "change_events",        "column": None,           "required": True},
    {"migration": "006", "feature": "Product watchlist",        "table": "product_watches",      "column": None,           "required": False},
    {"migration": "014", "feature": "Business profiles",        "table": "business_profiles",    "column": None,           "required": False},
    {"migration": "019", "feature": "Intent signals",           "table": "intent_signals",       "column": None,           "required": False},
    {"migration": "020", "feature": "Brand Decode",             "table": "competitors",          "column": "brand_decode", "required": False},
    {"migration": "021", "feature": "Business profile: sells",  "table": "business_profiles",    "column": "sells",        "required": False},
    {"migration": "021", "feature": "Business profile: traits", "table": "business_profiles",    "column": "brand_traits", "required": False},
    {"migration": "021", "feature": "Business profile: notes",  "table": "business_profiles",    "column": "notes",        "required": False},
    {"migration": "022", "feature": "Store DNA profile",        "table": "shopify_store_index",  "column": "store_dna",    "required": False},
    {"migration": "022", "feature": "Store DNA keywords",       "table": "shopify_store_index",  "column": "dna_keywords", "required": False},
]

_MISSING_RES = (
    re.compile(r"column\s+(?:[\w.]+\.)?[\"']?[\w]+[\"']?\s+does not exist", re.I),
    re.compile(r"Could not find the '[\w]+' column", re.I),
    re.compile(r"relation\s+[\"']?[\w.]+[\"']?\s+does not exist", re.I),
    re.compile(r"Could not find the table", re.I),
    re.compile(r"(?i)does not exist"),
)


def _looks_missing(msg: str) -> bool:
    return any(rx.search(msg or "") for rx in _MISSING_RES)


def probe(db, table: str, column: Optional[str]) -> str:
    """Return 'present' | 'missing' | 'db_error' for a table/column existence
    probe. Never raises."""
    try:
        # Column checks select that column. Table-existence checks must NOT
        # assume an `id` column — some tables are keyed by something else (e.g.
        # business_profiles has user_id as its PK and no `id`), so `select("*")`
        # tests existence without a false "column id does not exist" negative.
        db.table(table).select(column or "*").limit(1).execute()
        return "present"
    except Exception as exc:  # noqa: BLE001
        if _looks_missing(str(exc)):
            return "missing"
        # Anything else (auth, connection, timeout) → can't tell schema from here.
        logger.warning("schema probe error on %s.%s: %s", table, column, exc)
        return "db_error"


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pure aggregation of per-check probe results into an operational verdict.
    Each result item is a CHECKS entry plus a `state` in
    present|missing|db_error. Returns the structured health payload.
    """
    # If we couldn't even read the core required tables, the DB is unavailable.
    core_errors = [r for r in results if r.get("required") and r.get("state") == "db_error"]
    if core_errors and all(r.get("state") == "db_error" for r in results):
        return {
            "status": "db_unavailable",
            "latest_expected_migration": LATEST_EXPECTED_MIGRATION,
            "checks": results,
            "missing_required": [],
            "missing_optional": [],
        }

    missing_required = [
        {"migration": r["migration"], "feature": r["feature"], "table": r["table"], "column": r["column"]}
        for r in results if r.get("required") and r.get("state") in ("missing", "db_error")
    ]
    missing_optional = [
        {"migration": r["migration"], "feature": r["feature"], "table": r["table"], "column": r["column"]}
        for r in results if not r.get("required") and r.get("state") == "missing"
    ]

    if missing_required:
        status = "unhealthy"
    elif missing_optional:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "latest_expected_migration": LATEST_EXPECTED_MIGRATION,
        "checks": results,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
    }


def check_schema_health(db) -> Dict[str, Any]:
    """Run every probe against the live DB and summarize. Guarded end-to-end:
    exposes only table/column names and states — never row data or secrets."""
    results: List[Dict[str, Any]] = []
    for c in CHECKS:
        state = probe(db, c["table"], c["column"])
        results.append({**c, "state": state})
    return summarize(results)
