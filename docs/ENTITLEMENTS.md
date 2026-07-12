# Plan Entitlements

The **single source of truth** is `app/services/entitlements.py`. The API
(`GET /user/subscription`), the competitor-limit gate, the Stripe webhook
handler, and the watchlist cap all resolve through it. The frontend renders the
`limits` / `features` / `subscription_state` it returns — it never grants access
on its own; the backend re-enforces every gate.

Operator-tunable numbers (competitor caps, scan intervals) come from
`app/core/config.py` env settings; everything else is defined in the module.

## Authoritative state

Plan state lives on `user_profiles`:
- `tier` — `free | pro | agency | developer` (managed by the webhook handler)
- `subscription_status` — raw Stripe status

`resolve_tier()` fails closed to `free` for a missing/unknown tier.

## Matrix

| Capability | Free | Pro | Agency | Developer |
|---|---|---|---|---|
| Tracked competitors | 1 | 10 | 50 | 50 |
| Automatic scan cadence | Weekly (168h) | Daily (24h) | Twice daily (12h) | 12h |
| On-demand rescan | ✅ (~1 min cooldown) | ✅ | ✅ | ✅ |
| Historical retention | Current only (0d) | 90 days | Full (3650d) | Full |
| Price-history chart | Teaser (last points) | Full window | Full | Full |
| Saved/pinned products | 3 | 25 | 25 | 25 |
| Real-time change alerts | — (weekly summary only) | ✅ | ✅ | ✅ |
| Weekly AI digest email | — | ✅ | ✅ | ✅ |
| Intelligence Pro (AI summary) | — (locked) | ✅ | ✅ | ✅ |
| Winning products (with "why") | Top 3, no why | ✅ | ✅ | ✅ |
| Gap analysis detail | Top 3 titles | ✅ full | ✅ | ✅ |
| Head-to-head comparison | Diagnosis only | ✅ prescription | ✅ | ✅ |
| Quick wins | 2 | All | All | All |
| Playbook plays | 4 | All | All | All |
| Dashboard action items | 2 | 5 | 5 | 5 |
| CSV export | — (403) | ✅ | ✅ | ✅ |
| API keys / developer access | — (403) | ✅ | ✅ | ✅ |
| Team seats | — | — | ✅ | — |

Notes:
- **No plan is "manual-only."** Every tier gets automatic scans (free = weekly),
  so the UI never labels a plan "Manual" and always shows a truthful next-scan
  cadence. On-demand rescans are available to all tiers with a short
  per-competitor cooldown (not a plan-based limit).
- "Developer" is an internal/API tier — it is not offered on the public pricing
  page.

## Subscription-state handling

`subscription_state(profile)` → `active | trialing | past_due | canceled | inactive | none`.

| State | Access | UI |
|---|---|---|
| `active` / `trialing` | full paid | tier badge |
| `past_due` | **paid retained** (grace during Stripe retries; webhook updates status, not tier) | "Payment past due — update your card" warning |
| cancel-at-period-end | paid until period end (Stripe keeps status `active`, then emits `subscription.deleted`) | "Canceled — access until end of period" note |
| `canceled` / `unpaid` / `inactive` (post-deletion) | free | free tier |
| missing row / webhook delay | free (fail-closed); a paid `tier` with no status yet is treated as active so a just-upgraded user isn't denied features in the webhook gap | — |

## Enforcement points (server-side, authoritative)

Competitor limit `competitors.py` (402 `competitor_limit_reached`) · discovery
limit `competitors.py` (402, free 1/mo) · history `competitors.py:/snapshots`
(402 `history_locked`) · price-history teaser `competitors.py:/price-history` ·
AI summary `competitors.py:/ai-summary` (402) · winning-products / gaps /
comparison / quick-wins / action-items / playbook slicing · CSV export (403) ·
watchlist cap `watchlist.py` · API keys `api_keys.py` (403) · team `team.py`
(403 agency-only) · alerts/digests `tasks/alerts.py`, `tasks/scheduler.py`
(restricted to `tier in (pro,agency)` **and** `subscription_status == "active"`).

## Changing a limit

Edit `app/services/entitlements.py` (and, for competitor caps / scan intervals,
the corresponding `app/core/config.py` env default). `tests/test_entitlements.py`
locks the matrix; `frontend/lib/entitlements.test.ts` locks the display labels.
Do **not** re-introduce a per-file limits map.
