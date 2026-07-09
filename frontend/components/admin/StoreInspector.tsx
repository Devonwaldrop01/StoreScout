"use client";

/**
 * Store Inspector — click any indexed store to see everything StoreScout knows
 * about it and act on it: verification status + reason, discovery provenance
 * and stage timestamps, the multi-signal category with its confidence and
 * evidence ("why we classified it this way"), price bands, catalog stats,
 * target customer, brand keywords, related stores (graph foundation), and
 * one-click re-run of verification or knowledge.
 */

import { useCallback, useEffect, useState } from "react";
import { X, RefreshCw, Check, AlertTriangle, ExternalLink, Brain, ShieldCheck } from "lucide-react";

interface StoreRow {
  domain: string;
  brand_name: string | null;
  status: string;
  category: string | null;
  subcategory: string | null;
  category_confidence: number | null;
  category_evidence: { signal: string; detail: string; weight: number }[] | null;
  verification_confidence: number | null;
  verification_signals: string[] | null;
  rejection_reason: string | null;
  failure_reason: string | null;
  discovery_source: string | null;
  source: string | null;
  discovered_at: string | null;
  verified_at: string | null;
  knowledge_at: string | null;
  product_count: number | null;
  collection_count: number | null;
  median_price: number | null;
  min_price: number | null;
  max_price: number | null;
  price_bands: { p25?: number; p50?: number; p75?: number } | null;
  promo_rate: number | null;
  business_stage: string | null;
  pricing_tier: string | null;
  target_customer: string | null;
  brand_keywords: string[] | null;
  homepage_message: string | null;
}

