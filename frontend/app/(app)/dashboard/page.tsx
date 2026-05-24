"use client";

import { useEffect, useState, useCallback } from "react";
import { Plus, RefreshCw, TrendingUp, Bell, Sparkles, ArrowRight, Activity } from "lucide-react";
import Link from "next/link";
import { competitors as api, alerts as alertsApi, type Competitor, type AlertEvent, type DiscoverySuggestion } from "@/lib/api";
import { cn, formatRelativeTime, formatPrice, formatDelta, changeTypeIcon, severityColor } from "@/lib/utils";
import { AddCompetitorModal } from "@/components/competitors/AddCompetitorModal";
import UpgradeModal from "@/components/UpgradeModal";

// ── Per-competitor change counts (computed from loaded alerts) ────────────

function computeDeltas(alertList: AlertEvent[], competitorId: string) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const recent = alertList.filter(
    (a) => a.competitor_id === competitorId && new Date(a.detected_at).getTime() > weekAgo
  );
  return {
    priceDrops: recent.filter((a) => a.change_type === "price_change" && (a.delta_pct ?? 0) < 0).length,
    newProducts: recent.filter((a) => a.change_type === "new_product").length,
    criticals: recent.filter((a) => a.severity === "critical").length,
    total: recent.length,
  };
}

// ── Scan status ───────────────────────────────────────────────────────────

function ScanDot({ status }: { status: Competitor["scan_status"] }) {
  const cfg = {
    scanning: { color: "var(--accent)", pulse: true, label: "Scanning" },
    done:     { color: "var(--emerald)", pulse: false, label: "Up to date" },
    pending:  { color: "var(--muted)",   pulse: false, label: "Scheduled" },
    error:    { color: "var(--red)",     pulse: false, label: "Error" },
  }[status] ?? { color: "var(--muted)", pulse: false, label: "Unknown" };

  return (
    <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: cfg.color }}>
      <span
        className={cn("w-1.5 h-1.5 rounded-full shrink-0", cfg.pulse && "animate-pulse")}
        style={{ background: cfg.color }}
      />
      {cfg.label}
    </span>
  );
}

// ── Competitor card ───────────────────────────────────────────────────────

function CompetitorCard({ competitor, alertList }: { competitor: Competitor; alertList: AlertEvent[] }) {
  const [rescanning, setRescanning] = useState(false);
  const deltas = computeDeltas(alertList, competitor.id);
  const isScanning = competitor.scan_status === "scanning";

  async function handleRescan(e: React.MouseEvent) {
    e.preventDefault();
    setRescanning(true);
    await api.rescan(competitor.id).catch(() => {});
    setTimeout(() => setRescanning(false), 3000);
  }

  return (
    <Link
      href={`/dashboard/${competitor.id}`}
      className={cn(
        "block rounded-2xl border p-5 transition-all group card-lift fade-up",
        isScanning && "scan-shimmer"
      )}
      style={{ background: "var(--bg3)", borderColor: "var(--border)" }}
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-3 mb-5">
        <div className="min-w-0">
          <h3 className="font-bold text-base leading-tight truncate" style={{ color: "var(--text)" }}>
            {competitor.display_name || competitor.hostname}
          </h3>
          {competitor.display_name && (
            <p className="text-xs mt-0.5 truncate" style={{ color: "var(--muted)" }}>
              {competitor.hostname}
            </p>
          )}
        </div>
        <ScanDot status={competitor.scan_status} />
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="rounded-xl px-3 py-2.5" style={{ background: "var(--bg4)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-semibold uppercase tracking-wide mb-1" style={{ color: "var(--muted)" }}>Products</p>
          <p className="text-lg font-bold font-mono" style={{ color: "var(--text)" }}>
            {competitor.product_count?.toLocaleString() ?? "—"}
          </p>
        </div>
        <div className="rounded-xl px-3 py-2.5" style={{ background: "var(--bg4)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-semibold uppercase tracking-wide mb-1" style={{ color: "var(--muted)" }}>Last scan</p>
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
            {competitor.last_scanned_at ? formatRelativeTime(competitor.last_scanned_at) : "Pending"}
          </p>
        </div>
      </div>

      {/* Delta badges — this week's activity */}
      <div className="flex items-center gap-2 flex-wrap min-h-[24px]">
        {deltas.priceDrops > 0 && (
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "rgba(96,165,250,.12)", color: "var(--blue)" }}>
            ↓ {deltas.priceDrops} price drop{deltas.priceDrops !== 1 ? "s" : ""}
          </span>
        )}
        {deltas.newProducts > 0 && (
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "rgba(168,255,0,.1)", color: "var(--accent)" }}>
            + {deltas.newProducts} new
          </span>
        )}
        {deltas.criticals > 0 && (
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "rgba(239,68,68,.1)", color: "var(--red)" }}>
            ⚠ {deltas.criticals} critical
          </span>
        )}
        {deltas.total === 0 && competitor.scan_status === "done" && (
          <span className="text-[11px]" style={{ color: "var(--muted)" }}>No changes this week</span>
        )}

        {/* Rescan button — visible on hover */}
        <button
          onClick={handleRescan}
          className="ml-auto flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-all opacity-0 group-hover:opacity-100 hover:bg-white/10"
          style={{ color: "var(--muted)" }}
        >
          <RefreshCw className={cn("w-3 h-3", (rescanning || isScanning) && "animate-spin")} />
          Rescan
        </button>
      </div>
    </Link>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] text-center px-6 fade-in">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6"
        style={{ background: "rgba(168,255,0,.08)", border: "1px solid rgba(168,255,0,.18)" }}
      >
        <TrendingUp className="w-8 h-8" style={{ color: "var(--accent)" }} />
      </div>
      <h2 className="text-2xl font-bold mb-3" style={{ color: "var(--text)" }}>
        Track your first competitor
      </h2>
      <p className="text-sm mb-8 max-w-xs leading-relaxed" style={{ color: "var(--muted)" }}>
        Enter any Shopify store URL and we&apos;ll start monitoring their prices, new launches, and discount campaigns automatically.
      </p>
      <button
        onClick={onAdd}
        className="flex items-center gap-2 font-bold px-6 py-3 rounded-xl transition-all hover:brightness-110"
        style={{ background: "var(--accent)", color: "#0a0a0f" }}
      >
        <Plus className="w-4 h-4" />
        Add competitor
      </button>
    </div>
  );
}

