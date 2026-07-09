"use client";

/**
 * Internal lead-pipeline console (growth engine — never customer-facing,
 * not linked anywhere in the product). Token-gated by ADMIN_TOKEN.
 *
 * The morning workflow: open this page, see today's highest-scoring
 * prospects with research + a grounded outreach draft already attached,
 * copy the email, mark Contacted, move on.
 */

import { useCallback, useEffect, useState } from "react";
import {
  Crosshair, RefreshCw, Check, Copy, Search, Play,
  ChevronDown, ChevronUp, X,
} from "lucide-react";
import { EngineControls } from "@/components/admin/EngineControls";

const TOKEN_KEY = "ss_admin_token";

interface Lead {
  id: string;
  domain: string;
  brand_name: string | null;
  category: string | null;
  subcategory: string | null;
  business_stage: string | null;
  pricing_tier: string | null;
  lead_score: number | null;
  qualification_score: number | null;
  score_reasons: string[] | null;
  disqualifiers: string[] | null;
  outreach_status: string;
  competitors_found: number | null;
  generated_insights: { findings?: string[]; competitors?: { domain: string; brand_name: string | null }[] } | null;
  recommended_angle: string | null;
  suggested_subject: string | null;
  suggested_email: string | null;
  notes: string | null;
  created_at: string;
}

interface LeadsData {
  rows: Lead[];
  counts: Record<string, number>;
  new_today: number;
  stages: string[];
}

const STATUS_META: Record<string, { label: string; color: string }> = {
  ready:            { label: "Ready",        color: "#FFB224" },
  research_complete:{ label: "Researched",   color: "#7DB8C9" },
  contacted:        { label: "Contacted",    color: "#7DB8C9" },
  replied:          { label: "Replied",      color: "#4CC38A" },
  demo_scheduled:   { label: "Demo",         color: "#4CC38A" },
  trial_started:    { label: "Trial",        color: "#4CC38A" },
  customer:         { label: "Customer",     color: "#4CC38A" },
  lost:             { label: "Lost",         color: "#6C7164" },
  never_contact:    { label: "Never contact",color: "#F2555A" },
  discovered:       { label: "Discovered",   color: "#6C7164" },
  qualified:        { label: "Qualified",    color: "#7DB8C9" },
};

function scoreColor(s: number | null): string {
  if (s == null) return "var(--muted)";
  if (s >= 80) return "#4CC38A";
  if (s >= 65) return "#FFB224";
  return "var(--muted)";
}

async function adminFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Admin-Token": token, ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(typeof err.detail === "string" ? err.detail : "Request failed"), { status: res.status });
  }
  return res.json();
}

// ── Lead card ───────────────────────────────────────────────────────────────

