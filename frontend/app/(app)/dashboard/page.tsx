"use client";

import { useEffect, useState, useCallback, useRef, Suspense } from "react";
import {
  RefreshCw, ArrowRight, Sparkles,
  Activity, Zap, Clock, X, Lock, Target, Plus, Check, TrendingUp, ShieldAlert,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import {
  competitors as api, alerts as alertsApi, user as userApi,
  type Competitor, type AlertEvent, type DiscoverySuggestion, type PlaybookPlay,
} from "@/lib/api";
import { cn, formatPrice, formatRelativeTime } from "@/lib/utils";
import { groupAlertEvents, type SignalGroup, SIGNAL_CONFIG } from "@/lib/signals";
import { SignalFeed } from "@/components/signals/SignalFeed";
import { ActionPlaybook } from "@/components/competitors/ActionPlaybook";
import UpgradeModal from "@/components/UpgradeModal";
import { ScoutBrief, MetricCard } from "@/components/ui";

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

// ── Stats bar ─────────────────────────────────────────────────────────────

const OPPORTUNITY_TYPES = new Set(["launch_burst", "price_increase", "product_removals", "availability_shift"]);
const THREAT_TYPES = new Set(["flash_sale", "price_wave", "discount_wave"]);

function StatsBar({ competitorList, signalGroups, alertList }: { competitorList: Competitor[]; signalGroups: SignalGroup[]; alertList: AlertEvent[] }) {
  const weekAgo  = Date.now() - 7  * 24 * 60 * 60 * 1000;
  const twoWeeksAgo = Date.now() - 14 * 24 * 60 * 60 * 1000;
  const dayAgo   = Date.now() - 24 * 60 * 60 * 1000;

  const thisWeekChanges = alertList.filter((e) => new Date(e.detected_at).getTime() > weekAgo).length;
  const prevWeekChanges = alertList.filter((e) => {
    const t = new Date(e.detected_at).getTime();
    return t > twoWeeksAgo && t <= weekAgo;
  }).length;
  const todayChanges = alertList.filter((e) => new Date(e.detected_at).getTime() > dayAgo).length;

  const weeklyDelta = prevWeekChanges > 0
    ? Math.round(((thisWeekChanges - prevWeekChanges) / prevWeekChanges) * 100)
    : null;

  const dailyCounts = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return alertList.filter((a) => new Date(a.detected_at).toDateString() === d.toDateString()).length;
  });

  const strategicThisWeek = signalGroups.filter(
    (g) => g.tier === "strategic" && new Date(g.detected_at).getTime() > weekAgo
  );
  const opportunities = strategicThisWeek.filter((g) => OPPORTUNITY_TYPES.has(g.type)).length;
  const threats       = strategicThisWeek.filter((g) => THREAT_TYPES.has(g.type)).length;

  const nextScanTs = competitorList
    .filter((c) => c.next_scan_at)
    .map((c) => new Date(c.next_scan_at!).getTime())
    .sort((a, b) => a - b)[0];

  const changesColor = thisWeekChanges > 0 ? "var(--accent)" : "var(--muted)";
  const changesDeltaText = todayChanges > 0 && weeklyDelta === null ? `${todayChanges} today` : undefined;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <MetricCard
        icon={TrendingUp}
        label="Opportunities"
        value={opportunities}
        color={opportunities > 0 ? "var(--emerald)" : "var(--muted)"}
        deltaText="this week"
      />
      <MetricCard
        icon={Activity}
        label="Changes this week"
        value={thisWeekChanges}
        color={changesColor}
        delta={weeklyDelta}
        deltaText={changesDeltaText}
        sparkline={dailyCounts}
      />
      <MetricCard
        icon={ShieldAlert}
        label="Threats"
        value={threats}
        color={threats > 0 ? "var(--red)" : "var(--muted)"}
        deltaText="this week"
      />
      {nextScanTs && (
        <MetricCard icon={Clock} label="Next auto-scan" value={formatNextScan(new Date(nextScanTs).toISOString())} color="var(--muted)" />
      )}
    </div>
  );
}

