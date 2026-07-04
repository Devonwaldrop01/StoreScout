"use client";

import { useEffect, useState } from "react";
import { Swords, TrendingUp, TrendingDown, Minus, Lock, Store, ArrowRight, Loader2, Target } from "lucide-react";
import { competitors as api, myStore as myStoreApi, type ComparisonResponse, type ComparisonDimension } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

// ── verdict styling ──────────────────────────────────────────────────────────

function verdictStyle(v: string): { color: string; bg: string; label: string; Icon: typeof TrendingUp } {
  switch (v) {
    case "winning": return { color: "#FFB224", bg: "rgba(255,178,36,.12)", label: "Ahead", Icon: TrendingUp };
    case "losing": return { color: "#F2555A", bg: "rgba(242,85,90,.12)", label: "Behind", Icon: TrendingDown };
    case "matched": return { color: "var(--amber)", bg: "rgba(255,178,36,.12)", label: "Matched", Icon: Minus };
    default: return { color: "#FFB224", bg: "rgba(255,178,36,.12)", label: "Strategic", Icon: Target };
  }
}

function DimensionCard({ dim, onUpgrade }: { dim: ComparisonDimension; onUpgrade: () => void }) {
  const { color, bg, label, Icon } = verdictStyle(dim.verdict);
  return (
    <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <h4 className="font-semibold text-sm" style={{ color: "var(--text)" }}>{dim.label}</h4>
        <span className="flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-1 rounded-md shrink-0" style={{ background: bg, color }}>
          <Icon className="w-3 h-3" /> {label}
        </span>
      </div>

      <div className="flex items-center gap-3 mb-3 text-sm">
        <div className="flex-1 text-center rounded-lg py-2" style={{ background: "rgba(255,178,36,.06)" }}>
          <p className="text-[10px] uppercase tracking-wide mb-0.5" style={{ color: "var(--muted)" }}>You</p>
          <p className="font-mono font-bold" style={{ color: "#FFB224" }}>{dim.your_value}</p>
        </div>
        <Swords className="w-4 h-4 shrink-0" style={{ color: "var(--muted)" }} />
        <div className="flex-1 text-center rounded-lg py-2" style={{ background: "var(--bg3)" }}>
          <p className="text-[10px] uppercase tracking-wide mb-0.5" style={{ color: "var(--muted)" }}>Them</p>
          <p className="font-mono font-bold" style={{ color: "var(--text)" }}>{dim.their_value}</p>
        </div>
      </div>

      <p className="text-sm leading-relaxed mb-3" style={{ color: "var(--muted)" }}>{dim.insight}</p>

      {/* Action — gated */}
      {dim.action_locked ? (
        <button
          onClick={onUpgrade}
          className="w-full flex items-center justify-center gap-2 text-xs font-medium py-2 rounded-lg transition-all hover:brightness-110"
          style={{ background: "rgba(255,178,36,.08)", color: "#FFB224", border: "1px dashed rgba(255,178,36,.3)" }}
        >
          <Lock className="w-3 h-3" /> Unlock what to do about this
        </button>
      ) : dim.action ? (
        <div className="flex items-start gap-2 text-sm rounded-lg p-3" style={{ background: "rgba(255,178,36,.05)" }}>
          <ArrowRight className="w-4 h-4 mt-0.5 shrink-0" style={{ color: "#FFB224" }} />
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
    <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <Store className="w-8 h-8 mx-auto mb-3" style={{ color: "#FFB224" }} />
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
          className="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none"
          style={{ background: "var(--bg3)", border: "1px solid var(--border)", color: "var(--text)" }}
        />
        <button
          onClick={save}
          disabled={saving}
          className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110 disabled:opacity-60"
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

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-28 rounded-2xl animate-pulse" style={{ background: "var(--bg-card)" }} />
        {[1, 2, 3].map((i) => <div key={i} className="h-40 rounded-2xl animate-pulse" style={{ background: "var(--bg-card)" }} />)}
      </div>
    );
  }

  // No store set
  if (data && !data.has_store) {
    return <SetStorePrompt onSaved={refresh} />;
  }

  // Store set but a snapshot isn't ready yet
  if (data && data.has_store && data.ready === false) {
    const msg = data.reason === "my_store_scanning"
      ? "We're scanning your store now — usually 60–90 seconds. Refresh shortly to see the comparison."
      : "This competitor hasn't finished its first scan yet. Check back in a minute.";
    return (
      <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <Loader2 className="w-6 h-6 mx-auto mb-3 animate-spin" style={{ color: "#FFB224" }} />
        <p style={{ color: "var(--muted)" }}>{msg}</p>
        <button onClick={refresh} className="mt-4 text-sm font-medium px-4 py-2 rounded-lg" style={{ background: "var(--bg3)", color: "var(--text)" }}>
          Refresh
        </button>
      </div>
    );
  }

  if (!data || !data.overall) {
    return (
      <div className="rounded-2xl p-8 text-center" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
        <p style={{ color: "var(--muted)" }}>Comparison not available yet.</p>
      </div>
    );
  }

  const verdict = data.overall.verdict || "";
  const overallColor = verdict.includes("ahead") ? "#FFB224"
    : verdict.includes("behind") ? "#F2555A" : "var(--amber)";

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start gap-2">
        <Swords className="w-5 h-5 mt-0.5" style={{ color: "#FFB224" }} />
        <div>
          <h3 className="font-semibold" style={{ color: "var(--text)" }}>
            {data.my_hostname} vs {data.their_hostname}
          </h3>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Where you stand head-to-head, and where the open lanes are.
          </p>
        </div>
      </div>

      {/* Overall verdict */}
      <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: `1px solid ${overallColor}40` }}>
        <div className="flex items-center justify-between mb-2">
          <span className="font-bold text-lg" style={{ color: overallColor }}>{verdict}</span>
          <div className="flex gap-3 text-xs font-mono">
            <span style={{ color: "#FFB224" }}>{data.overall.score.winning}W</span>
            <span style={{ color: "#F2555A" }}>{data.overall.score.losing}L</span>
            <span style={{ color: "var(--amber)" }}>{data.overall.score.matched}M</span>
          </div>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{data.overall.summary}</p>
      </div>

      {/* Match strategy */}
      {data.match_strategy && (
        <div className="rounded-2xl p-5" style={{ background: "rgba(255,178,36,.05)", border: "1px solid rgba(255,178,36,.2)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4" style={{ color: "#FFB224" }} />
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
                    <p className="text-xs font-semibold uppercase tracking-wide mb-1.5" style={{ color: "var(--amber)" }}>Match them on</p>
                    <ul className="space-y-1">
                      {data.match_strategy.match_these.map((m) => (
                        <li key={m} className="text-sm capitalize" style={{ color: "var(--muted)" }}>· {m}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {data.match_strategy.own_these.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide mb-1.5" style={{ color: "#FFB224" }}>Own your lane in</p>
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

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