// ── Live summary strip ────────────────────────────────────────────────────

function SummaryStrip({ alertList }: { alertList: AlertEvent[] }) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const recent = alertList.filter((a) => new Date(a.detected_at).getTime() > weekAgo);
  if (recent.length === 0) return null;

  const priceDrops  = recent.filter((a) => a.change_type === "price_change" && (a.delta_pct ?? 0) < 0).length;
  const newProducts = recent.filter((a) => a.change_type === "new_product").length;
  const criticals   = recent.filter((a) => a.severity === "critical").length;

  return (
    <div
      className="flex items-center gap-3 flex-wrap rounded-xl px-4 py-3 mb-6 fade-up"
      style={{ background: "rgba(168,255,0,.05)", border: "1px solid rgba(168,255,0,.14)" }}
    >
      {/* Live pulse */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "var(--accent)" }} />
        <span className="text-xs font-bold" style={{ color: "var(--accent)" }}>
          {recent.length} change{recent.length !== 1 ? "s" : ""} this week
        </span>
      </div>
      <span className="hidden sm:block w-px h-4" style={{ background: "rgba(168,255,0,.2)" }} />
      <div className="flex flex-wrap gap-2">
        {priceDrops > 0 && (
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full" style={{ background: "rgba(96,165,250,.1)", color: "var(--blue)" }}>
            ↓ {priceDrops} price drop{priceDrops !== 1 ? "s" : ""}
          </span>
        )}
        {newProducts > 0 && (
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full" style={{ background: "rgba(168,255,0,.1)", color: "var(--accent)" }}>
            + {newProducts} new product{newProducts !== 1 ? "s" : ""}
          </span>
        )}
        {criticals > 0 && (
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full" style={{ background: "rgba(239,68,68,.1)", color: "var(--red)" }}>
            ⚠ {criticals} critical
          </span>
        )}
      </div>
      <Link href="/alerts" className="ml-auto text-xs font-medium flex items-center gap-1 hover:opacity-80 transition-opacity shrink-0" style={{ color: "var(--accent)" }}>
        See all <ArrowRight className="w-3 h-3" />
      </Link>
    </div>
  );
}

// ── Activity feed (right column) ──────────────────────────────────────────