// ── Signal type breakdown ─────────────────────────────────────────────────

function SignalBreakdown({ groups }: { groups: SignalGroup[] }) {
  if (groups.length === 0) return null;

  const price = groups
    .filter((g) => ["price_wave", "price_increase", "flash_sale"].includes(g.type))
    .reduce((s, g) => s + g.count, 0);
  const launch = groups
    .filter((g) => g.type === "launch_burst")
    .reduce((s, g) => s + g.count, 0);
  const discount = groups
    .filter((g) => ["discount_wave", "flash_sale"].includes(g.type))
    .reduce((s, g) => s + g.count, 0);
  const stock = groups
    .filter((g) => g.type === "availability_shift")
    .reduce((s, g) => s + g.count, 0);

  const items = [
    { label: "price changes", count: price, color: "var(--accent)", hex: "#3b82f6" },
    { label: "launches", count: launch, color: "var(--emerald)", hex: "#10b981" },
    { label: "discounts", count: discount, color: "var(--amber)", hex: "var(--amber)" },
    { label: "stock events", count: stock, color: "var(--muted)", hex: "#64748b" },
  ].filter((i) => i.count > 0);

  if (items.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mb-3 px-0.5">
      {items.map(({ label, count, hex }) => (
        <span key={label} className="flex items-center gap-1.5 text-xs">
          <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: hex }} />
          <span className="font-bold tabular-nums" style={{ color: "var(--text)" }}>{count}</span>
          <span style={{ color: "var(--muted)" }}>{label}</span>
        </span>
      ))}
    </div>
  );
}

// ── Playbook sidebar widget ───────────────────────────────────────────────

const DEADLINE_COLOR: Record<string, string> = {
  "right now": "#f87171",
  "today": "var(--amber)",
  "within 48h": "var(--amber)",
  "this week": "#3b82f6",
};

