"use client";

import { useEffect, useState } from "react";
import { Swords, TrendingUp, TrendingDown, Minus, Lock, Store, ArrowRight, Loader2, Target } from "lucide-react";
import { competitors as api, myStore as myStoreApi, type ComparisonResponse, type ComparisonDimension } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";
import { SaveToPlaybook } from "@/components/SaveToPlaybook";

// ── verdict styling ──────────────────────────────────────────────────────────

function verdictStyle(v: string): { color: string; bg: string; label: string; Icon: typeof TrendingUp } {
  switch (v) {
    case "winning": return { color: "#4CC38A", bg: "rgba(76,195,138,.12)", label: "Ahead", Icon: TrendingUp };
    case "losing": return { color: "#F2555A", bg: "rgba(242,85,90,.12)", label: "Behind", Icon: TrendingDown };
    case "matched": return { color: "#A8AC9E", bg: "rgba(236,238,230,.08)", label: "Matched", Icon: Minus };
    default: return { color: "#A8AC9E", bg: "rgba(236,238,230,.08)", label: "Strategic", Icon: Target };
  }
}

function DimensionCard({ dim, onUpgrade }: { dim: ComparisonDimension; onUpgrade: () => void }) {
  const { color, bg, label, Icon } = verdictStyle(dim.verdict);
  // Highlight the side that's ahead from the user's POV.
  const youAhead = dim.verdict === "winning";
  const themAhead = dim.verdict === "losing";
  const youStyle = youAhead
    ? { background: "rgba(76,195,138,.08)", border: "1px solid rgba(76,195,138,.35)", valueColor: "#4CC38A" }
    : themAhead
      ? { background: "var(--bg3)", border: "1px solid var(--border)", valueColor: "var(--text-2)" }
      : { background: "var(--bg3)", border: "1px solid var(--border)", valueColor: "var(--text)" };
  const themStyle = themAhead
    ? { background: "rgba(242,85,90,.06)", border: "1px solid rgba(242,85,90,.3)", valueColor: "#F2555A" }
    : { background: "var(--bg3)", border: "1px solid var(--border)", valueColor: "var(--text-2)" };

  return (
    <div className="rounded-md overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: `3px solid ${color}` }}>
      <div className="p-5">
        <div className="flex items-center justify-between gap-3 mb-3.5">
          <h4 className="font-semibold text-sm" style={{ color: "var(--text)" }}>{dim.label}</h4>
          <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-2 py-1 rounded-md shrink-0" style={{ background: bg, color }}>
            <Icon className="w-3 h-3" /> {label}
          </span>
        </div>

        {/* Head-to-head tiles — symmetric, winner highlighted */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-stretch gap-2 mb-3.5">
          <div className="text-center rounded-md py-2.5 px-2" style={{ background: youStyle.background, border: youStyle.border }}>
            <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--muted)" }}>You</p>
            <p className="font-mono font-bold text-base leading-none" style={{ color: youStyle.valueColor }}>{dim.your_value}</p>
          </div>
          <div className="flex items-center justify-center">
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: "var(--bg3)", color: "var(--muted)" }}>VS</span>
          </div>
          <div className="text-center rounded-md py-2.5 px-2" style={{ background: themStyle.background, border: themStyle.border }}>
            <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--muted)" }}>Them</p>
            <p className="font-mono font-bold text-base leading-none" style={{ color: themStyle.valueColor }}>{dim.their_value}</p>
          </div>
        </div>

        <p className="text-[13px] leading-relaxed" style={{ color: "var(--text-2)" }}>{dim.insight}</p>
      </div>

      {/* Action — gated; sits in a footer band so the "what to do" reads as the payoff */}
      {dim.action_locked ? (
        <button
          onClick={onUpgrade}
          className="w-full flex items-center justify-center gap-2 text-xs font-semibold py-2.5 transition-all hover:brightness-110"
          style={{ background: "rgba(255,178,36,.07)", color: "var(--accent)", borderTop: "1px dashed rgba(255,178,36,.3)" }}
        >
          <Lock className="w-3.5 h-3.5" /> Unlock the move → what to do about this
        </button>
      ) : dim.action ? (
        <div className="flex items-start gap-2 text-[13px] px-5 py-3" style={{ background: "var(--bg3)", borderTop: "1px solid var(--border)" }}>
          <ArrowRight className="w-4 h-4 mt-0.5 shrink-0" style={{ color: color }} />
          <span style={{ color: "var(--text)" }}>{dim.action}</span>
        </div>
      ) : null}
    </div>
  );
}