function ActivityFeed({ alertList, alertsLoading }: { alertList: AlertEvent[]; alertsLoading: boolean }) {
  if (alertsLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
        ))}
      </div>
    );
  }

  if (alertList.length === 0) {
    return (
      <div className="rounded-2xl p-6 text-center" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
        <Bell className="w-7 h-7 mx-auto mb-3" style={{ color: "var(--muted)", opacity: 0.4 }} />
        <p className="text-sm font-medium" style={{ color: "var(--muted)" }}>No changes yet</p>
        <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--muted)" }}>
          Activity appears here when competitors change prices, launch products, or run discounts.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {alertList.map((alert, i) => {
        const icon = changeTypeIcon(alert.change_type);
        const old_v = alert.old_value || {};
        const new_v = alert.new_value || {};

        let detail = "";
        if (alert.change_type === "price_change" && alert.delta_pct != null) {
          detail = `${formatPrice(old_v.price as number)} → ${formatPrice(new_v.price as number)} (${formatDelta(alert.delta_pct)})`;
        } else if (alert.change_type === "new_product" && new_v.price_min) {
          detail = `$${new_v.price_min}`;
        } else if (alert.change_type === "discount_start" || alert.change_type === "discount_end") {
          detail = `${formatDelta(alert.delta_pct || 0)} catalog promo`;
        }

        const severityDot = { critical: "var(--red)", warning: "var(--amber)", info: "var(--muted)" }[alert.severity] || "var(--muted)";

        return (
          <Link
            key={alert.id}
            href={`/dashboard/${alert.competitor_id}`}
            className={cn("flex items-start gap-3 rounded-xl p-3 transition-colors hover:bg-white/[0.03]", `fade-up-${Math.min(i + 1, 5)}`)}
            style={{ border: "1px solid var(--border)", background: "var(--bg3)" }}
          >
            <span className="text-sm leading-none mt-0.5 shrink-0">{icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 mb-0.5">
                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: severityDot }} />
                <span className="text-xs font-semibold truncate" style={{ color: "var(--text-2)" }}>
                  {alert.hostname}
                </span>
              </div>
              <p className="text-xs truncate" style={{ color: "var(--muted)" }}>
                {alert.product_title || alert.change_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </p>
              {detail && (
                <p className="text-xs font-mono mt-0.5" style={{ color: "var(--blue)" }}>{detail}</p>
              )}
            </div>
            <p className="text-[11px] shrink-0" style={{ color: "var(--muted)" }}>
              {formatRelativeTime(alert.detected_at)}
            </p>
          </Link>
        );
      })}
    </div>
  );
}

// ── Discovery suggestions ─────────────────────────────────────────────────

