"use client";

/**
 * Integrations Hub — the ecosystem, framed as intelligence.
 *
 * Not a list of APIs: an intelligence map (what StoreScout already understands,
 * what the next connection unlocks) + category tabs + value-story cards that
 * answer "what does StoreScout learn, and what gets smarter?". Real connect
 * flows are delegated back to the parent via onConnect; everything else is
 * presented with its value story and a clear state.
 */

import { useEffect, useState } from "react";
import { Check, ChevronDown, Sparkles, Lock } from "lucide-react";
import { integrations as api, type IntegrationHubData, type IntegrationEntry } from "@/lib/api";

const STATUS_META: Record<string, { label: string; color: string }> = {
  connected:   { label: "Connected",  color: "#4CC38A" },
  available:   { label: "Available",  color: "#FFB224" },
  coming_soon: { label: "Coming soon", color: "#6C7164" },
};

const DIM_COLOR: Record<string, string> = {
  competitor: "#FFB224", business: "#4CC38A", marketing: "#7DB8C9",
  customer: "#C08BE0", operational: "#A8AC9E",
};

function IntelligenceMap({ dims }: { dims: IntegrationHubData["intelligence"] }) {
  return (
    <div className="rounded-md p-4 sm:p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>What StoreScout understands</h3>
        <span className="text-[11px]" style={{ color: "var(--muted)" }}>· connect more to fill the map</span>
      </div>
      <div className="space-y-2.5">
        {dims.map((d) => {
          const c = DIM_COLOR[d.key] || "var(--accent)";
          return (
            <div key={d.key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium" style={{ color: "var(--text-2)" }}>{d.label}</span>
                <span className="num text-[11px]" style={{ color: d.pct >= 60 ? c : "var(--muted)" }}>
                  {d.key === "competitor" ? "Full" : `${d.connected}/${d.total}`}
                </span>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--bg3)" }}>
                <div className="h-full rounded-full transition-all" style={{ width: `${d.pct}%`, background: c }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function IntegrationCard({ e, onConnect }: { e: IntegrationEntry; onConnect?: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const meta = STATUS_META[e.status];
  const connectable = e.status === "available" && !!onConnect;

  return (
    <div className="rounded-md overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[.015]">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>{e.name}</span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: `${meta.color}1a`, color: meta.color }}>{meta.label}</span>
          </div>
          <p className="text-[11px] mt-0.5 line-clamp-1" style={{ color: "var(--muted)" }}>{e.gets_better}</p>
        </div>
        <ChevronDown className={`w-4 h-4 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} style={{ color: "var(--muted)" }} />
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="pt-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide mb-1" style={{ color: "var(--text-2)" }}>What StoreScout learns</p>
            <ul className="space-y-0.5">
              {e.learns.map((l, i) => (
                <li key={i} className="text-[13px] flex items-start gap-1.5" style={{ color: "var(--muted)" }}>
                  <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ background: "var(--text-2)" }} />{l}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide mb-1" style={{ color: "#4CC38A" }}>What gets better</p>
            <p className="text-[13px] leading-relaxed" style={{ color: "var(--text-2)" }}>{e.gets_better}</p>
          </div>
          {e.capabilities.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {e.capabilities.map((c, i) => (
                <span key={i} className="text-[11px] px-2 py-0.5 rounded flex items-center gap-1" style={{ background: "var(--bg3)", color: "var(--text-2)" }}>
                  <Check className="w-3 h-3" style={{ color: "#4CC38A" }} /> {c}
                </span>
              ))}
            </div>
          )}
          <div className="pt-1">
            {e.status === "connected" ? (
              <span className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: "#4CC38A" }}><Check className="w-4 h-4" /> Connected & feeding StoreScout</span>
            ) : connectable ? (
              <button onClick={() => onConnect!(e.id)} className="text-xs font-semibold px-4 py-2 rounded-md transition-all hover:brightness-110" style={{ background: "var(--accent)", color: "var(--ink)" }}>
                Connect {e.name}
              </button>
            ) : e.status === "available" ? (
              <span className="text-xs" style={{ color: "var(--muted)" }}>Available — manage below.</span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs" style={{ color: "var(--muted)" }}><Lock className="w-3.5 h-3.5" /> Coming soon — we&apos;ll unlock this intelligence next.</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function IntegrationHub({ onConnect }: { onConnect?: (id: string) => void }) {
  const [hub, setHub] = useState<IntegrationHubData | null>(null);
  const [cat, setCat] = useState("all");

  useEffect(() => { api.hub().then((r) => setHub(r.data)).catch(() => {}); }, []);

  if (!hub) return <div className="h-40 rounded-md animate-pulse" style={{ background: "var(--bg-card)" }} />;

  const shown = cat === "all" ? hub.integrations : hub.integrations.filter((e) => e.category === cat);
  const cats = [{ key: "all", label: "All", count: hub.integrations.length }, ...hub.categories];

  return (
    <div className="space-y-4">
      <IntelligenceMap dims={hub.intelligence} />

      <p className="text-[13px]" style={{ color: "var(--muted)" }}>
        Every integration teaches StoreScout something new — and that knowledge makes every recommendation,
        investigation, and Playbook smarter. <span style={{ color: "var(--text-2)" }}>{hub.connected_count} connected.</span>
      </p>

      {/* Category tabs */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {cats.map((c) => (
          <button key={c.key} onClick={() => setCat(c.key)}
            className="text-xs font-medium px-3 py-1.5 rounded-md transition-all"
            style={{ background: cat === c.key ? "var(--bg3)" : "transparent", border: "1px solid var(--border)", color: cat === c.key ? "var(--text)" : "var(--muted)" }}>
            {c.label} <span style={{ color: "var(--muted)" }}>{c.count}</span>
          </button>
        ))}
      </div>

      <div className="grid sm:grid-cols-2 gap-2.5">
        {shown.map((e) => <IntegrationCard key={e.id} e={e} onConnect={onConnect} />)}
      </div>
    </div>
  );
}