// ── set-your-store form ──────────────────────────────────────────────────────

function SetStorePrompt({ onSaved }: { onSaved: () => void }) {
  const [url, setUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    if (!url.trim()) return;
    setSaving(true);
    setError("");
    try {
      await myStoreApi.set(url.trim());
      onSaved();
    } catch {
      setError("Could not add that store. Check the URL and try again.");
      setSaving(false);
    }
  }

  return (
    <div className="rounded-md p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <Store className="w-8 h-8 mx-auto mb-3" style={{ color: "var(--text-2)" }} />
      <h3 className="font-semibold mb-1" style={{ color: "var(--text)" }}>Add your store to compare</h3>
      <p className="text-sm mb-5 max-w-md mx-auto" style={{ color: "var(--muted)" }}>
        See exactly where you stand against this competitor — price, catalog, discounting, launch pace,
        and the lanes they leave open for you. Adding your store is free and doesn&apos;t use a tracking slot.
      </p>
      <div className="flex gap-2 max-w-md mx-auto">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && save()}
          placeholder="yourstore.com"
          className="flex-1 px-4 py-2.5 rounded-md text-sm outline-none"
          style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
        />
        <button
          onClick={save}
          disabled={saving}
          className="font-semibold text-sm px-5 py-2.5 rounded-md transition-all hover:brightness-110 disabled:opacity-60"
          style={{ background: "#FFB224", color: "#0B0C0A" }}
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Compare"}
        </button>
      </div>
      {error && <p className="text-xs mt-3" style={{ color: "#F2555A" }}>{error}</p>}
    </div>
  );
}

// ── main component ───────────────────────────────────────────────────────────

