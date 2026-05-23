"use client";

import { useEffect, useState, useCallback } from "react";
import { Plus, RefreshCw, TrendingUp, Bell, Sparkles } from "lucide-react";
import Link from "next/link";
import { competitors as api, alerts as alertsApi, type Competitor, type AlertEvent, type DiscoverySuggestion } from "@/lib/api";
import { cn, formatRelativeTime, formatPrice, formatDelta, changeTypeIcon, severityColor } from "@/lib/utils";
import { AddCompetitorModal } from "@/components/competitors/AddCompetitorModal";
import UpgradeModal from "@/components/UpgradeModal";

// ── Severity helpers ──────────────────────────────────────────────────────────

function severityBorder(severity: string): string {
  return (
    { critical: "rgba(248,113,113,.35)", warning: "rgba(250,204,21,.35)", info: "var(--border)" }[severity]
    || "var(--border)"
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ScanStatusDot({ status }: { status: Competitor["scan_status"] }) {
  const configs = {
    scanning: { color: "#a3f000", pulse: true, label: "Scanning…" },
    done: { color: "#22d3ee", pulse: false, label: "Up to date" },
    pending: { color: "#7d92aa", pulse: false, label: "Scheduled" },
    error: { color: "#f87171", pulse: false, label: "Error" },
  };
  const c = configs[status] || configs.pending;
  return (
    <span className="flex items-center gap-1.5 text-xs" style={{ color: c.color }}>
      <span className={cn("w-2 h-2 rounded-full inline-block", c.pulse && "animate-pulse")} style={{ background: c.color }} />
      {c.label}
    </span>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl px-3 py-2 text-center" style={{ background: "rgba(255,255,255,.04)", border: "1px solid var(--border)" }}>
      <p className="text-xs mb-0.5" style={{ color: "var(--muted)" }}>{label}</p>
      <p className="text-sm font-semibold font-mono" style={{ color: "var(--text)" }}>{value}</p>
    </div>
  );
}

function CompetitorCard({ competitor }: { competitor: Competitor }) {
  const [rescanning, setRescanning] = useState(false);

  async function handleRescan(e: React.MouseEvent) {
    e.preventDefault();
    setRescanning(true);
    await api.rescan(competitor.id).catch(() => {});
    setTimeout(() => setRescanning(false), 3000);
  }

  const isActive = competitor.scan_status === "scanning";

  return (
    <Link
      href={`/dashboard/${competitor.id}`}
      className="block rounded-2xl border p-5 transition-all hover:border-white/20 hover:-translate-y-0.5 group"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-base" style={{ color: "var(--text)" }}>
            {competitor.display_name || competitor.hostname}
          </h3>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{competitor.hostname}</p>
        </div>
        <ScanStatusDot status={competitor.scan_status} />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <MetricPill label="Products" value={competitor.product_count?.toLocaleString() ?? "—"} />
        <MetricPill label="Last scan" value={competitor.last_scanned_at ? formatRelativeTime(competitor.last_scanned_at) : "—"} />
        <MetricPill label="Status" value={competitor.is_active ? "Active" : "Paused"} />
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs" style={{ color: "var(--muted)" }}>Added {formatRelativeTime(competitor.created_at)}</span>
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={handleRescan}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-colors hover:bg-white/10"
            style={{ color: "var(--muted)" }}
          >
            <RefreshCw className={cn("w-3 h-3", (rescanning || isActive) && "animate-spin")} />
            Rescan
          </button>
        </div>
      </div>
    </Link>
  );
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] text-center px-6">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6" style={{ background: "rgba(163,240,0,.1)", border: "1px solid rgba(163,240,0,.2)" }}>
        <TrendingUp className="w-8 h-8" style={{ color: "var(--green)" }} />
      </div>
      <h2 className="text-2xl font-bold mb-3" style={{ color: "var(--text)" }}>Add your first competitor</h2>
      <p className="text-base mb-8 max-w-sm" style={{ color: "var(--muted)" }}>
        Enter any Shopify store URL and we&apos;ll start monitoring their prices, launches, and discounts automatically.
      </p>
      <button
        onClick={onAdd}
        className="flex items-center gap-2 font-semibold px-6 py-3 rounded-xl transition-all hover:brightness-110"
        style={{ background: "var(--green)", color: "#060d18" }}
      >
        <Plus className="w-4 h-4" />
        Add competitor
      </button>
    </div>
  );
}

