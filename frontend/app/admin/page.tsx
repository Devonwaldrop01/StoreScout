"use client";

/**
 * The admin operating system's home: a Morning Executive Brief.
 * StoreScout's philosophy applied to itself — what happened, why it matters,
 * and the ONE thing to do today. Every number is a real database fact;
 * MRR is explicitly an estimate; nothing unmeasurable is faked.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Sunrise, Database, Crosshair, RefreshCw, LogOut, Zap, TrendingDown, Lightbulb,
} from "lucide-react";

const TOKEN_KEY = "ss_admin_token";

interface Brief {
  generated_at: string;
  priority: string;
  business: { users_total: number; users_24h: number; users_7d: number; pro: number; agency: number; mrr_estimate: number };
  funnel: { stage: string; count: number }[];
  biggest_drop: { from: string; to: string; lost: number; rate: number } | null;
  health: { competitors_active: number; scans_24h: number; scan_errors: number; scans_stuck?: number; changes_24h: number; failed_jobs?: { hostname: string | null; error: string; at: string }[] };
  engines: {
    index_verified: number; index_verified_24h: number;
    last_index_run: { ran_at: string; verified: number; processed: number; failed: number } | null;
    leads_ready: number; leads_today: number; leads_contacted: number; leads_replied: number; leads_customers: number;
  };
  content_ideas: string[];
}

async function adminFetch<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`/api/v1${path}`, { headers: { "X-Admin-Token": token } });
  if (!res.ok) throw Object.assign(new Error(String(res.status)), { status: res.status });
  return res.json();
}

export default function AdminHomePage() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [authed, setAuthed] = useState(false);
  const [authError, setAuthError] = useState("");
  const [brief, setBrief] = useState<Brief | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (tok: string) => {
    setLoading(true);
    try {
      const r = await adminFetch<{ data: Brief }>("/admin/brief", tok);
      setBrief(r.data);
      setAuthed(true);
      setAuthError("");
    } catch (e: unknown) {
      setAuthed(false);
      setAuthError((e as { status?: number })?.status === 403
        ? "Invalid token (or ADMIN_TOKEN not set on the backend)."
        : "Couldn't reach the backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(TOKEN_KEY) || "";
      if (stored) { setToken(stored); load(stored); }
    } catch { /* ignore */ }
  }, [load]);

  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" style={{ background: "var(--bg)" }}>
        <div className="w-full max-w-sm rounded-md p-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-1">
            <Sunrise className="w-4 h-4" style={{ color: "var(--accent)" }} />
            <h1 className="text-sm font-bold" style={{ color: "var(--text)" }}>StoreScout — Operating System</h1>
          </div>
          <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>Enter the admin token for the morning brief.</p>
          <input
            type="password"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && tokenInput.trim()) { try { localStorage.setItem(TOKEN_KEY, tokenInput.trim()); } catch {} setToken(tokenInput.trim()); load(tokenInput.trim()); } }}
            placeholder="Admin token"
            className="w-full text-sm rounded-md px-3 py-2 outline-none mb-3"
            style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
          />
          {authError && <p className="text-xs mb-3" style={{ color: "#F2555A" }}>{authError}</p>}
          <button
            onClick={() => { const t = tokenInput.trim(); if (!t) return; try { localStorage.setItem(TOKEN_KEY, t); } catch {} setToken(t); load(t); }}
            disabled={!tokenInput.trim() || loading}
            className="w-full text-sm font-semibold px-4 py-2 rounded-md transition-all hover:brightness-110 disabled:opacity-40"
            style={{ background: "var(--accent)", color: "var(--ink)" }}
          >
            {loading ? "Loading…" : "Open the brief"}
          </button>
        </div>
      </div>
    );
  }

  if (!brief) return null;
  const b = brief.business;
  const h = brief.health;
  const e = brief.engines;
  const maxFunnel = Math.max(1, ...brief.funnel.map((f) => f.count));

  return (
    <div className="min-h-screen px-5 sm:px-8 py-8" style={{ background: "var(--bg)" }}>
      <div className="max-w-4xl mx-auto space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="tick-label mb-1">Internal · operating system</p>
            <div className="flex items-center gap-2">
              <Sunrise className="w-5 h-5" style={{ color: "var(--accent)" }} />
              <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>Morning Brief</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/admin/store-index" className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06]" style={{ color: "var(--muted)", border: "1px solid var(--border)" }}>
              <Database className="w-3.5 h-3.5" /> Index
            </Link>
            <Link href="/admin/leads" className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06]" style={{ color: "var(--muted)", border: "1px solid var(--border)" }}>
              <Crosshair className="w-3.5 h-3.5" /> Leads
            </Link>
            <button onClick={() => load(token)} className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06]" style={{ color: "var(--muted)", border: "1px solid var(--border)" }}>
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button onClick={() => { try { localStorage.removeItem(TOKEN_KEY); } catch {} setAuthed(false); }} className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06]" style={{ color: "var(--muted)", border: "1px solid var(--border)" }}>
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Today's priority — the ONE thing */}
        <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: "3px solid var(--accent)" }}>
          <div className="flex items-start gap-3">
            <Zap className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "var(--accent)" }} />
            <div>
              <p className="label-caps mb-1" style={{ color: "var(--accent)" }}>Today&apos;s priority</p>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text)" }}>{brief.priority}</p>
            </div>
          </div>
        </div>

        {/* Business */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: "Users", value: b.users_total.toLocaleString(), color: "var(--text)" },
            { label: "New · 24h", value: String(b.users_24h), color: b.users_24h > 0 ? "#4CC38A" : "var(--muted)" },
            { label: "New · 7d", value: String(b.users_7d), color: "var(--text-2)" },
            { label: "Pro", value: String(b.pro), color: "#4CC38A" },
            { label: "Agency", value: String(b.agency), color: "#4CC38A" },
            { label: "MRR (est.)", value: `$${b.mrr_estimate.toLocaleString()}`, color: "var(--accent)" },
          ].map((t) => (
            <div key={t.label} className="rounded-md px-4 py-3" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <p className="label-caps mb-1">{t.label}</p>
              <p className="num text-xl font-bold" style={{ color: t.color }}>{t.value}</p>
            </div>
          ))}
        </div>

        {/* Funnel */}
        <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <p className="label-caps mb-3">Activation funnel · live database counts</p>
          <div className="space-y-2">
            {brief.funnel.map((f) => (
              <div key={f.stage}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs" style={{ color: "var(--text-2)" }}>{f.stage}</span>
                  <span className="num text-xs font-bold" style={{ color: "var(--text)" }}>{f.count}</span>
                </div>
                <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg3)" }}>
                  <div className="h-full rounded-full" style={{ width: `${(f.count / maxFunnel) * 100}%`, background: "#4A4E44" }} />
                </div>
              </div>
            ))}
          </div>
          {brief.biggest_drop && brief.biggest_drop.lost > 0 && (
            <p className="text-[11px] mt-3 flex items-center gap-1.5" style={{ color: "var(--muted)" }}>
              <TrendingDown className="w-3 h-3 shrink-0" style={{ color: "#F2555A" }} />
              Biggest leak: {brief.biggest_drop.from} → {brief.biggest_drop.to} ({brief.biggest_drop.rate}% convert, {brief.biggest_drop.lost} lost)
            </p>
          )}
        </div>

        {/* Health + Engines */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="label-caps mb-3">Platform health</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Tracked competitors", value: h.competitors_active, color: "var(--text)" },
                { label: "Scans · 24h", value: h.scans_24h, color: "var(--text-2)" },
                { label: "Scan errors", value: h.scan_errors, color: h.scan_errors > 0 ? "#F2555A" : "#4CC38A" },
                { label: "Changes · 24h", value: h.changes_24h, color: "var(--text-2)" },
              ].map((t) => (
                <div key={t.label}>
                  <p className="num text-lg font-bold" style={{ color: t.color }}>{t.value}</p>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--muted)" }}>{t.label}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <p className="label-caps mb-3">Engines</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Verified stores", value: e.index_verified, color: "var(--text)" },
                { label: "Verified · 24h", value: e.index_verified_24h, color: e.index_verified_24h > 0 ? "#4CC38A" : "var(--muted)" },
                { label: "Leads ready", value: e.leads_ready, color: e.leads_ready > 0 ? "var(--accent)" : "var(--muted)" },
                { label: "Replied / customers", value: `${e.leads_replied} / ${e.leads_customers}`, color: "#4CC38A" },
              ].map((t) => (
                <div key={t.label}>
                  <p className="num text-lg font-bold" style={{ color: t.color }}>{t.value}</p>
                  <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--muted)" }}>{t.label}</p>
                </div>
              ))}
            </div>
            {e.last_index_run && (
              <p className="text-[11px] mt-3" style={{ color: "var(--muted)" }}>
                Last index run: {e.last_index_run.verified} verified / {e.last_index_run.processed} processed · {new Date(e.last_index_run.ran_at).toLocaleString()}
              </p>
            )}
          </div>
        </div>

        {/* Worker health — recent failed scans */}
        {(h.failed_jobs?.length ?? 0) > 0 && (
          <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <div className="flex items-center gap-2 mb-3">
              <p className="label-caps">Recent failed scans</p>
              {(h.scans_stuck ?? 0) > 0 && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: "rgba(255,178,36,.12)", color: "var(--accent)" }}>
                  {h.scans_stuck} stuck scanning
                </span>
              )}
            </div>
            <div className="space-y-1.5">
              {h.failed_jobs!.map((j, i) => (
                <div key={i} className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="num text-xs font-semibold" style={{ color: "var(--text-2)" }}>{j.hostname}</p>
                    <p className="text-[11px] leading-snug" style={{ color: "var(--muted)" }}>{j.error || "—"}</p>
                  </div>
                  <span className="text-[10px] shrink-0" style={{ color: "var(--muted)" }}>{new Date(j.at).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Content opportunities — from real detected changes */}
        <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-3.5 h-3.5" style={{ color: "var(--text-2)" }} />
            <p className="label-caps">Content opportunities · from yesterday&apos;s real detections</p>
          </div>
          {brief.content_ideas.length === 0 ? (
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              No strong stories in the last 48h — ideas appear here whenever tracked competitors make notable moves.
            </p>
          ) : (
            <ul className="space-y-2">
              {brief.content_ideas.map((idea, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: "var(--accent)" }} />
                  <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>{idea}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <p className="text-[11px]" style={{ color: "var(--muted)", opacity: 0.6 }}>
          Generated {new Date(brief.generated_at).toLocaleString()} · every number is a live database fact · MRR is tier × list price (estimate) ·
          session analytics (paths, scroll depth) intentionally absent until an event pipeline exists — no fabricated metrics.
        </p>
      </div>
    </div>
  );
}