function PlaybookWidget() {
  const [plays, setPlays] = useState<PlaybookPlay[]>([]);
  const [playbookLoading, setPlaybookLoading] = useState(true);
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    userApi.playbook()
      .then((r) => { setPlays((r.plays || []).slice(0, 1)); setLocked(r.locked ?? false); })
      .catch(() => {})
      .finally(() => setPlaybookLoading(false));
  }, []);

  if (!playbookLoading && plays.length === 0 && !locked) return null;

  return (
    <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
      <div
        className="px-4 py-2.5 flex items-center justify-between"
        style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}
      >
        <p className="label-caps">Playbook</p>
        <Link
          href="/playbook"
          className="text-[11px] font-medium flex items-center gap-1"
          style={{ color: "var(--muted)" }}
          onMouseEnter={(e) => { (e.target as HTMLElement).style.color = "var(--text-2)"; }}
          onMouseLeave={(e) => { (e.target as HTMLElement).style.color = "var(--muted)"; }}
        >
          See all <ArrowRight className="w-3 h-3" />
        </Link>
      </div>
      <div style={{ background: "var(--bg-card)" }}>
        {playbookLoading ? (
          <div className="px-4 py-3 animate-pulse">
            <div className="h-3 rounded-full w-4/5" style={{ background: "var(--bg3)" }} />
            <div className="h-2.5 rounded-full w-1/2 mt-1.5" style={{ background: "var(--bg3)" }} />
          </div>
        ) : locked ? (
          <div className="px-4 py-3 flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 shrink-0" style={{ color: "var(--muted)" }} />
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              Upgrade to Pro to unlock your full playbook.
            </p>
          </div>
        ) : (
          plays.map((p, i) => (
            <Link
              key={p.id}
              href="/playbook"
              className="flex items-start gap-2.5 px-4 py-3 hover:bg-white/[0.02] transition-colors"
              style={i < plays.length - 1 ? { borderBottom: "1px solid var(--border)" } : undefined}
            >
              <span
                className="text-[9px] font-bold px-1.5 py-0.5 rounded mt-0.5 whitespace-nowrap shrink-0"
                style={{
                  background: `${DEADLINE_COLOR[p.deadline] ?? "#94a3b8"}18`,
                  color: DEADLINE_COLOR[p.deadline] ?? "#94a3b8",
                }}
              >
                {p.deadline}
              </span>
              <p className="text-xs leading-snug line-clamp-3" style={{ color: "var(--text)" }}>
                {p.headline}
              </p>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

// ── Competitor monitor strip ──────────────────────────────────────────────

function CompetitorMonitor({
  competitor, signalGroups, selectMode, isSelected, onToggle,
}: {
  competitor: Competitor;
  signalGroups: SignalGroup[];
  selectMode: boolean;
  isSelected: boolean;
  onToggle: () => void;
}) {
  const [rescanning, setRescanning] = useState(false);
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const recentSignals = signalGroups.filter(
    (g) => g.competitor_id === competitor.id && new Date(g.detected_at).getTime() > weekAgo
  );
  const isScanning = competitor.scan_status === "scanning";
  const hasStrategic = recentSignals.some((g) => g.tier === "strategic");
  const changeCount = recentSignals.reduce((s, g) => s + g.count, 0);

  const snapshotData = competitor.snapshot_data as Record<string, unknown> | undefined;
  const pricing = snapshotData?.pricing as Record<string, unknown> | undefined;
  const medianPrice = pricing?.median as number | undefined;

  // Clear queued state once the scan actually picks up
  useEffect(() => {
    if (isScanning) setRescanning(false);
  }, [isScanning]);

  async function handleRescan(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setRescanning(true);
    await api.rescan(competitor.id).catch(() => { setRescanning(false); });
  }

  const topStrategic = recentSignals.find((g) => g.tier === "strategic");
  const topSignalCfg = topStrategic ? SIGNAL_CONFIG[topStrategic.type] : null;

  // Orange for "urgent intelligence", not red (red = errors/broken)
  const ALERT_COLOR = "var(--amber)";
  const statusColor = isScanning ? "var(--accent)" : hasStrategic ? ALERT_COLOR : "var(--emerald)";

  const borderColor = isSelected
    ? "rgba(59,130,246,.3)"
    : hasStrategic
    ? "rgba(245,158,11,.2)"
    : "var(--border)";

  const rowBody = (
    <>
      {/* Checkbox — always visible in select mode, hover-visible otherwise */}
      <div
        className={cn(
          "w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-all",
          !selectMode && "opacity-0 group-hover:opacity-100",
        )}
        style={{
          borderColor: isSelected ? "var(--accent)" : "var(--muted)",
          background: isSelected ? "var(--accent)" : "transparent",
        }}
        onClick={!selectMode ? (e) => { e.preventDefault(); e.stopPropagation(); onToggle(); } : undefined}
      >
        {isSelected && <Check className="w-2.5 h-2.5" style={{ color: "#ffffff" }} />}
      </div>

      {/* Status dot — hidden when checkbox is shown */}
      {!selectMode && (
        <span
          className={cn(
            "w-2 h-2 rounded-full shrink-0 transition-opacity group-hover:opacity-0",
            isScanning && "animate-pulse"
          )}
          style={{ background: statusColor }}
        />
      )}

      {/* Name + stats */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold truncate" style={{ color: "var(--text)" }}>
            {competitor.display_name || competitor.hostname}
          </p>
          {changeCount > 0 && (
            <span
              className="text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
              style={{ background: hasStrategic ? "rgba(239,68,68,.15)" : "rgba(59,130,246,.1)", color: hasStrategic ? "var(--red)" : "var(--accent)" }}
            >
              {changeCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          <span className="text-[11px] num" style={{ color: "var(--muted)" }}>
            {competitor.product_count?.toLocaleString() ?? "—"} products
          </span>
          {medianPrice != null && (
            <>
              <span style={{ color: "var(--border)" }}>·</span>
              <span className="text-[11px] num" style={{ color: "var(--muted)" }}>{formatPrice(medianPrice)} median</span>
            </>
          )}
          {competitor.promo_rate != null && competitor.promo_rate > 0 && (
            <>
              <span style={{ color: "var(--border)" }}>·</span>
              <span className="text-[11px] num" style={{ color: competitor.promo_rate >= 20 ? "var(--amber)" : "var(--muted)" }}>
                {competitor.promo_rate.toFixed(0)}% on sale
              </span>
            </>
          )}
        </div>
      </div>

      {/* Right side: signal pill or last-scan time + rescan */}
      {!selectMode && (
        <div className="flex items-center gap-2 shrink-0">
          {isScanning ? (
            <span className="text-[11px]" style={{ color: "var(--accent)" }}>Scanning…</span>
          ) : rescanning ? (
            <span className="text-[11px]" style={{ color: "var(--muted)" }}>Queued…</span>
          ) : topSignalCfg && topStrategic ? (
            <span
              className="text-[10px] font-bold px-2 py-1 rounded-md whitespace-nowrap"
              style={{ background: `color-mix(in srgb, ${topSignalCfg.color} 12%, transparent)`, color: topSignalCfg.color }}
            >
              {topStrategic.headline}
            </span>
          ) : changeCount > 0 ? (
            <span
              className="text-[10px] font-semibold px-2 py-1 rounded-md"
              style={{ background: "rgba(59,130,246,.08)", color: "var(--accent)" }}
            >
              {changeCount} change{changeCount !== 1 ? "s" : ""}
            </span>
          ) : competitor.last_scanned_at ? (
            <span className="text-[11px]" style={{ color: "var(--muted)" }}>
              {formatRelativeTime(competitor.last_scanned_at)}
            </span>
          ) : null}
          <button
            onClick={handleRescan}
            className="p-1 rounded-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-white/10"
            style={{ color: "var(--muted)" }}
          >
            <RefreshCw className={cn("w-3 h-3", (rescanning || isScanning) && "animate-spin")} />
          </button>
        </div>
      )}
    </>
  );

  const sharedClass = cn(
    "flex items-center gap-3 rounded-xl px-4 py-3 transition-colors group",
    isScanning && !selectMode && "scan-shimmer",
    isSelected && "bg-[rgba(59,130,246,.03)]"
  );
  const sharedStyle = {
    border: `1px solid ${borderColor}`,
    background: isSelected ? "rgba(59,130,246,.03)" : "var(--bg3)",
  };

  if (selectMode) {
    return (
      <div
        onClick={onToggle}
        className={cn(sharedClass, "cursor-pointer hover:bg-white/[0.02]")}
        style={sharedStyle}
      >
        {rowBody}
      </div>
    );
  }

  return (
    <Link
      href={`/dashboard/${competitor.id}`}
      className={cn(sharedClass, "hover:bg-white/[0.03]")}
      style={sharedStyle}
    >
      {rowBody}
    </Link>
  );
}

// ── Most active competitor ────────────────────────────────────────────────


// ── Watch list panel ──────────────────────────────────────────────────────

function WatchPanel({ competitorList, signalGroups }: { competitorList: Competitor[]; signalGroups: SignalGroup[] }) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const errorCount = competitorList.filter((c) => c.scan_status === "error").length;
  const scanningCount = competitorList.filter((c) => c.scan_status === "scanning").length;
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
      <div className="px-4 py-2.5 flex items-center justify-between" style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <span className={cn("w-1.5 h-1.5 rounded-full", scanningCount > 0 && "animate-pulse")}
            style={{ background: errorCount > 0 ? "var(--red)" : scanningCount > 0 ? "var(--accent)" : "var(--emerald)" }} />
          <p className="label-caps">Tracked stores</p>
        </div>
        <Link href="/competitors" className="text-[11px] font-medium" style={{ color: "var(--muted)" }}
          onMouseEnter={(e) => { (e.target as HTMLElement).style.color = "var(--text-2)"; }}
          onMouseLeave={(e) => { (e.target as HTMLElement).style.color = "var(--muted)"; }}
        >
          Manage →
        </Link>
      </div>
      <div style={{ background: "var(--bg-card)" }}>
        {competitorList.map((c) => {
          const isScanning = c.scan_status === "scanning";
          const isError = c.scan_status === "error";
          const dotColor = isScanning ? "var(--accent)" : isError ? "var(--red)" : "var(--emerald)";
          const weeklyChanges = signalGroups
            .filter((g) => g.competitor_id === c.id && new Date(g.detected_at).getTime() > weekAgo)
            .reduce((s, g) => s + g.count, 0);
          const subtext = isScanning
            ? "Scanning now"
            : isError
            ? "Scan error"
            : c.last_scanned_at
            ? weeklyChanges > 0
              ? `${formatRelativeTime(c.last_scanned_at)} · ${weeklyChanges} change${weeklyChanges !== 1 ? "s" : ""}`
              : formatRelativeTime(c.last_scanned_at)
            : `Next: ${formatNextScan(c.next_scan_at)}`;
          return (
            <Link
              key={c.id}
              href={`/dashboard/${c.id}`}
              className="flex items-center justify-between px-4 py-2.5 border-b last:border-0 hover:bg-white/[0.02] transition-colors"
              style={{ borderColor: "var(--border)" }}
            >
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold truncate" style={{ color: "var(--text)" }}>
                  {c.display_name || c.hostname}
                </p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", isScanning && "animate-pulse")} style={{ background: dotColor }} />
                  <span className="text-[11px] truncate" style={{ color: weeklyChanges > 0 && !isScanning ? "var(--text-2)" : "var(--muted)" }}>
                    {subtext}
                  </span>
                </div>
              </div>
              {c.product_count != null && (
                <span className="text-[11px] font-mono shrink-0 ml-3" style={{ color: "var(--muted)" }}>
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

// ── Empty state ───────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[380px] text-center px-6 fade-in">
      <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-5" style={{ background: "rgba(255,255,255,.04)", border: "1px solid var(--border)" }}>
        <Target className="w-5 h-5" style={{ color: "var(--muted)" }} />
      </div>
      <h2 className="text-lg font-semibold mb-2" style={{ color: "var(--text)" }}>No competitors tracked yet</h2>
      <p className="text-sm mb-7 max-w-xs leading-relaxed" style={{ color: "var(--muted)" }}>
        Add a Shopify store to start monitoring price changes, product launches, and discount campaigns.
      </p>
      <Link
        href="/competitors"
        className="flex items-center gap-2 text-sm font-semibold px-5 py-2.5 rounded-lg transition-all"
        style={{ background: "var(--accent)", color: "#ffffff" }}
      >
        Add your first competitor
      </Link>
    </div>
  );
}

// ── Discovery suggestions ─────────────────────────────────────────────────

function DiscoverySuggestions({
  suggestions, onTrack, tracking, dismissed, onDismiss,
}: {
  suggestions: DiscoverySuggestion[];
  onTrack: (hostname: string) => Promise<void>;
  tracking: string | null;
  dismissed: Set<string>;
  onDismiss: (hostname: string) => void;
}) {
  const visible = suggestions.filter((s) => !dismissed.has(s.hostname));
  if (visible.length === 0) return null;

  const isCurated = visible.every((s) => s.is_curated);

  return (
    <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
      {/* Section header */}
      <div
        className="flex items-center gap-2 px-4 py-3"
        style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}
      >
        <Sparkles className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
        <p className="text-xs font-bold flex-1" style={{ color: "var(--text)" }}>
          {isCurated ? "Popular stores to track" : "Similar to what you're tracking"}
        </p>
        {!isCurated && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold" style={{ background: "rgba(59,130,246,.08)", color: "var(--muted)" }}>
            Based on your catalog
          </span>
        )}
      </div>

      {/* Suggestion rows */}
      <div>
        {visible.map((s, idx) => (
          <div
            key={s.hostname}
            className="flex items-center gap-3 px-4 py-3 group"
            style={{
              background: "var(--bg2)",
              borderTop: idx === 0 ? "none" : "1px solid var(--border)",
            }}
          >
            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-xs font-semibold truncate" style={{ color: "var(--text)" }}>
                  {s.hostname}
                </p>
                {s.median_price != null && (
                  <span className="text-[10px] font-mono shrink-0" style={{ color: "var(--muted)" }}>
                    ~${Math.round(s.median_price)} avg
                  </span>
                )}
              </div>
              {/* Match reason / category chips */}
              <div className="flex flex-wrap gap-1">
                {(s.match_reasons.length > 0 ? s.match_reasons : s.category ? [s.category] : []).slice(0, 3).map((r) => (
                  <span
                    key={r}
                    className="text-[10px] px-1.5 py-0.5 rounded-md"
                    style={{ background: "rgba(255,255,255,.05)", color: "var(--muted)" }}
                  >
                    {r}
                  </span>
                ))}
                {s.product_count != null && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-md" style={{ background: "rgba(255,255,255,.05)", color: "var(--muted)" }}>
                    {s.product_count.toLocaleString()} products
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={() => onDismiss(s.hostname)}
                className="p-1 rounded-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-white/5"
                style={{ color: "var(--muted)" }}
                title="Dismiss"
              >
                <X className="w-3 h-3" />
              </button>
              <button
                onClick={() => onTrack(s.hostname)}
                disabled={tracking === s.hostname}
                className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1.5 rounded-lg transition-all hover:brightness-110 disabled:opacity-50"
                style={{ background: "var(--accent)", color: "#ffffff" }}
              >
                {tracking === s.hostname
                  ? <RefreshCw className="w-3 h-3 animate-spin" />
                  : <Plus className="w-3 h-3" />}
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

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [competitorList, setCompetitorList] = useState<Competitor[]>([]);
  const [alertList, setAlertList] = useState<AlertEvent[]>([]);
  const [suggestions, setSuggestions] = useState<DiscoverySuggestion[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [trackingHostname, setTrackingHostname] = useState<string | null>(null);
  const [maxCompetitors, setMaxCompetitors] = useState<number | null>(null);
  const [userTier, setUserTier] = useState<string>("free");
  const [scanningAll, setScanningAll] = useState(false);
  const [firstName, setFirstName] = useState<string | null>(null);

  const scanAllStartRef = useRef<number>(0);

  async function handleScanAll() {
    if (scanningAll) return;
    setScanningAll(true);
    scanAllStartRef.current = Date.now();
    // Stagger requests 150ms apart to avoid concurrent DB issues
    for (const c of competitorList) {
      await api.rescan(c.id).catch(() => {});
      await new Promise<void>((r) => setTimeout(r, 150));
    }
    load();
  }

  // Resolve first name from OAuth metadata for the greeting
  useEffect(() => {
    createClient().auth.getUser().then(({ data }) => {
      const meta = data.user?.user_metadata ?? {};
      // Onboarding-entered name wins over OAuth defaults
      const full = (meta.display_name || meta.full_name || meta.name) as string | undefined;
      if (full) setFirstName(full.split(" ")[0]);
    }).catch(() => {});
  }, []);

  // Clear scanningAll once no competitors are actively scanning and a
  // minimum window has elapsed (so Celery has time to pick up the tasks)
  useEffect(() => {
    if (!scanningAll) return;
    const elapsed = Date.now() - scanAllStartRef.current;
    const anyScanning = competitorList.some((c) => c.scan_status === "scanning");
    if (elapsed > 15_000 && !anyScanning) setScanningAll(false);
  }, [competitorList, scanningAll]);

  // Auto-open upgrade modal when onboarding sends ?upgrade=pro or ?upgrade=agency
  useEffect(() => {
    const plan = searchParams.get("upgrade");
    if (plan === "pro" || plan === "agency") {
      setUpgradeOpen(true);
      router.replace("/dashboard");
    }
  }, [searchParams, router]);

  const load = useCallback(async () => {
    try { const { data } = await api.list(); setCompetitorList(data); }
    catch {}
    finally { setLoading(false); }
  }, []);

  // Load subscription once to know if user is at competitor limit
  useEffect(() => {
    userApi.subscription().then((r) => {
      setMaxCompetitors(r.data.limits?.max_competitors ?? 1);
      setUserTier(r.data.tier ?? "free");
    }).catch(() => {});
  }, []);

  const loadAlerts = useCallback(async () => {
    try { const { data } = await alertsApi.list(100); setAlertList(data); }
    catch {}
    finally { setAlertsLoading(false); }
  }, []);

  const loadSuggestions = useCallback(async () => {
    try { const { data } = await api.discover(); setSuggestions(data.suggestions || []); }
    catch {}
  }, []);

  useEffect(() => {
    load(); loadAlerts();
    const ci = setInterval(load, 10000);
    const ai = setInterval(loadAlerts, 30000);
    return () => { clearInterval(ci); clearInterval(ai); };
  }, [load, loadAlerts]);

  useEffect(() => {
    if (!loading) loadSuggestions();
  }, [loading, loadSuggestions]);

  async function handleTrack(hostname: string) {
    if (maxCompetitors !== null && competitorList.length >= maxCompetitors) {
      setUpgradeOpen(true);
      return;
    }
    setTrackingHostname(hostname);
    try {
      const { data: newComp } = await api.add(`https://${hostname}`);
      setCompetitorList((prev) => [newComp, ...prev]);
      setSuggestions((prev) => prev.filter((s) => s.hostname !== hostname));
      loadSuggestions();
    } catch (err: unknown) {
      const apiErr = err as { status?: number; data?: { detail?: { code?: string } | string } };
      const detail = apiErr?.data?.detail;
      const isLimitError =
        (typeof detail === "object" && detail?.code === "competitor_limit_reached") ||
        apiErr?.status === 402 ||
        apiErr?.status === 403;
      if (isLimitError) setUpgradeOpen(true);
    } finally {
      setTrackingHostname(null);
    }
  }

  function handleDismiss(hostname: string) {
    setDismissed((prev) => new Set([...prev, hostname]));
  }

  // Compute signal groups once from loaded alerts
  const signalGroups = alertsLoading ? [] : groupAlertEvents(alertList);

  // Skeleton
  if (loading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <div className="space-y-2">
            <div className="h-7 w-36 rounded-lg animate-pulse" style={{ background: "var(--bg3)" }} />
            <div className="h-4 w-24 rounded-lg animate-pulse" style={{ background: "var(--bg3)" }} />
          </div>
          <div className="h-9 w-32 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-14 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />)}
        </div>
        <div className="flex gap-5">
          <div className="flex-1 space-y-3">
            {[1, 2, 3].map((i) => <div key={i} className="h-20 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />)}
          </div>
          <div className="hidden lg:block w-64 space-y-3">
            {[1, 2, 3].map((i) => <div key={i} className="h-16 rounded-xl animate-pulse" style={{ background: "var(--bg3)" }} />)}
          </div>
        </div>
      </div>
    );
  }

  const nextScanTs = competitorList
    .filter((c) => c.next_scan_at)
    .map((c) => new Date(c.next_scan_at!).getTime())
    .sort((a, b) => a - b)[0];
  const lastScannedTs = competitorList
    .filter((c) => c.last_scanned_at)
    .map((c) => new Date(c.last_scanned_at!).getTime())
    .sort((a, b) => b - a)[0]; // most recent
  const weekAgoMs = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const changesThisWeek = alertList.filter((e) => new Date(e.detected_at).getTime() > weekAgoMs).length;
  const requireAction = signalGroups.filter(
    (g) => g.tier === "strategic" && new Date(g.detected_at).getTime() > weekAgoMs
  ).length;

  return (
    <div>
      {/* Greeting header */}
      {competitorList.length > 0 && (
        <ScoutBrief
          firstName={firstName}
          competitorCount={competitorList.length}
          lastScan={lastScannedTs ? formatRelativeTime(new Date(lastScannedTs).toISOString()) : undefined}
          nextScan={nextScanTs ? formatNextScan(new Date(nextScanTs).toISOString()) : undefined}
          changesThisWeek={changesThisWeek}
          requireAction={requireAction}
          onRefresh={handleScanAll}
          refreshing={scanningAll || competitorList.some((c) => c.scan_status === "scanning")}
        />
      )}

      {competitorList.length === 0 ? (
        <>
          <EmptyState />
          {suggestions.filter((s) => !dismissed.has(s.hostname)).length > 0 && (
            <div className="mt-6 max-w-sm">
              <DiscoverySuggestions
                suggestions={suggestions}
                onTrack={handleTrack}
                tracking={trackingHostname}
                dismissed={dismissed}
                onDismiss={handleDismiss}
              />
            </div>
          )}
        </>
      ) : (
        <>
          {/* Stats bar */}
          {!alertsLoading && <StatsBar competitorList={competitorList} signalGroups={signalGroups} alertList={alertList} />}

          {/* Your Move action panel */}
          <ActionPlaybook competitorCount={competitorList.length} />

          {/* ── 2-column layout ── */}
          <div className="flex gap-5 items-start">

            {/* ── Center: intelligence stream ── */}
            <div className="flex-1 min-w-0">

              {/* Signal feed */}
              {!alertsLoading && (
                <>
                  <div className="flex items-center justify-between mb-2.5">
                    <p className="label-caps">Recent signals</p>
                    <Link
                      href="/alerts"
                      className="text-[11px] font-medium flex items-center gap-1 transition-colors"
                      style={{ color: "var(--muted)" }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text-2)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = "var(--muted)"; }}
                    >
                      All alerts <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                  <SignalBreakdown groups={signalGroups} />
                  {signalGroups.length === 0 ? (
                    <div
                      className="rounded-lg px-4 py-5 text-center"
                      style={{ border: "1px solid var(--border)" }}
                    >
                      <p className="text-sm" style={{ color: "var(--muted)" }}>
                        No activity detected recently — we&apos;ll show signals here as competitors make changes.
                      </p>
                    </div>
                  ) : (
                    <SignalFeed groups={signalGroups} />
                  )}
                </>
              )}

            </div>

            {/* ── Right: context panel (desktop only) ── */}
            <div className="hidden lg:block w-[260px] shrink-0 space-y-3">
              {/* Competitor health */}
              <WatchPanel competitorList={competitorList} signalGroups={signalGroups} />

              {/* Playbook preview */}
              <PlaybookWidget />

              {/* Integration nudge */}
              <Link
                href="/settings?tab=integrations"
                className="flex items-start gap-2.5 px-3.5 py-3 rounded-xl transition-all block"
                style={{ background: "rgba(59,130,246,.04)", border: "1px solid rgba(59,130,246,.1)" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(59,130,246,.07)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(59,130,246,.04)"; }}
              >
                <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5" style={{ background: "rgba(59,130,246,.12)" }}>
                  <Zap className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold mb-0.5" style={{ color: "var(--text)" }}>Connect your store</p>
                  <p className="text-[11px] leading-snug" style={{ color: "var(--muted)" }}>Shopify, GA4 &amp; Klaviyo unlock personalized Playbook recommendations</p>
                </div>
              </Link>
            </div>
          </div>

          {/* Mobile: context panel stacked below */}
          <div className="lg:hidden mt-6 space-y-3">
            <WatchPanel competitorList={competitorList} signalGroups={signalGroups} />
            <PlaybookWidget />
          </div>
        </>
      )}

      {upgradeOpen && <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="competitor_limit" currentTier={userTier} />}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={null}>
      <DashboardContent />
    </Suspense>
  );
}