function DiscoverySuggestions({
  suggestions, onTrack, tracking,
}: {
  suggestions: DiscoverySuggestion[];
  onTrack: (hostname: string) => Promise<void>;
  tracking: string | null;
}) {
  if (suggestions.length === 0) return null;

  return (
    <div className="mt-10">
      <div className="flex items-center gap-2.5 mb-4">
        <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <p className="text-sm font-bold" style={{ color: "var(--text)" }}>Stores you might want to track</p>
        <span
          className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full"
          style={{ background: "rgba(168,255,0,.1)", color: "var(--accent)" }}
        >
          Based on your competitors
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {suggestions.map((s, i) => (
          <div
            key={s.competitor_id}
            className={cn("rounded-2xl p-4 flex flex-col gap-3 card-lift", `fade-up-${Math.min(i + 1, 5)}`)}
            style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-bold truncate" style={{ color: "var(--text)" }}>{s.hostname}</p>
                {s.market_position && (
                  <p className="text-xs mt-0.5 capitalize" style={{ color: "var(--muted)" }}>{s.market_position}</p>
                )}
              </div>
              {s.median_price != null && (
                <span className="text-xs font-mono shrink-0" style={{ color: "var(--muted)" }}>
                  ~{formatPrice(s.median_price)}
                </span>
              )}
            </div>

            {s.match_reasons.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {s.match_reasons.map((r) => (
                  <span
                    key={r}
                    className="text-[11px] px-2 py-0.5 rounded-full"
                    style={{ background: "rgba(168,255,0,.08)", color: "var(--accent)", border: "1px solid rgba(168,255,0,.14)" }}
                  >
                    {r}
                  </span>
                ))}
              </div>
            )}

            <div className="flex items-center justify-between mt-auto pt-1">
              {s.product_count != null && (
                <span className="text-xs" style={{ color: "var(--muted)" }}>
                  {s.product_count.toLocaleString()} products
                </span>
              )}
              <button
                onClick={() => onTrack(s.hostname)}
                disabled={tracking === s.hostname}
                className="ml-auto flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg transition-all hover:brightness-110 disabled:opacity-50"
                style={{ background: "var(--accent)", color: "#0a0a0f" }}
              >
                {tracking === s.hostname ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : (
                  <Plus className="w-3 h-3" />
                )}
                Track
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [competitorList, setCompetitorList] = useState<Competitor[]>([]);
  const [alertList, setAlertList] = useState<AlertEvent[]>([]);
  const [suggestions, setSuggestions] = useState<DiscoverySuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [trackingHostname, setTrackingHostname] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.list();
      setCompetitorList(data);
    } catch {}
    finally { setLoading(false); }
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      const { data } = await alertsApi.list(50);
      setAlertList(data);
    } catch {}
    finally { setAlertsLoading(false); }
  }, []);

  const loadSuggestions = useCallback(async () => {
    try {
      const { data } = await api.discover();
      setSuggestions(data.suggestions || []);
    } catch {}
  }, []);

  useEffect(() => {
    load();
    loadAlerts();
    const ci = setInterval(load, 10000);
    const ai = setInterval(loadAlerts, 30000);
    return () => { clearInterval(ci); clearInterval(ai); };
  }, [load, loadAlerts]);

  useEffect(() => {
    if (!loading && competitorList.length > 0) loadSuggestions();
  }, [loading, competitorList.length, loadSuggestions]);

  function handleAdded(competitor: Competitor) {
    setCompetitorList((prev) => [competitor, ...prev]);
    setSuggestions((prev) => prev.filter((s) => s.hostname !== competitor.hostname));
    setShowModal(false);
    loadSuggestions();
  }

  async function handleTrack(hostname: string) {
    setTrackingHostname(hostname);
    try {
      const { data: newComp } = await api.add(`https://${hostname}`);
      setCompetitorList((prev) => [newComp, ...prev]);
      setSuggestions((prev) => prev.filter((s) => s.hostname !== hostname));
      loadSuggestions();
    } catch (err: unknown) {
      const e = err as { status?: number };
      if (e?.status === 403) setUpgradeOpen(true);
    } finally {
      setTrackingHostname(null);
    }
  }

  // ── Skeleton ──
  if (loading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-8">
          <div className="space-y-2">
            <div className="h-7 w-36 rounded-lg animate-pulse" style={{ background: "var(--bg3)" }} />
            <div className="h-4 w-24 rounded-lg animate-pulse" style={{ background: "var(--bg3)" }} />
          </div>
          <div className="h-9 w-32 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-2xl animate-pulse" style={{ background: "var(--bg3)" }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Dashboard</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--muted)" }}>
            {competitorList.length === 0
              ? "No competitors tracked yet"
              : `${competitorList.length} store${competitorList.length !== 1 ? "s" : ""} tracked`}
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 font-bold text-sm px-4 py-2.5 rounded-xl transition-all hover:brightness-110"
          style={{ background: "var(--accent)", color: "#0a0a0f" }}
        >
          <Plus className="w-4 h-4" />
          Add competitor
        </button>
      </div>

      {/* Summary strip */}
      {!alertsLoading && <SummaryStrip alertList={alertList} />}

      {competitorList.length === 0 ? (
        <EmptyState onAdd={() => setShowModal(true)} />
      ) : (
        <div className="flex gap-6 items-start">
          {/* Competitor grid */}
          <div className="flex-1 min-w-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {competitorList.map((c) => (
                <CompetitorCard key={c.id} competitor={c} alertList={alertList} />
              ))}
            </div>

            <DiscoverySuggestions
              suggestions={suggestions}
              onTrack={handleTrack}
              tracking={trackingHostname}
            />
          </div>

          {/* Activity feed — right column on desktop */}
          <div className="hidden lg:block w-72 shrink-0">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4" style={{ color: "var(--muted)" }} />
                <p className="text-sm font-bold" style={{ color: "var(--text)" }}>Recent Activity</p>
              </div>
              <Link href="/alerts" className="text-xs font-medium flex items-center gap-1 hover:opacity-80" style={{ color: "var(--accent)" }}>
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            <ActivityFeed alertList={alertList} alertsLoading={alertsLoading} />
          </div>
        </div>
      )}

      {/* Activity — mobile (stacked below) */}
      {competitorList.length > 0 && (
        <div className="lg:hidden mt-8">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4" style={{ color: "var(--muted)" }} />
              <p className="text-sm font-bold" style={{ color: "var(--text)" }}>Recent Activity</p>
            </div>
            <Link href="/alerts" className="text-xs font-medium flex items-center gap-1 hover:opacity-80" style={{ color: "var(--accent)" }}>
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <ActivityFeed alertList={alertList} alertsLoading={alertsLoading} />
        </div>
      )}

      {showModal && (
        <AddCompetitorModal onClose={() => setShowModal(false)} onAdded={handleAdded} />
      )}
      {upgradeOpen && (
        <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="competitor_limit" />
      )}
    </div>
  );
}