function ActivityFeed({ alertList, alertsLoading }: { alertList: AlertEvent[]; alertsLoading: boolean }) {
  if (alertsLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 rounded-xl animate-pulse" style={{ background: "var(--bg-card)" }} />
        ))}
      </div>
    );
  }

  if (alertList.length === 0) {
    return (
      <div
        className="rounded-2xl p-6 text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <Bell className="w-7 h-7 mx-auto mb-3 opacity-30" style={{ color: "var(--muted)" }} />
        <p className="text-sm font-medium" style={{ color: "var(--muted)" }}>No changes yet</p>
        <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
          Activity appears here when competitors change prices, launch products, or run discounts.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {alertList.map((alert) => {
        const icon = changeTypeIcon(alert.change_type);
        const colorClass = severityColor(alert.severity);
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

        return (
          <Link
            key={alert.id}
            href={`/dashboard/${alert.competitor_id}`}
            className="flex items-start gap-3 rounded-xl p-3 transition-colors hover:bg-white/5"
            style={{ border: `1px solid ${severityBorder(alert.severity)}`, background: "var(--bg-card)" }}
          >
            <span className="text-base leading-none mt-0.5 shrink-0">{icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 mb-0.5">
                <span className="text-xs font-semibold truncate" style={{ color: "var(--muted)" }}>
                  {alert.hostname}
                </span>
                {alert.severity !== "info" && (
                  <span className={cn("text-[10px] font-bold uppercase shrink-0", colorClass)}>
                    {alert.severity}
                  </span>
                )}
              </div>
              <p className="text-xs font-medium truncate" style={{ color: "var(--text)" }}>
                {alert.product_title || alert.change_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </p>
              {detail && <p className={cn("text-xs font-mono mt-0.5", colorClass)}>{detail}</p>}
            </div>
            <p className="text-xs shrink-0" style={{ color: "var(--muted)" }}>
              {formatRelativeTime(alert.detected_at)}
            </p>
          </Link>
        );
      })}
    </div>
  );
}

function SummaryStrip({ alertList }: { alertList: AlertEvent[] }) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const recent = alertList.filter((a) => new Date(a.detected_at).getTime() > weekAgo);
  if (recent.length === 0) return null;

  const priceDrops = recent.filter((a) => a.change_type === "price_change" && (a.delta_pct ?? 0) < 0).length;
  const newProducts = recent.filter((a) => a.change_type === "new_product").length;
  const criticals = recent.filter((a) => a.severity === "critical").length;

  const chips: { label: string; color: string; bg: string }[] = [];
  if (priceDrops > 0) chips.push({ label: `↓ ${priceDrops} price drop${priceDrops !== 1 ? "s" : ""}`, color: "#60a5fa", bg: "rgba(96,165,250,.1)" });
  if (newProducts > 0) chips.push({ label: `+ ${newProducts} new product${newProducts !== 1 ? "s" : ""}`, color: "#a3f000", bg: "rgba(163,240,0,.1)" });
  if (criticals > 0) chips.push({ label: `⚠ ${criticals} critical`, color: "#f87171", bg: "rgba(248,113,113,.1)" });

  return (
    <div
      className="flex items-center gap-3 flex-wrap rounded-2xl px-4 py-3 mb-6"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
        {recent.length} change{recent.length !== 1 ? "s" : ""} this week
      </span>
      <span className="w-px h-4 hidden sm:block" style={{ background: "var(--border)" }} />
      <div className="flex flex-wrap gap-2">
        {chips.map((chip) => (
          <span
            key={chip.label}
            className="text-xs font-medium px-2.5 py-1 rounded-full"
            style={{ background: chip.bg, color: chip.color }}
          >
            {chip.label}
          </span>
        ))}
      </div>
      <Link href="/alerts" className="ml-auto text-xs hover:underline shrink-0" style={{ color: "var(--muted)" }}>
        See all →
      </Link>
    </div>
  );
}

// ── Competitor Discovery ──────────────────────────────────────────────────────

function DiscoverySuggestions({
  suggestions,
  onTrack,
  tracking,
}: {
  suggestions: DiscoverySuggestion[];
  onTrack: (hostname: string) => Promise<void>;
  tracking: string | null;
}) {
  if (suggestions.length === 0) return null;

  return (
    <div className="mt-8">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-4 h-4" style={{ color: "var(--green)" }} />
        <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Stores you might want to track</p>
        <span
          className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
          style={{ background: "rgba(163,240,0,.12)", color: "var(--green)" }}
        >
          Based on your competitors
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {suggestions.map((s) => (
          <div
            key={s.competitor_id}
            className="rounded-2xl p-4 flex flex-col gap-3"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-semibold truncate" style={{ color: "var(--text)" }}>{s.hostname}</p>
                {s.market_position && (
                  <p className="text-xs mt-0.5 capitalize" style={{ color: "var(--muted)" }}>{s.market_position}</p>
                )}
              </div>
              {s.median_price != null && (
                <span className="text-xs font-mono shrink-0" style={{ color: "var(--muted)" }}>
                  ~{formatPrice(s.median_price)} med.
                </span>
              )}
            </div>

            {/* Match reason tags */}
            {s.match_reasons.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {s.match_reasons.map((r) => (
                  <span
                    key={r}
                    className="text-[11px] px-2 py-0.5 rounded-full"
                    style={{ background: "rgba(163,240,0,.08)", color: "var(--green)", border: "1px solid rgba(163,240,0,.15)" }}
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
                className="ml-auto flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all hover:brightness-110 disabled:opacity-50"
                style={{ background: "var(--green)", color: "#060d18" }}
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

// ── Page ──────────────────────────────────────────────────────────────────────

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
      const { data } = await alertsApi.list(30);
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
    const competitorInterval = setInterval(load, 10000);
    const alertsInterval = setInterval(loadAlerts, 30000);
    return () => { clearInterval(competitorInterval); clearInterval(alertsInterval); };
  }, [load, loadAlerts]);

  useEffect(() => {
    if (!loading && competitorList.length > 0) {
      loadSuggestions();
    }
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
      if (e?.status === 403) {
        setUpgradeOpen(true);
      }
    } finally {
      setTrackingHostname(null);
    }
  }

  if (loading) {
    return (
      <div>
        <div className="h-8 w-48 rounded-xl mb-2 animate-pulse" style={{ background: "var(--bg-card)" }} />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
          {[1, 2, 3].map((i) => <div key={i} className="h-40 rounded-2xl animate-pulse" style={{ background: "var(--bg-card)" }} />)}
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
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            {competitorList.length} store{competitorList.length !== 1 ? "s" : ""} tracked
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 font-semibold text-sm px-4 py-2.5 rounded-xl transition-all hover:brightness-110"
          style={{ background: "var(--green)", color: "#060d18" }}
        >
          <Plus className="w-4 h-4" />
          Add competitor
        </button>
      </div>

      {/* Summary strip — only when there's activity */}
      {!alertsLoading && <SummaryStrip alertList={alertList} />}

      {competitorList.length === 0 ? (
        <EmptyState onAdd={() => setShowModal(true)} />
      ) : (
        <div className="flex gap-6 items-start">
          {/* Competitor grid */}
          <div className="flex-1 min-w-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {competitorList.map((c) => (
                <CompetitorCard key={c.id} competitor={c} />
              ))}
            </div>
          </div>

          {/* Activity feed — sidebar on desktop */}
          <div className="hidden lg:block w-72 shrink-0">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Recent Activity</p>
              <Link href="/alerts" className="text-xs hover:underline" style={{ color: "var(--muted)" }}>View all</Link>
            </div>
            <ActivityFeed alertList={alertList} alertsLoading={alertsLoading} />
          </div>
        </div>
      )}

      {/* Activity feed — stacked on mobile, below competitors */}
      {competitorList.length > 0 && (
        <div className="lg:hidden mt-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Recent Activity</p>
            <Link href="/alerts" className="text-xs hover:underline" style={{ color: "var(--muted)" }}>View all</Link>
          </div>
          <ActivityFeed alertList={alertList} alertsLoading={alertsLoading} />
        </div>
      )}

      {/* Discovery suggestions — below the main grid */}
      {competitorList.length > 0 && (
        <DiscoverySuggestions
          suggestions={suggestions}
          onTrack={handleTrack}
          tracking={trackingHostname}
        />
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