export default function ComparisonTab({ competitorId }: { competitorId: string }) {
  const [data, setData] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // setLoading lives in an event handler (refresh button / onSaved), not the
  // effect body, to avoid cascading-render warnings.
  function refresh() {
    setLoading(true);
    setRefreshKey((k) => k + 1);
  }

  useEffect(() => {
    let cancelled = false;
    api.comparison(competitorId)
      .then((r) => { if (!cancelled) setData(r.data); })
      .catch(() => { if (!cancelled) setData(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [competitorId, refreshKey]);

  // Auto-poll while a scan is still producing the comparison — no manual
  // refresh. Stops as soon as it's ready (or the store isn't set).
  useEffect(() => {
    if (!data || !data.has_store || data.ready !== false) return;
    const t = setInterval(() => {
      api.comparison(competitorId).then((r) => setData(r.data)).catch(() => {});
    }, 5000);
    return () => clearInterval(t);
  }, [competitorId, data]);

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-28 rounded-md animate-pulse" style={{ background: "var(--bg-card)" }} />
        {[1, 2, 3].map((i) => <div key={i} className="h-40 rounded-md animate-pulse" style={{ background: "var(--bg-card)" }} />)}
      </div>
    );
  }

  // No store set
  if (data && !data.has_store) {
    return <SetStorePrompt onSaved={refresh} />;
  }

  // Store set but a snapshot isn't ready yet — live progress, auto-updates
  if (data && data.has_store && data.ready === false) {
    const msg = data.reason === "my_store_scanning"
      ? "Scanning your store to build the head-to-head — usually 60–90 seconds."
      : "This competitor is finishing its first scan — the scorecard builds automatically.";
    return (
      <div className="rounded-md p-8 text-center analyzing-sweep" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <Loader2 className="w-6 h-6 mx-auto mb-3 animate-spin" style={{ color: "var(--accent)" }} />
        <p style={{ color: "var(--text-2)" }}>{msg}</p>
        <p className="text-xs mt-1.5" style={{ color: "var(--muted)" }}>This updates on its own — no need to refresh.</p>
      </div>
    );
  }

  if (!data || !data.overall) {
    return (
      <div className="rounded-md p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <p style={{ color: "var(--muted)" }}>Comparison not available yet.</p>
      </div>
    );
  }

  const verdict = data.overall.verdict || "";
  const overallColor = verdict.includes("ahead") ? "#4CC38A"
    : verdict.includes("behind") ? "#F2555A" : "#A8AC9E";

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start gap-2">
        <Swords className="w-5 h-5 mt-0.5" style={{ color: "var(--text-2)" }} />
        <div>
          <h3 className="font-semibold" style={{ color: "var(--text)" }}>
            {data.my_hostname} vs {data.their_hostname}
          </h3>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Where you stand head-to-head, and where the open lanes are.
          </p>
        </div>
      </div>

      {/* Overall verdict — the scoreboard */}
      <div className="rounded-md p-5" style={{ background: "var(--bg-card)", border: `1px solid ${overallColor}40`, borderLeft: `3px solid ${overallColor}` }}>
        <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
          <span className="font-bold text-lg leading-tight" style={{ color: overallColor }}>{verdict}</span>
          <div className="flex items-center gap-1.5 shrink-0">
            {([
              ["Ahead", data.overall.score.winning, "#4CC38A"],
              ["Behind", data.overall.score.losing, "#F2555A"],
              ["Even", data.overall.score.matched, "#A8AC9E"],
            ] as [string, number, string][]).map(([lbl, n, c]) => (
              <div key={lbl} className="text-center rounded-md px-2.5 py-1" style={{ background: `${c}14` }}>
                <p className="num text-sm font-bold leading-none" style={{ color: c }}>{n}</p>
                <p className="text-[9px] uppercase tracking-wider mt-0.5" style={{ color: "var(--muted)" }}>{lbl}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>{data.overall.summary}</p>
      </div>

      {/* Match strategy */}
      {data.match_strategy && (
        <div className="rounded-md p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4" style={{ color: "var(--text-2)" }} />
            <h4 className="font-semibold text-sm" style={{ color: "var(--text)" }}>
              {data.match_strategy.is_newcomer ? "Your game plan as the challenger" : "Your game plan"}
            </h4>
          </div>
          {data.match_strategy.locked ? (
            <div>
              <p className="text-sm mb-3" style={{ color: "var(--muted)" }}>
                The exact lanes to match and the ones to own are part of your strategic playbook.
              </p>
              <button
                onClick={() => setUpgradeOpen(true)}
                className="flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg transition-all hover:brightness-110"
                style={{ background: "#FFB224", color: "#0B0C0A" }}
              >
                <Lock className="w-3.5 h-3.5" /> Unlock your game plan
              </button>
            </div>
          ) : (
            <>
              <p className="text-sm leading-relaxed mb-3" style={{ color: "var(--text)" }}>{data.match_strategy.narrative}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {data.match_strategy.match_these.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide mb-1.5" style={{ color: "var(--text-2)" }}>Match them on</p>
                    <ul className="space-y-1">
                      {data.match_strategy.match_these.map((m) => (
                        <li key={m} className="text-sm capitalize" style={{ color: "var(--muted)" }}>· {m}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.match_strategy.own_these.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide mb-1.5" style={{ color: "#4CC38A" }}>Own your lane in</p>
                    <ul className="space-y-1">
                      {data.match_strategy.own_these.map((m) => (
                        <li key={m} className="text-sm capitalize" style={{ color: "var(--muted)" }}>· {m}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Dimensions */}
      {data.dimensions?.map((d) => (
        <DimensionCard key={d.key} dim={d} onUpgrade={() => setUpgradeOpen(true)} />
      ))}

      {/* ── The scorecard's closing argument: protect / attack ───────────── */}
      {(() => {
        const dims = data.dimensions ?? [];
        const protect = dims.find((d) => d.verdict === "winning");
        const attack = dims.find((d) => d.verdict === "losing");
        if (!protect && !attack) return null;
        const interpretation = [
          protect && `Your clearest edge is ${protect.label.toLowerCase()} (${protect.your_value} vs ${protect.their_value}) — that's the position to defend before chasing anything new.`,
          attack && `The fight worth picking is ${attack.label.toLowerCase()} (${attack.your_value} vs ${attack.their_value}) — it's the gap they'd least expect you to close.`,
        ].filter(Boolean).join(" ");
        const move = attack?.action || protect?.action || null;
        return (
          <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: "3px solid var(--accent)" }}>
            <p className="label-caps mb-1.5" style={{ color: "var(--accent)" }}>StoreScout interpretation</p>
            <p className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>{interpretation}</p>
            {move && (
              <div className="flex items-start justify-between gap-3 mt-2.5">
                <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>→ {move}</p>
                <SaveToPlaybook
                  size="xs"
                  item={{
                    source_type: "pricing",
                    source_ref: `${competitorId}:compare`,
                    competitor_id: competitorId,
                    hostname: data.their_hostname,
                    title: move,
                    reason: interpretation,
                    evidence: `Scorecard: ${data.overall.score.winning}W · ${data.overall.score.losing}L · ${data.overall.score.matched}M vs ${data.their_hostname}`,
                    priority: "medium",
                  }}
                />
              </div>
            )}
          </div>
        );
      })()}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