interface InspectorData {
  store: StoreRow;
  related: { domain: string; weight: number }[];
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

const STATUS_COLOR: Record<string, string> = {
  verified: "#4CC38A", discovered: "#7DB8C9", candidate: "#7DB8C9", rejected: "#F2555A", failed: "#6C7164",
};

function fmtDate(s: string | null) {
  return s ? new Date(s).toLocaleString() : "—";
}

export function StoreInspector({ domain, token, onClose, onChanged }: {
  domain: string; token: string; onClose: () => void; onChanged?: () => void;
}) {
  const [data, setData] = useState<InspectorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string>("");
  const [actionMsg, setActionMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const r = await adminFetch<{ data: InspectorData }>(`/admin/store-inspector/${encodeURIComponent(domain)}`, token);
      setData(r.data);
    } catch (e: unknown) {
      setError((e as Error).message || "Couldn't load this store.");
    } finally {
      setLoading(false);
    }
  }, [domain, token]);

  useEffect(() => { load(); }, [load]);

  async function runAction(action: "reverify" | "reclassify") {
    if (busy) return;
    setBusy(action);
    setActionMsg("");
    try {
      const r = await adminFetch<{ data: Record<string, unknown> }>(
        `/admin/store-inspector/${encodeURIComponent(domain)}/action`, token,
        { method: "POST", body: JSON.stringify({ action }) },
      );
      const d = r.data || {};
      setActionMsg(action === "reverify"
        ? `Verification: ${d.outcome ?? "done"}${d.reason ? ` (${d.reason})` : ""}.`
        : `Reclassified → ${d.category ?? "—"} at ${d.confidence ?? "—"}% confidence.`);
      await load();
      onChanged?.();
    } catch (e: unknown) {
      setActionMsg((e as Error).message || "Action failed.");
    } finally {
      setBusy("");
    }
  }

  const s = data?.store;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-3 sm:p-6 overflow-y-auto"
      style={{ background: "rgba(0,0,0,0.6)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-lg my-auto"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-5 py-4" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <a href={`https://${domain}`} target="_blank" rel="noreferrer"
                 className="num text-sm font-bold truncate hover:underline flex items-center gap-1" style={{ color: "var(--text)" }}>
                {domain} <ExternalLink className="w-3 h-3 shrink-0" style={{ color: "var(--muted)" }} />
              </a>
            </div>
            {s?.brand_name && <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{s.brand_name}</p>}
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-white/[0.06] shrink-0" style={{ color: "var(--muted)" }}>
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {loading && <p className="text-xs" style={{ color: "var(--muted)" }}>Loading…</p>}
          {error && <p className="text-xs" style={{ color: "#F2555A" }}>{error}</p>}

          {s && (
            <>
              {/* Status + actions */}
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <span className="flex items-center gap-1.5 text-xs font-semibold px-2 py-1 rounded"
                      style={{ color: STATUS_COLOR[s.status] ?? "var(--muted)", background: "var(--bg3)" }}>
                  {s.status === "verified" ? <Check className="w-3 h-3" /> : s.status === "rejected" || s.status === "failed" ? <AlertTriangle className="w-3 h-3" /> : null}
                  {s.status}
                  {s.verification_confidence != null && s.status === "verified" ? ` · ${s.verification_confidence}%` : ""}
                </span>
                <div className="flex items-center gap-2">
                  <button onClick={() => runAction("reverify")} disabled={!!busy}
                          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md transition-all hover:brightness-110 disabled:opacity-40"
                          style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text-2)" }}>
                    {busy === "reverify" ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                    Re-verify
                  </button>
                  <button onClick={() => runAction("reclassify")} disabled={!!busy || s.status !== "verified"}
                          title={s.status !== "verified" ? "Only verified stores can be classified" : ""}
                          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md transition-all hover:brightness-110 disabled:opacity-40"
                          style={{ background: "var(--accent)", color: "var(--ink)" }}>
                    {busy === "reclassify" ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Brain className="w-3.5 h-3.5" />}
                    Re-run knowledge
                  </button>
                </div>
              </div>
              {actionMsg && <p className="text-xs" style={{ color: "var(--text-2)" }}>{actionMsg}</p>}
              {(s.rejection_reason || s.failure_reason) && s.status !== "verified" && (
                <p className="text-xs px-3 py-2 rounded" style={{ background: "rgba(242,85,90,.08)", color: "#F2555A" }}>
                  Reason: {s.rejection_reason || s.failure_reason}
                </p>
              )}

              {/* Category — the most important part */}
              <div className="rounded-md p-3" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
                <div className="flex items-center justify-between mb-1">
                  <p className="label-caps">Category · why we classified it this way</p>
                  {s.category_confidence != null && (
                    <span className="num text-xs font-bold" style={{ color: s.category_confidence >= 55 ? "#4CC38A" : "var(--accent)" }}>
                      {s.category_confidence}% confidence
                    </span>
                  )}
                </div>
                <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                  {s.category ? `${s.category}${s.subcategory ? ` · ${s.subcategory}` : ""}` : "Not classified yet"}
                </p>
                {(s.category_evidence?.length ?? 0) > 0 ? (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {s.category_evidence!.map((ev, i) => (
                      <span key={i} className="text-[11px] px-2 py-0.5 rounded num" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-2)" }}
                            title={`signal: ${ev.signal} · weight ${ev.weight}`}>
                        {ev.detail} <span style={{ color: "var(--muted)" }}>({ev.signal})</span>
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] mt-1" style={{ color: "var(--muted)" }}>
                    {s.knowledge_at ? "No keyword evidence recorded." : "Knowledge stage hasn't run yet — hit “Re-run knowledge”."}
                  </p>
                )}
              </div>

              {/* Catalog + pricing */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "Products", value: s.product_count ?? "—" },
                  { label: "Collections", value: s.collection_count ?? "—" },
                  { label: "Median price", value: s.median_price != null ? `$${s.median_price}` : "—" },
                  { label: "Promo rate", value: s.promo_rate != null ? `${s.promo_rate}%` : "—" },
                ].map((t) => (
                  <div key={t.label}>
                    <p className="num text-base font-bold" style={{ color: "var(--text)" }}>{t.value}</p>
                    <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--muted)" }}>{t.label}</p>
                  </div>
                ))}
              </div>
              {s.price_bands && (s.price_bands.p25 != null || s.price_bands.p75 != null) && (
                <p className="text-[11px]" style={{ color: "var(--muted)" }}>
                  Price bands — p25 ${s.price_bands.p25 ?? "—"} · p50 ${s.price_bands.p50 ?? "—"} · p75 ${s.price_bands.p75 ?? "—"}
                  {s.pricing_tier ? ` · ${s.pricing_tier}` : ""}{s.business_stage ? ` · ${s.business_stage}` : ""}
                </p>
              )}

              {/* Audience + keywords */}
              {(s.target_customer || (s.brand_keywords?.length ?? 0) > 0) && (
                <div className="space-y-2">
                  {s.target_customer && (
                    <p className="text-xs" style={{ color: "var(--text-2)" }}>
                      <span className="label-caps mr-2">Target customer</span>{s.target_customer}
                    </p>
                  )}
                  {(s.brand_keywords?.length ?? 0) > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {s.brand_keywords!.map((k, i) => (
                        <span key={i} className="text-[11px] px-2 py-0.5 rounded num" style={{ background: "var(--bg3)", color: "var(--text-2)" }}>{k}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Verification signals */}
              {(s.verification_signals?.length ?? 0) > 0 && (
                <div>
                  <p className="label-caps mb-1">Verification signals</p>
                  <ul className="space-y-0.5">
                    {s.verification_signals!.map((sig, i) => (
                      <li key={i} className="text-[11px] flex items-center gap-1.5" style={{ color: "var(--text-2)" }}>
                        <Check className="w-3 h-3 shrink-0" style={{ color: "#4CC38A" }} />{sig}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Provenance + timestamps */}
              <div className="grid sm:grid-cols-3 gap-3 text-[11px]" style={{ color: "var(--muted)" }}>
                <div>
                  <p className="label-caps mb-0.5">Discovered</p>
                  <p style={{ color: "var(--text-2)" }}>{s.discovery_source || s.source || "—"}</p>
                  <p>{fmtDate(s.discovered_at)}</p>
                </div>
                <div>
                  <p className="label-caps mb-0.5">Verified</p>
                  <p>{fmtDate(s.verified_at)}</p>
                </div>
                <div>
                  <p className="label-caps mb-0.5">Knowledge</p>
                  <p>{fmtDate(s.knowledge_at)}</p>
                </div>
              </div>

              {/* Related — graph foundation */}
              <div>
                <p className="label-caps mb-1">Related stores</p>
                {(data?.related.length ?? 0) === 0 ? (
                  <p className="text-[11px]" style={{ color: "var(--muted)" }}>
                    Relationship graph is scaffolded but not populated yet — related stores appear here once edges are built.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {data!.related.map((r) => (
                      <span key={r.domain} className="num text-[11px] px-2 py-0.5 rounded" style={{ background: "var(--bg3)", color: "var(--text-2)" }}>{r.domain}</span>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
