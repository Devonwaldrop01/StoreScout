"use client";

/**
 * Internal admin console for the verified Shopify store index.
 * Token-gated (ADMIN_TOKEN on the backend; endpoints are hard-disabled while
 * that env var is empty). Not linked from anywhere in the product UI.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Database, RefreshCw, Check, X, AlertTriangle, Plus, Play, LogOut, Search, Crosshair,
} from "lucide-react";
import { EngineControls } from "@/components/admin/EngineControls";

const TOKEN_KEY = "ss_admin_token";

interface IndexRow {
  domain: string;
  brand_name: string | null;
  category: string | null;
  subcategory: string | null;
  status: string;
  verification_confidence: number | null;
  product_count: number | null;
  median_price: number | null;
  promo_rate: number | null;
  source: string | null;
  source_query: string | null;
  failure_reason: string | null;
  business_stage?: string | null;
  pricing_tier?: string | null;
  last_verified_at: string | null;
  created_at: string | null;
}

interface RunRow {
  ran_at: string;
  trigger: string | null;
  processed: number;
  verified: number;
  rejected: number;
  failed: number;
  duplicates: number;
  reverified: number;
  source_counts: Record<string, number> | null;
}

interface Stats {
  total: number;
  verified: number;
  candidates: number;
  rejected: number;
  failed: number;
  added_today: number;
  verified_today?: number;
  success_rate?: number | null;
  avg_confidence?: number | null;
  categories?: { name: string; count: number }[];
  sources?: { name: string; count: number }[];
  top_failures?: { reason: string; count: number }[];
  runs?: RunRow[];
  rows: IndexRow[];
}

const STATUS_COLOR: Record<string, string> = {
  verified: "#4CC38A",
  candidate: "#7DB8C9",
  rejected: "#F2555A",
  failed: "#6C7164",
};

async function adminFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": token,
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(typeof err.detail === "string" ? err.detail : "Request failed"), { status: res.status });
  }
  return res.json();
}

export default function StoreIndexAdminPage() {
  const [token, setToken] = useState<string>("");
  const [tokenInput, setTokenInput] = useState("");
  const [authed, setAuthed] = useState(false);
  const [authError, setAuthError] = useState("");

  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);

  const [filterStatus, setFilterStatus] = useState("");
  const [filterDomain, setFilterDomain] = useState("");

  const [seedText, setSeedText] = useState("");
  const [seedResult, setSeedResult] = useState("");
  const [seeding, setSeeding] = useState(false);

  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState("");

  const loadStats = useCallback(async (tok: string, status = "", domain = "") => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (status) params.set("status", status);
      if (domain) params.set("domain", domain);
      const r = await adminFetch<{ data: Stats }>(`/admin/store-index/stats?${params}`, tok);
      setStats(r.data);
      setAuthed(true);
      setAuthError("");
    } catch (e: unknown) {
      const status403 = (e as { status?: number })?.status === 403;
      setAuthed(false);
      setAuthError(status403 ? "Invalid token (or ADMIN_TOKEN not set on the backend)." : "Couldn't reach the backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Try a stored token on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(TOKEN_KEY) || "";
      if (stored) {
        setToken(stored);
        loadStats(stored);
      }
    } catch { /* ignore */ }
  }, [loadStats]);

  function handleLogin() {
    const t = tokenInput.trim();
    if (!t) return;
    try { localStorage.setItem(TOKEN_KEY, t); } catch { /* ignore */ }
    setToken(t);
    loadStats(t);
  }

  function handleLogout() {
    try { localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ }
    setToken("");
    setTokenInput("");
    setAuthed(false);
    setStats(null);
  }

  async function handleSeed() {
    const urls = seedText.split(/[\n,\s]+/).map((u) => u.trim()).filter(Boolean);
    if (urls.length === 0 || seeding) return;
    setSeeding(true);
    setSeedResult("");
    try {
      const r = await adminFetch<{ inserted: number; duplicates: number }>(
        "/admin/store-index/seed", token,
        { method: "POST", body: JSON.stringify({ urls }) },
      );
      setSeedResult(`Seeded ${r.inserted} new candidate${r.inserted === 1 ? "" : "s"} (${r.duplicates} already known).`);
      setSeedText("");
      loadStats(token, filterStatus, filterDomain);
    } catch (e: unknown) {
      setSeedResult((e as Error).message || "Seeding failed.");
    } finally {
      setSeeding(false);
    }
  }

  async function handleRun() {
    if (running) return;
    setRunning(true);
    setRunResult("");
    try {
      const r = await adminFetch<{ status: string; result?: Record<string, number>; limit: number }>(
        "/admin/store-index/run", token,
        { method: "POST", body: JSON.stringify({ limit: 10 }) },
      );
      if (r.status === "queued") {
        setRunResult("Test run queued (10 domains) — refresh stats in ~a minute.");
      } else {
        const res = r.result || {};
        setRunResult(`Run complete: ${res.processed ?? 0} processed — ${res.verified ?? 0} verified, ${res.rejected ?? 0} rejected, ${res.failed ?? 0} failed.`);
        loadStats(token, filterStatus, filterDomain);
      }
    } catch (e: unknown) {
      setRunResult((e as Error).message || "Run failed.");
    } finally {
      setRunning(false);
    }
  }

  // ── Token gate ───────────────────────────────────────────────────────────
  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" style={{ background: "var(--bg)" }}>
        <div className="w-full max-w-sm rounded-md p-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-1">
            <Database className="w-4 h-4" style={{ color: "var(--accent)" }} />
            <h1 className="text-sm font-bold" style={{ color: "var(--text)" }}>Store Index — Admin</h1>
          </div>
          <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
            Enter the admin token (ADMIN_TOKEN on the backend).
          </p>
          <input
            type="password"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleLogin(); }}
            placeholder="Admin token"
            className="w-full text-sm rounded-md px-3 py-2 outline-none mb-3"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
          />
          {authError && <p className="text-xs mb-3" style={{ color: "#F2555A" }}>{authError}</p>}
          <button
            onClick={handleLogin}
            disabled={!tokenInput.trim() || loading}
            className="w-full text-sm font-semibold px-4 py-2 rounded-md transition-all hover:brightness-110 disabled:opacity-40"
            style={{ background: "var(--accent)", color: "var(--ink)" }}
          >
            {loading ? "Checking…" : "Open console"}
          </button>
        </div>
      </div>
    );
  }

  // ── Console ──────────────────────────────────────────────────────────────
  const tiles = stats ? [
    { label: "Total", value: String(stats.total.toLocaleString()), color: "var(--text)" },
    { label: "Verified", value: String(stats.verified.toLocaleString()), color: STATUS_COLOR.verified },
    { label: "Verified today", value: String(stats.verified_today ?? 0), color: STATUS_COLOR.verified },
    { label: "Candidates", value: String(stats.candidates.toLocaleString()), color: STATUS_COLOR.candidate },
    { label: "Success rate", value: stats.success_rate != null ? `${stats.success_rate}%` : "—", color: "var(--text-2)" },
    { label: "Avg confidence", value: stats.avg_confidence != null ? `${stats.avg_confidence}%` : "—", color: "var(--text-2)" },
    { label: "Rejected", value: String(stats.rejected.toLocaleString()), color: STATUS_COLOR.rejected },
    { label: "Added today", value: String(stats.added_today), color: "var(--accent)" },
  ] : [];

  const maxCat = Math.max(1, ...(stats?.categories ?? []).map((c) => c.count));

  return (
    <div className="min-h-screen px-5 sm:px-8 py-8" style={{ background: "var(--bg)" }}>
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="tick-label mb-1">Internal · not linked in product</p>
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5" style={{ color: "var(--accent)" }} />
              <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>
                Verified Shopify Store Index
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/admin/leads"
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06]"
              style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
            >
              <Crosshair className="w-3.5 h-3.5" /> Leads
            </Link>
            <button
              onClick={() => loadStats(token, filterStatus, filterDomain)}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06]"
              style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
            </button>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06]"
              style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
            >
              <LogOut className="w-3.5 h-3.5" /> Sign out
            </button>
          </div>
        </div>

        {/* Stat tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          {tiles.map((t) => (
            <div key={t.label} className="rounded-md px-4 py-3" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <p className="label-caps mb-1">{t.label}</p>
              <p className="num text-xl font-bold" style={{ color: t.color }}>{t.value}</p>
            </div>
          ))}
        </div>

        {/* Quality panels: category distribution · sources · failures */}
        {stats && ((stats.categories?.length ?? 0) > 0 || (stats.sources?.length ?? 0) > 0 || (stats.top_failures?.length ?? 0) > 0) && (
          <div className="grid md:grid-cols-3 gap-4">
            <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <p className="label-caps mb-3">Verified by category</p>
              {(stats.categories?.length ?? 0) === 0 ? (
                <p className="text-xs" style={{ color: "var(--muted)" }}>Builds as stores verify.</p>
              ) : (
                <div className="space-y-2">
                  {stats.categories!.map((c) => (
                    <div key={c.name}>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-xs" style={{ color: "var(--text-2)" }}>{c.name}</span>
                        <span className="num text-xs" style={{ color: "var(--muted)" }}>{c.count}</span>
                      </div>
                      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg3)" }}>
                        <div className="h-full rounded-full" style={{ width: `${(c.count / maxCat) * 100}%`, background: "#4A4E44" }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <p className="label-caps mb-3">Discovery sources</p>
              {(stats.sources?.length ?? 0) === 0 ? (
                <p className="text-xs" style={{ color: "var(--muted)" }}>No rows yet.</p>
              ) : (
                <div className="space-y-1.5">
                  {stats.sources!.map((s) => (
                    <div key={s.name} className="flex items-center justify-between">
                      <span className="num text-xs" style={{ color: "var(--text-2)" }}>{s.name}</span>
                      <span className="num text-xs font-bold" style={{ color: "var(--text)" }}>{s.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <p className="label-caps mb-3">Most common failures</p>
              {(stats.top_failures?.length ?? 0) === 0 ? (
                <p className="text-xs" style={{ color: "var(--muted)" }}>None recorded — good sign.</p>
              ) : (
                <div className="space-y-1.5">
                  {stats.top_failures!.map((f) => (
                    <div key={f.reason} className="flex items-start justify-between gap-2">
                      <span className="text-[11px] leading-snug" style={{ color: "var(--text-2)" }}>{f.reason}</span>
                      <span className="num text-xs font-bold shrink-0" style={{ color: STATUS_COLOR.rejected }}>{f.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Worker run history */}
        {(stats?.runs?.length ?? 0) > 0 && (
          <div className="rounded-md overflow-x-auto" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="label-caps px-4 pt-3 pb-1">Worker runs · last {stats!.runs!.length}</p>
            <table className="w-full text-left">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["When", "Trigger", "Processed", "Verified", "Rejected", "Failed", "Re-verified", "Sources"].map((h) => (
                    <th key={h} className="label-caps px-4 py-2 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stats!.runs!.map((r, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td className="px-4 py-2 num text-xs" style={{ color: "var(--text-2)" }}>{new Date(r.ran_at).toLocaleString()}</td>
                    <td className="px-4 py-2 text-xs" style={{ color: "var(--muted)" }}>{r.trigger ?? "—"}</td>
                    <td className="px-4 py-2 num text-xs" style={{ color: "var(--text-2)" }}>{r.processed}</td>
                    <td className="px-4 py-2 num text-xs font-bold" style={{ color: STATUS_COLOR.verified }}>{r.verified}</td>
                    <td className="px-4 py-2 num text-xs" style={{ color: STATUS_COLOR.rejected }}>{r.rejected}</td>
                    <td className="px-4 py-2 num text-xs" style={{ color: STATUS_COLOR.failed }}>{r.failed}</td>
                    <td className="px-4 py-2 num text-xs" style={{ color: "var(--muted)" }}>{r.reverified}</td>
                    <td className="px-4 py-2 num text-[11px]" style={{ color: "var(--muted)" }}>
                      {r.source_counts ? Object.entries(r.source_counts).map(([k, v]) => `${k}:${v}`).join(" · ") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Runtime engine controls */}
        <EngineControls
          token={token}
          title="Daily discovery worker"
          knobs={[
            { key: "shopify_index_enabled", label: "Automatic daily discovery", type: "toggle", help: "Runs at 04:30 UTC. Manual test runs below always work regardless." },
            { key: "shopify_index_daily_verified_target", label: "New verified stores / day", type: "number", min: 1, max: 250, help: "Dev 25–50 · early prod 50–100 · scaled 100–250" },
            { key: "shopify_index_daily_candidate_limit", label: "Request budget / day", type: "number", min: 1, max: 500, help: "Hard cap on domains processed" },
          ]}
        />

        {/* Actions row */}
        <div className="grid md:grid-cols-2 gap-4">
          {/* Seed */}
          <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 mb-2">
              <Plus className="w-3.5 h-3.5" style={{ color: "var(--text-2)" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Seed candidate URLs</p>
            </div>
            <textarea
              value={seedText}
              onChange={(e) => setSeedText(e.target.value)}
              rows={3}
              placeholder={"gymshark.com\nallbirds.com\nryderwear.com"}
              className="w-full text-xs num rounded-md px-3 py-2 resize-none outline-none mb-2"
              style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
            />
            <div className="flex items-center justify-between gap-3">
              <p className="text-[11px]" style={{ color: "var(--muted)" }}>One per line — processed by the next run.</p>
              <button
                onClick={handleSeed}
                disabled={seeding || !seedText.trim()}
                className="text-xs font-semibold px-3 py-1.5 rounded-md transition-all hover:brightness-110 disabled:opacity-40 shrink-0"
                style={{ background: "var(--accent)", color: "var(--ink)" }}
              >
                {seeding ? "Seeding…" : "Seed"}
              </button>
            </div>
            {seedResult && <p className="text-xs mt-2" style={{ color: "var(--text-2)" }}>{seedResult}</p>}
          </div>

          {/* Test run */}
          <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 mb-2">
              <Play className="w-3.5 h-3.5" style={{ color: "var(--text-2)" }} />
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Test indexing run</p>
            </div>
            <p className="text-xs mb-3 leading-relaxed" style={{ color: "var(--muted)" }}>
              Processes up to 10 candidates now (verify → light scan → classify → upsert). Bypasses the
              SHOPIFY_INDEX_ENABLED flag; caps and politeness still apply.
            </p>
            <button
              onClick={handleRun}
              disabled={running}
              className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md transition-all hover:brightness-110 disabled:opacity-40"
              style={{ background: "var(--accent)", color: "var(--ink)" }}
            >
              {running ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              {running ? "Running…" : "Run 10 domains"}
            </button>
            {runResult && <p className="text-xs mt-2" style={{ color: "var(--text-2)" }}>{runResult}</p>}
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          {["", "verified", "candidate", "rejected", "failed"].map((s) => (
            <button
              key={s || "all"}
              onClick={() => { setFilterStatus(s); loadStats(token, s, filterDomain); }}
              className="text-xs font-medium px-3 py-1.5 rounded-md transition-all"
              style={{
                background: filterStatus === s ? "var(--bg3)" : "transparent",
                border: "1px solid var(--border)",
                color: filterStatus === s ? "var(--text)" : "var(--muted)",
              }}
            >
              {s || "All"}
            </button>
          ))}
          <div className="flex items-center gap-1.5 ml-auto rounded-md px-2.5 py-1.5" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
            <Search className="w-3.5 h-3.5" style={{ color: "var(--muted)" }} />
            <input
              value={filterDomain}
              onChange={(e) => setFilterDomain(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") loadStats(token, filterStatus, filterDomain); }}
              placeholder="Filter by domain…"
              className="bg-transparent outline-none text-xs w-40"
              style={{ color: "var(--text)" }}
            />
          </div>
        </div>

        {/* Table */}
        <div className="rounded-md overflow-x-auto" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          {(stats?.rows.length ?? 0) === 0 ? (
            <div className="p-10 text-center">
              <Database className="w-7 h-7 mx-auto mb-3" style={{ color: "var(--muted)", opacity: 0.4 }} />
              <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>Index is empty{filterStatus || filterDomain ? " for this filter" : ""}</p>
              <p className="text-xs max-w-sm mx-auto" style={{ color: "var(--muted)" }}>
                Seed a few URLs above and hit &quot;Run 10 domains&quot; — verified stores will appear here and start powering competitor discovery.
              </p>
            </div>
          ) : (
            <table className="w-full text-left">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Domain", "Status", "Conf.", "Category", "Products", "Median", "Promo", "Source", "Note"].map((h) => (
                    <th key={h} className="label-caps px-3 py-2.5 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stats!.rows.map((r) => (
                  <tr key={r.domain} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td className="px-3 py-2">
                      <p className="num text-xs font-semibold" style={{ color: "var(--text)" }}>{r.domain}</p>
                      {r.brand_name && <p className="text-[11px]" style={{ color: "var(--muted)" }}>{r.brand_name}</p>}
                    </td>
                    <td className="px-3 py-2">
                      <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: STATUS_COLOR[r.status] ?? "var(--muted)" }}>
                        {r.status === "verified" ? <Check className="w-3 h-3" /> : r.status === "rejected" ? <X className="w-3 h-3" /> : r.status === "failed" ? <AlertTriangle className="w-3 h-3" /> : null}
                        {r.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 num text-xs" style={{ color: "var(--text-2)" }}>
                      {r.verification_confidence != null ? `${r.verification_confidence}%` : "—"}
                    </td>
                    <td className="px-3 py-2 text-xs" style={{ color: "var(--text-2)" }}>
                      {r.category ? `${r.category}${r.subcategory ? ` · ${r.subcategory}` : ""}` : "—"}
                      {(r.business_stage || r.pricing_tier) && (
                        <p className="text-[11px]" style={{ color: "var(--muted)" }}>
                          {[r.business_stage, r.pricing_tier].filter(Boolean).join(" · ")}
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-2 num text-xs" style={{ color: "var(--text-2)" }}>{r.product_count ?? "—"}</td>
                    <td className="px-3 py-2 num text-xs" style={{ color: "var(--text-2)" }}>{r.median_price != null ? `$${r.median_price}` : "—"}</td>
                    <td className="px-3 py-2 num text-xs" style={{ color: "var(--text-2)" }}>{r.promo_rate != null ? `${r.promo_rate}%` : "—"}</td>
                    <td className="px-3 py-2 text-xs" style={{ color: "var(--muted)" }}>{r.source ?? "—"}</td>
                    <td className="px-3 py-2 text-[11px] max-w-[220px] truncate" style={{ color: "var(--muted)" }} title={r.failure_reason || r.source_query || ""}>
                      {r.failure_reason || r.source_query || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <p className="text-[11px]" style={{ color: "var(--muted)", opacity: 0.6 }}>
          Latest 50 rows by update time. Daily worker: SHOPIFY_INDEX_ENABLED · limit {""}
          SHOPIFY_INDEX_DAILY_CANDIDATE_LIMIT · threshold SHOPIFY_INDEX_MIN_CONFIDENCE.
        </p>
      </div>
    </div>
  );
}
