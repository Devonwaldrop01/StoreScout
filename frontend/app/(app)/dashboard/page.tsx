"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Plus, RefreshCw, TrendingUp, Bell, Sparkles, ArrowRight,
  Activity, Package, Zap, Clock,
} from "lucide-react";
import Link from "next/link";
import { BarChart, Bar, XAxis, ResponsiveContainer, Cell } from "recharts";
import { competitors as api, alerts as alertsApi, type Competitor, type AlertEvent, type DiscoverySuggestion } from "@/lib/api";
import { cn, formatRelativeTime, formatPrice, formatDelta, changeTypeIcon } from "@/lib/utils";
import { AddCompetitorModal } from "@/components/competitors/AddCompetitorModal";
import UpgradeModal from "@/components/UpgradeModal";

// ── Helpers ───────────────────────────────────────────────────────────────

function formatNextScan(dateStr: string | undefined): string {
  if (!dateStr) return "pending";
  const ms = new Date(dateStr).getTime() - Date.now();
  if (ms < 0) return "soon";
  const hours = Math.floor(ms / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d ${hours % 24}h`;
  if (hours > 0) return `${hours}h`;
  return "< 1h";
}

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

// ── Stats bar ─────────────────────────────────────────────────────────────

function StatsBar({
  competitorList, alertList,
}: {
  competitorList: Competitor[];
  alertList: AlertEvent[];
}) {
  const totalProducts = competitorList.reduce((s, c) => s + (c.product_count || 0), 0);
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const changesThisWeek = alertList.filter((a) => new Date(a.detected_at).getTime() > weekAgo).length;
  const criticals = alertList.filter(
    (a) => a.severity === "critical" && new Date(a.detected_at).getTime() > weekAgo
  ).length;

  const nextScanDate = competitorList
    .filter((c) => c.next_scan_at)
    .map((c) => new Date(c.next_scan_at!).getTime())
    .sort((a, b) => a - b)[0];
  const nextScanLabel = nextScanDate ? formatNextScan(new Date(nextScanDate).toISOString()) : null;

  const stats = [
    {
      icon: Package,
      label: "Products tracked",
      value: totalProducts.toLocaleString(),
      color: "var(--blue)",
    },
    {
      icon: Activity,
      label: "Changes this week",
      value: changesThisWeek.toString(),
      color: changesThisWeek > 0 ? "var(--accent)" : "var(--muted)",
      highlight: changesThisWeek > 0,
    },
    {
      icon: Zap,
      label: criticals > 0 ? "Critical alerts" : "All clear",
      value: criticals > 0 ? criticals.toString() : "✓",
      color: criticals > 0 ? "var(--red)" : "var(--emerald)",
    },
    ...(nextScanLabel
      ? [{
          icon: Clock,
          label: "Next scan",
          value: nextScanLabel,
          color: "var(--muted)",
        }]
      : []),
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-7">
      {stats.map(({ icon: Icon, label, value, color, highlight }) => (
        <div
          key={label}
          className="rounded-2xl px-4 py-3.5 flex items-center gap-3"
          style={{
            background: highlight ? "rgba(168,255,0,.05)" : "var(--bg3)",
            border: highlight ? "1px solid rgba(168,255,0,.18)" : "1px solid var(--border)",
          }}
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: `${color}18` }}
          >
            <Icon className="w-4 h-4" style={{ color }} />
          </div>
          <div className="min-w-0">
            <p className="text-lg font-bold font-mono leading-none" style={{ color: "var(--text)" }}>
              {value}
            </p>
            <p className="text-[11px] mt-0.5 truncate" style={{ color: "var(--muted)" }}>{label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Weekly activity mini chart ────────────────────────────────────────────

function WeeklyActivityChart({ alertList }: { alertList: AlertEvent[] }) {
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    const dayLabel = d.toLocaleDateString("en-US", { weekday: "short" });
    const dateStr = d.toDateString();
    const count = alertList.filter(
      (a) => new Date(a.detected_at).toDateString() === dateStr
    ).length;
    return { day: dayLabel, count, isToday: i === 6 };
  });

  const hasActivity = days.some((d) => d.count > 0);

  return (
    <div
      className="rounded-2xl px-4 pt-4 pb-2 mb-4"
      style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>
          7-day change activity
        </p>
        {!hasActivity && (
          <span className="text-[11px]" style={{ color: "var(--muted)" }}>All quiet</span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={52}>
        <BarChart data={days} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="day"
            tick={{ fill: "#5a6a82", fontSize: 9 }}
            axisLine={false}
            tickLine={false}
          />
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {days.map((entry, index) => (
              <Cell
                key={index}
                fill={
                  entry.count === 0
                    ? "rgba(255,255,255,.06)"
                    : entry.isToday
                    ? "#a8ff00"
                    : "rgba(96,165,250,.6)"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Watch list ────────────────────────────────────────────────────────────

function WatchList({ competitorList }: { competitorList: Competitor[] }) {
  return (
    <div
      className="rounded-2xl overflow-hidden mb-4"
      style={{ border: "1px solid var(--border)" }}
    >
      <div
        className="px-4 py-3 flex items-center gap-2"
        style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}
      >
        <span
          className="w-1.5 h-1.5 rounded-full animate-pulse"
          style={{ background: "var(--emerald)" }}
        />
        <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>Watching</p>
      </div>
      <div style={{ background: "var(--bg-card)" }}>
        {competitorList.map((c) => {
          const scanDot = {
            scanning: { color: "var(--accent)", label: "Scanning now" },
            done: { color: "var(--emerald)", label: `Next: ${formatNextScan(c.next_scan_at)}` },
            pending: { color: "var(--muted)", label: "Queued" },
            error: { color: "var(--red)", label: "Error" },
          }[c.scan_status] ?? { color: "var(--muted)", label: "Unknown" };

          return (
            <Link
              key={c.id}
              href={`/dashboard/${c.id}`}
              className="flex items-center justify-between px-4 py-3 border-b hover:bg-white/[0.02] transition-colors last:border-0"
              style={{ borderColor: "var(--border)" }}
            >
              <div className="min-w-0">
                <p className="text-xs font-semibold truncate" style={{ color: "var(--text)" }}>
                  {c.display_name || c.hostname}
                </p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span
                    className={cn("w-1.5 h-1.5 rounded-full shrink-0", c.scan_status === "scanning" && "animate-pulse")}
                    style={{ background: scanDot.color }}
                  />
                  <span className="text-[11px]" style={{ color: "var(--muted)" }}>{scanDot.label}</span>
                </div>
              </div>
              {c.product_count != null && (
                <span className="text-xs font-mono shrink-0 ml-2" style={{ color: "var(--muted)" }}>
                  {c.product_count.toLocaleString()}
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

// ── Spotlight alert ───────────────────────────────────────────────────────

function SpotlightAlert({ alertList }: { alertList: AlertEvent[] }) {
  const dayAgo = Date.now() - 24 * 60 * 60 * 1000;
  const spotlight = alertList
    .filter((a) => new Date(a.detected_at).getTime() > dayAgo)
    .sort((a, b) => {
      const sev = { critical: 3, warning: 2, info: 1 } as Record<string, number>;
      return (sev[b.severity] ?? 0) - (sev[a.severity] ?? 0);
    })[0];

  if (!spotlight || spotlight.severity === "info") return null;

  const old_v = spotlight.old_value || {};
  const new_v = spotlight.new_value || {};
  let detail = "";
  if (spotlight.change_type === "price_change" && spotlight.delta_pct != null) {
    detail = `${formatPrice(old_v.price as number)} → ${formatPrice(new_v.price as number)} (${formatDelta(spotlight.delta_pct)})`;
  }

  const borderColor = spotlight.severity === "critical" ? "rgba(239,68,68,.35)" : "rgba(245,158,11,.35)";
  const bg = spotlight.severity === "critical" ? "rgba(239,68,68,.05)" : "rgba(245,158,11,.05)";
  const accentColor = spotlight.severity === "critical" ? "var(--red)" : "var(--amber)";

  return (
    <Link
      href={`/dashboard/${spotlight.competitor_id}`}
      className="block rounded-2xl p-4 mb-4 transition-all hover:brightness-105"
      style={{ background: bg, border: `1px solid ${borderColor}` }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
          style={{ background: `${accentColor}20`, color: accentColor }}
        >
          {spotlight.severity === "critical" ? "⚡ Critical" : "⚠ Warning"}
        </span>
        <span className="text-[11px] ml-auto" style={{ color: "var(--muted)" }}>
          {formatRelativeTime(spotlight.detected_at)}
        </span>
      </div>
      <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>
        {spotlight.product_title || spotlight.change_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
      </p>
      {detail && (
        <p className="text-xs font-mono mt-1" style={{ color: accentColor }}>{detail}</p>
      )}
      <p className="text-[11px] mt-1.5" style={{ color: "var(--muted)" }}>{spotlight.hostname}</p>
    </Link>
  );
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

  const snapshotData = competitor.snapshot_data as Record<string, unknown> | undefined;
  const pricing = snapshotData?.pricing as Record<string, unknown> | undefined;
  const medianPrice = pricing?.median as number | undefined;
  const promoRate = competitor.promo_rate;

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
      <div className="flex items-start justify-between gap-3 mb-4">
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
      <div className="flex items-center gap-4 mb-3">
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-bold font-mono" style={{ color: "var(--text)" }}>
            {competitor.product_count?.toLocaleString() ?? "—"}
          </span>
          <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>products</span>
        </div>
        {medianPrice != null && (
          <>
            <span className="w-px h-4" style={{ background: "var(--border)" }} />
            <div className="flex items-baseline gap-1">
              <span className="text-sm font-semibold font-mono" style={{ color: "var(--text-2)" }}>
                {formatPrice(medianPrice)}
              </span>
              <span className="text-xs" style={{ color: "var(--muted)" }}>median</span>
            </div>
          </>
        )}
      </div>

      {/* Promo rate bar */}
      {promoRate != null && promoRate > 0 && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold" style={{ color: "var(--amber)" }}>
              {Math.round(promoRate * 100)}% on promo
            </span>
          </div>
          <div className="h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,.06)" }}>
            <div
              className="h-full rounded-full"
              style={{ width: `${Math.round(promoRate * 100)}%`, background: "var(--amber)" }}
            />
          </div>
        </div>
      )}

      {/* Delta badges */}
      <div className="flex items-center gap-2 flex-wrap min-h-[22px] mt-3">
        {deltas.priceDrops > 0 && (
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "rgba(96,165,250,.12)", color: "var(--blue)" }}>
            ↓ {deltas.priceDrops} price drop{deltas.priceDrops !== 1 ? "s" : ""}
          </span>
        )}
        {deltas.newProducts > 0 && (
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full" style={{ background: "rgba(168,255,0,.1)", color: "var(--accent)" }}>
            +{deltas.newProducts} new
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
        <button
          onClick={handleRescan}
          className="ml-auto flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-all opacity-0 group-hover:opacity-100 hover:bg-white/10"
          style={{ color: "var(--muted)" }}
        >
          <RefreshCw className={cn("w-3 h-3", (rescanning || isScanning) && "animate-spin")} />
          Rescan
        </button>
      </div>

      {/* Last scan */}
      <p className="text-[11px] mt-3 pt-3" style={{ color: "var(--muted)", borderTop: "1px solid var(--border)" }}>
        {competitor.last_scanned_at
          ? `Last scanned ${formatRelativeTime(competitor.last_scanned_at)}`
          : "Scan pending"}
      </p>
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

// ── Activity feed ─────────────────────────────────────────────────────────

function ActivityFeed({ alertList, alertsLoading }: { alertList: AlertEvent[]; alertsLoading: boolean }) {
  if (alertsLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
        ))}
      </div>
    );
  }

  if (alertList.length === 0) {
    return (
      <div className="rounded-2xl p-5 text-center" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
        <Bell className="w-6 h-6 mx-auto mb-2" style={{ color: "var(--muted)", opacity: 0.35 }} />
        <p className="text-xs font-medium mb-1" style={{ color: "var(--muted)" }}>No changes yet</p>
        <p className="text-[11px] leading-relaxed" style={{ color: "var(--muted)", opacity: 0.7 }}>
          We&apos;ll alert you here the moment a competitor moves.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {alertList.slice(0, 15).map((alert, i) => {
        const icon = changeTypeIcon(alert.change_type);
        const old_v = alert.old_value || {};
        const new_v = alert.new_value || {};
        let detail = "";
        if (alert.change_type === "price_change" && alert.delta_pct != null) {
          detail = `${formatPrice(old_v.price as number)} → ${formatPrice(new_v.price as number)} (${formatDelta(alert.delta_pct)})`;
        } else if (alert.change_type === "new_product" && new_v.price_min) {
          detail = `$${new_v.price_min}`;
        }
        const severityDot = { critical: "var(--red)", warning: "var(--amber)", info: "var(--muted)" }[alert.severity] ?? "var(--muted)";

        return (
          <Link
            key={alert.id}
            href={`/dashboard/${alert.competitor_id}`}
            className={cn(
              "flex items-start gap-3 rounded-xl p-3 transition-colors hover:bg-white/[0.03]",
              `fade-up-${Math.min(i + 1, 5)}`
            )}
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

  // Skeleton
  if (loading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-7">
          <div className="space-y-2">
            <div className="h-7 w-36 rounded-lg animate-pulse" style={{ background: "var(--bg3)" }} />
            <div className="h-4 w-24 rounded-lg animate-pulse" style={{ background: "var(--bg3)" }} />
          </div>
          <div className="h-9 w-32 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-7">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 rounded-2xl animate-pulse" style={{ background: "var(--bg3)" }} />
          ))}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-44 rounded-2xl animate-pulse" style={{ background: "var(--bg3)" }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>Dashboard</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--muted)" }}>
            {competitorList.length === 0
              ? "No competitors tracked yet"
              : `Monitoring ${competitorList.length} store${competitorList.length !== 1 ? "s" : ""}`}
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

      {/* Stats bar — always visible */}
      {competitorList.length > 0 && !alertsLoading && (
        <StatsBar competitorList={competitorList} alertList={alertList} />
      )}

      {competitorList.length === 0 ? (
        <EmptyState onAdd={() => setShowModal(true)} />
      ) : (
        <div className="flex gap-6 items-start">

          {/* ── Left: competitor grid ── */}
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

          {/* ── Right: intelligence feed (desktop) ── */}
          <div className="hidden lg:block w-72 shrink-0">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4" style={{ color: "var(--accent)" }} />
                <p className="text-sm font-bold" style={{ color: "var(--text)" }}>Change Feed</p>
              </div>
              <Link
                href="/alerts"
                className="text-xs font-medium flex items-center gap-1 hover:opacity-80"
                style={{ color: "var(--accent)" }}
              >
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            {/* 7-day activity chart */}
            {!alertsLoading && <WeeklyActivityChart alertList={alertList} />}

            {/* Spotlight alert */}
            {!alertsLoading && <SpotlightAlert alertList={alertList} />}

            {/* Watch list */}
            <WatchList competitorList={competitorList} />

            {/* Recent changes */}
            {!alertsLoading && alertList.length > 0 && (
              <ActivityFeed alertList={alertList} alertsLoading={alertsLoading} />
            )}
          </div>
        </div>
      )}

      {/* ── Mobile: stacked feed below ── */}
      {competitorList.length > 0 && (
        <div className="lg:hidden mt-8 space-y-4">
          {!alertsLoading && <WeeklyActivityChart alertList={alertList} />}
          {!alertsLoading && <SpotlightAlert alertList={alertList} />}
          <WatchList competitorList={competitorList} />
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4" style={{ color: "var(--accent)" }} />
              <p className="text-sm font-bold" style={{ color: "var(--text)" }}>Change Feed</p>
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