function LeadCard({ lead, token, onChanged }: { lead: Lead; token: string; onChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState(lead.notes ?? "");

  const meta = STATUS_META[lead.outreach_status] ?? { label: lead.outreach_status, color: "var(--muted)" };
  const findings = lead.generated_insights?.findings ?? [];

  function copy(text: string, key: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 1500);
    }).catch(() => {});
  }

  async function setStatus(status: string) {
    if (saving) return;
    setSaving(true);
    try {
      await adminFetch(`/admin/leads/${lead.id}`, token, { method: "PATCH", body: JSON.stringify({ outreach_status: status }) });
      onChanged();
    } catch { /* surfaced by refresh */ } finally { setSaving(false); }
  }

  async function saveNotes() {
    if (saving) return;
    setSaving(true);
    try {
      await adminFetch(`/admin/leads/${lead.id}`, token, { method: "PATCH", body: JSON.stringify({ notes }) });
    } catch { /* ignore */ } finally { setSaving(false); }
  }

  return (
    <div className="rounded-md overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      {/* Row header */}
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-4 px-4 py-3 text-left transition-colors hover:bg-white/[.02]">
        <div className="w-12 shrink-0 text-center">
          <p className="num text-xl font-bold leading-none" style={{ color: scoreColor(lead.lead_score) }}>{lead.lead_score ?? "—"}</p>
          <p className="text-[9px] uppercase tracking-wider mt-0.5" style={{ color: "var(--muted)" }}>score</p>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="num text-sm font-semibold" style={{ color: "var(--text)" }}>{lead.domain}</p>
            {lead.brand_name && <span className="text-xs" style={{ color: "var(--muted)" }}>{lead.brand_name}</span>}
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: `${meta.color}18`, color: meta.color }}>
              {meta.label}
            </span>
          </div>
          <p className="text-xs mt-0.5 truncate" style={{ color: "var(--text-2)" }}>
            {lead.recommended_angle || [lead.category, lead.business_stage, lead.pricing_tier].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="hidden sm:block text-right shrink-0">
          <p className="num text-xs" style={{ color: "var(--text-2)" }}>{lead.competitors_found ?? 0} rivals indexed</p>
          <p className="text-[11px]" style={{ color: "var(--muted)" }}>
            {[lead.category, lead.business_stage].filter(Boolean).join(" · ") || "—"}
          </p>
        </div>
        {open ? <ChevronUp className="w-4 h-4 shrink-0" style={{ color: "var(--muted)" }} /> : <ChevronDown className="w-4 h-4 shrink-0" style={{ color: "var(--muted)" }} />}
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="px-4 pb-4 space-y-4" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="grid md:grid-cols-2 gap-4 pt-4">
            {/* Why this lead */}
            <div>
              <p className="label-caps mb-2">Why this lead · qualification {lead.qualification_score ?? "—"}</p>
              <div className="space-y-1">
                {(lead.score_reasons ?? []).map((r, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <Check className="w-3 h-3 mt-0.5 shrink-0" style={{ color: "#4CC38A" }} />
                    <p className="text-xs leading-snug" style={{ color: "var(--text-2)" }}>{r}</p>
                  </div>
                ))}
                {(lead.disqualifiers ?? []).map((r, i) => (
                  <div key={`d${i}`} className="flex items-start gap-2">
                    <X className="w-3 h-3 mt-0.5 shrink-0" style={{ color: "#F2555A" }} />
                    <p className="text-xs leading-snug" style={{ color: "var(--muted)" }}>{r}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Research findings */}
            <div>
              <p className="label-caps mb-2">Market findings</p>
              {findings.length === 0 ? (
                <p className="text-xs" style={{ color: "var(--muted)" }}>No notable findings recorded.</p>
              ) : (
                <div className="space-y-1">
                  {findings.map((f, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: "var(--accent)" }} />
                      <p className="text-xs leading-snug" style={{ color: "var(--text-2)" }}>{f}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Email draft */}
          {lead.suggested_email && (
            <div className="rounded-md p-3" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
              <div className="flex items-center justify-between gap-3 mb-2">
                <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
                  <span className="label-caps mr-2" style={{ color: "var(--muted)" }}>Subject</span>
                  {lead.suggested_subject || "—"}
                </p>
                <button
                  onClick={() => copy(`Subject: ${lead.suggested_subject ?? ""}\n\n${lead.suggested_email}`, "email")}
                  className="flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded transition-all hover:bg-white/[.06] shrink-0"
                  style={{ color: copied === "email" ? "#4CC38A" : "var(--muted)", border: "1px solid var(--border)" }}
                >
                  {copied === "email" ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  {copied === "email" ? "Copied" : "Copy draft"}
                </button>
              </div>
              <p className="text-xs leading-relaxed whitespace-pre-wrap" style={{ color: "var(--text-2)" }}>{lead.suggested_email}</p>
            </div>
          )}

          {/* Notes + actions */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 flex gap-2">
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                onBlur={saveNotes}
                placeholder="Notes…"
                className="flex-1 text-xs rounded-md px-3 py-2 outline-none"
                style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              {[
                { s: "contacted", label: "Contacted" },
                { s: "replied", label: "Replied" },
                { s: "customer", label: "Customer" },
                { s: "lost", label: "Skip" },
                { s: "never_contact", label: "Never" },
              ].map(({ s, label }) => (
                <button
                  key={s}
                  onClick={() => setStatus(s)}
                  disabled={saving || lead.outreach_status === s}
                  className="text-[11px] font-semibold px-2.5 py-1.5 rounded-md transition-all hover:brightness-110 disabled:opacity-40"
                  style={
                    s === "contacted"
                      ? { background: "var(--accent)", color: "var(--ink)" }
                      : { background: "var(--bg3)", border: "1px solid var(--border)", color: STATUS_META[s]?.color ?? "var(--text-2)" }
                  }
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────

export default function LeadsAdminPage() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [authed, setAuthed] = useState(false);
  const [authError, setAuthError] = useState("");

  const [data, setData] = useState<LeadsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [q, setQ] = useState("");
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState("");

  const load = useCallback(async (tok: string, status = "", query = "") => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (status) params.set("status", status);
      if (query) params.set("q", query);
      const r = await adminFetch<{ data: LeadsData }>(`/admin/leads?${params}`, tok);
      setData(r.data);
      setAuthed(true);
      setAuthError("");
      try { window.dispatchEvent(new Event("ss-admin-auth")); } catch { /* ignore */ }
    } catch (e: unknown) {
      const s403 = (e as { status?: number })?.status === 403;
      setAuthed(false);
      setAuthError(s403 ? "Invalid token (or ADMIN_TOKEN not set on the backend)." : "Couldn't reach the backend.");
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

  function handleLogin() {
    const t = tokenInput.trim();
    if (!t) return;
    try { localStorage.setItem(TOKEN_KEY, t); } catch { /* ignore */ }
    setToken(t);
    load(t);
  }

  async function handleRun() {
    if (running) return;
    setRunning(true);
    setRunResult("");
    try {
      const r = await adminFetch<{ status: string; result?: Record<string, number> }>(
        "/admin/leads/run", token, { method: "POST", body: JSON.stringify({ limit: 5 }) },
      );
      if (r.status === "queued") setRunResult("Discovery queued (5 prospects) — refresh in ~a minute.");
      else {
        const res = r.result || {};
        setRunResult(`Run complete: ${res.created ?? 0} prospects created (${res.examined ?? 0} examined, ${res.below_threshold ?? 0} below threshold).`);
        load(token, filterStatus, q);
      }
    } catch (e: unknown) {
      setRunResult((e as Error).message || "Run failed.");
    } finally {
      setRunning(false);
    }
  }

  if (!authed) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6" style={{ background: "var(--bg)" }}>
        <div className="w-full max-w-sm rounded-md p-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-1">
            <Crosshair className="w-4 h-4" style={{ color: "var(--accent)" }} />
            <h1 className="text-sm font-bold" style={{ color: "var(--text)" }}>Lead Engine — Admin</h1>
          </div>
          <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>Enter the admin token (ADMIN_TOKEN on the backend).</p>
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

  const counts = data?.counts ?? {};
  const tiles = [
    { label: "New today", value: data?.new_today ?? 0, color: "var(--accent)" },
    { label: "Ready", value: counts.ready ?? 0, color: STATUS_META.ready.color },
    { label: "Contacted", value: counts.contacted ?? 0, color: STATUS_META.contacted.color },
    { label: "Replied", value: counts.replied ?? 0, color: STATUS_META.replied.color },
    { label: "Customers", value: (counts.customer ?? 0) + (counts.trial_started ?? 0), color: STATUS_META.customer.color },
    { label: "Total", value: Object.values(counts).reduce((a, b) => a + b, 0), color: "var(--text)" },
  ];

  return (
    <div className="min-h-screen px-5 sm:px-8 py-8" style={{ background: "var(--bg)" }}>
      <div className="max-w-5xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="tick-label mb-1">Internal growth engine · not customer-facing</p>
            <div className="flex items-center gap-2">
              <Crosshair className="w-5 h-5" style={{ color: "var(--accent)" }} />
              <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--text)" }}>Lead Discovery</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRun}
              disabled={running}
              className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-md transition-all hover:brightness-110 disabled:opacity-40"
              style={{ background: "var(--accent)", color: "var(--ink)" }}
            >
              {running ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              {running ? "Running…" : "Discover 5 now"}
            </button>
            <button
              onClick={() => load(token, filterStatus, q)}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06]"
              style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>
        </div>

        {runResult && (
          <p className="text-xs px-3 py-2 rounded-md" style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text-2)" }}>
            {runResult}
          </p>
        )}

        {/* Runtime engine controls */}
        <EngineControls
          token={token}
          title="Daily lead discovery"
          knobs={[
            { key: "lead_engine_enabled", label: "Automatic daily discovery", type: "toggle", help: "Runs at 05:30 UTC after the index refresh. \"Discover 5 now\" always works regardless." },
            { key: "lead_engine_daily_target", label: "Prospects / day", type: "number", min: 1, max: 50, help: "High-quality target — dev 20" },
            { key: "lead_engine_min_qualification", label: "Min qualification score", type: "number", min: 0, max: 100, help: "Below this a store never becomes a prospect" },
          ]}
        />

        {/* Tiles */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
          {tiles.map((t) => (
            <div key={t.label} className="rounded-md px-4 py-3" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <p className="label-caps mb-1">{t.label}</p>
              <p className="num text-xl font-bold" style={{ color: t.color }}>{t.value}</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          {["", "ready", "contacted", "replied", "customer", "lost"].map((s) => (
            <button
              key={s || "all"}
              onClick={() => { setFilterStatus(s); load(token, s, q); }}
              className="text-xs font-medium px-3 py-1.5 rounded-md transition-all"
              style={{
                background: filterStatus === s ? "var(--bg3)" : "transparent",
                border: "1px solid var(--border)",
                color: filterStatus === s ? "var(--text)" : "var(--muted)",
              }}
            >
              {s ? (STATUS_META[s]?.label ?? s) : "All"}
            </button>
          ))}
          <div className="flex items-center gap-1.5 ml-auto rounded-md px-2.5 py-1.5" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
            <Search className="w-3.5 h-3.5" style={{ color: "var(--muted)" }} />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") load(token, filterStatus, q); }}
              placeholder="Search domain or brand…"
              className="bg-transparent outline-none text-xs w-44"
              style={{ color: "var(--text)" }}
            />
          </div>
        </div>

        {/* Lead list — highest score first */}
        {(data?.rows.length ?? 0) === 0 ? (
          <div className="rounded-md p-10 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
            <Crosshair className="w-7 h-7 mx-auto mb-3" style={{ color: "var(--muted)", opacity: 0.4 }} />
            <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>No prospects{filterStatus || q ? " for this filter" : " yet"}</p>
            <p className="text-xs max-w-sm mx-auto" style={{ color: "var(--muted)" }}>
              The lead engine draws from verified stores in the index — grow the index first, then hit
              &quot;Discover 5 now&quot; to qualify and research your first prospects.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {data!.rows.map((lead) => (
              <LeadCard key={lead.id} lead={lead} token={token} onChanged={() => load(token, filterStatus, q)} />
            ))}
          </div>
        )}

        <p className="text-[11px]" style={{ color: "var(--muted)", opacity: 0.6 }}>
          Sorted by lead score. Daily worker: LEAD_ENGINE_ENABLED · target LEAD_ENGINE_DAILY_TARGET ·
          threshold LEAD_ENGINE_MIN_QUALIFICATION. Outcomes you mark here feed back into scoring.
        </p>
      </div>
    </div>
  );
}
