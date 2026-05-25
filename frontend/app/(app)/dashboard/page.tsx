"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Plus, RefreshCw, TrendingUp, Sparkles, ArrowRight,
  Activity, Package, Zap, Clock, X,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { BarChart, Bar, XAxis, ResponsiveContainer, Cell } from "recharts";
import {
  competitors as api, alerts as alertsApi,
  type Competitor, type AlertEvent, type DiscoverySuggestion,
} from "@/lib/api";
import { cn, formatRelativeTime, formatPrice } from "@/lib/utils";
import { groupAlertEvents, generateNarrative, type SignalGroup } from "@/lib/signals";
import { SignalFeed } from "@/components/signals/SignalFeed";
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

// ── Stats bar ─────────────────────────────────────────────────────────────

function StatsBar({ competitorList, signalGroups }: { competitorList: Competitor[]; signalGroups: SignalGroup[] }) {
  const totalProducts = competitorList.reduce((s, c) => s + (c.product_count || 0), 0);
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const weeklyChanges = signalGroups.reduce(
    (s, g) => s + g.events.filter((e) => new Date(e.detected_at).getTime() > weekAgo).length,
    0
  );
  const criticals = signalGroups
    .filter((g) => g.tier === "strategic")
    .filter((g) => new Date(g.detected_at).getTime() > weekAgo).length;

  const nextScanTs = competitorList
    .filter((c) => c.next_scan_at)
    .map((c) => new Date(c.next_scan_at!).getTime())
    .sort((a, b) => a - b)[0];

  const stats = [
    { icon: Package, label: "Products tracked", value: totalProducts.toLocaleString(), color: "var(--blue)" },
    {
      icon: Activity, label: "Changes this week",
      value: weeklyChanges.toString(),
      color: weeklyChanges > 0 ? "var(--accent)" : "var(--muted)",
      highlight: weeklyChanges > 0,
    },
    {
      icon: Zap,
      label: criticals > 0 ? "Active signals" : "All clear",
      value: criticals > 0 ? criticals.toString() : "✓",
      color: criticals > 0 ? "var(--red)" : "var(--emerald)",
    },
    ...(nextScanTs ? [{ icon: Clock, label: "Next scan", value: formatNextScan(new Date(nextScanTs).toISOString()), color: "var(--muted)" }] : []),
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      {stats.map(({ icon: Icon, label, value, color, highlight }) => (
        <div
          key={label}
          className="rounded-xl px-4 py-3 flex items-center gap-3"
          style={{
            background: highlight ? "rgba(168,255,0,.05)" : "var(--bg3)",
            border: highlight ? "1px solid rgba(168,255,0,.18)" : "1px solid var(--border)",
          }}
        >
          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${color}18` }}>
            <Icon className="w-4 h-4" style={{ color }} />
          </div>
          <div className="min-w-0">
            <p className="text-lg font-bold font-mono leading-none" style={{ color: "var(--text)" }}>{value}</p>
            <p className="text-[11px] mt-0.5 truncate" style={{ color: "var(--muted)" }}>{label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Narrative header ──────────────────────────────────────────────────────

function NarrativeBar({ narrative, signalGroups }: { narrative: string | null; signalGroups: SignalGroup[] }) {
  if (!narrative) return null;
  const hasStrategic = signalGroups.some((g) => g.tier === "strategic");
  return (
    <div
      className="flex items-center gap-3 rounded-xl px-4 py-2.5 mb-4 fade-in"
      style={{
        background: hasStrategic ? "rgba(239,68,68,.06)" : "rgba(168,255,0,.05)",
        border: hasStrategic ? "1px solid rgba(239,68,68,.2)" : "1px solid rgba(168,255,0,.14)",
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0 animate-pulse"
        style={{ background: hasStrategic ? "var(--red)" : "var(--accent)" }}
      />
      <p className="text-xs font-semibold" style={{ color: hasStrategic ? "var(--red)" : "var(--accent)" }}>
        {narrative}
      </p>
    </div>
  );
}

// ── Weekly activity chart ─────────────────────────────────────────────────

function WeeklyChart({ alertList }: { alertList: AlertEvent[] }) {
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    const count = alertList.filter((a) => new Date(a.detected_at).toDateString() === d.toDateString()).length;
    return { day: d.toLocaleDateString("en-US", { weekday: "short" }), count, isToday: i === 6 };
  });
  const hasActivity = days.some((d) => d.count > 0);

  return (
    <div className="rounded-xl px-4 pt-3.5 pb-2 mb-3" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>7-day activity</p>
        {!hasActivity && <span className="text-[11px]" style={{ color: "var(--muted)" }}>All quiet</span>}
      </div>
      <ResponsiveContainer width="100%" height={48}>
        <BarChart data={days} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <XAxis dataKey="day" tick={{ fill: "#5a6a82", fontSize: 9 }} axisLine={false} tickLine={false} />
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {days.map((d, i) => (
              <Cell key={i} fill={d.count === 0 ? "rgba(255,255,255,.06)" : d.isToday ? "#a8ff00" : "rgba(96,165,250,.6)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Competitor monitor strip ──────────────────────────────────────────────

function CompetitorMonitor({ competitor, signalGroups }: { competitor: Competitor; signalGroups: SignalGroup[] }) {
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

  async function handleRescan(e: React.MouseEvent) {
    e.preventDefault();
    setRescanning(true);
    await api.rescan(competitor.id).catch(() => {});
    setTimeout(() => setRescanning(false), 3000);
  }

  const statusColor = isScanning ? "var(--accent)" : hasStrategic ? "var(--red)" : "var(--emerald)";

  return (
    <Link
      href={`/dashboard/${competitor.id}`}
      className={cn(
        "flex items-center gap-3 rounded-xl px-4 py-3 transition-colors hover:bg-white/[0.03] group",
        isScanning && "scan-shimmer"
      )}
      style={{ border: `1px solid ${hasStrategic ? "rgba(239,68,68,.2)" : "var(--border)"}`, background: "var(--bg3)" }}
    >
      {/* Status dot */}
      <span
        className={cn("w-2 h-2 rounded-full shrink-0", isScanning && "animate-pulse")}
        style={{ background: statusColor }}
      />

      {/* Name + stats */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold truncate" style={{ color: "var(--text)" }}>
            {competitor.display_name || competitor.hostname}
          </p>
          {changeCount > 0 && (
            <span
              className="text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
              style={{ background: hasStrategic ? "rgba(239,68,68,.15)" : "rgba(168,255,0,.1)", color: hasStrategic ? "var(--red)" : "var(--accent)" }}
            >
              {changeCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[11px]" style={{ color: "var(--muted)" }}>
            {competitor.product_count?.toLocaleString() ?? "—"} products
          </span>
          {medianPrice != null && (
            <>
              <span style={{ color: "var(--border)" }}>·</span>
              <span className="text-[11px] font-mono" style={{ color: "var(--muted)" }}>{formatPrice(medianPrice)} median</span>
            </>
          )}
        </div>
      </div>

      {/* Next scan + rescan */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-[11px]" style={{ color: "var(--muted)" }}>
          {isScanning ? "Scanning…" : `Next: ${formatNextScan(competitor.next_scan_at)}`}
        </span>
        <button
          onClick={handleRescan}
          className="p-1 rounded-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-white/10"
          style={{ color: "var(--muted)" }}
        >
          <RefreshCw className={cn("w-3 h-3", (rescanning || isScanning) && "animate-spin")} />
        </button>
      </div>
    </Link>
  );
}

// ── Most active competitor ────────────────────────────────────────────────

function MostActive({ competitorList, signalGroups }: { competitorList: Competitor[]; signalGroups: SignalGroup[] }) {
  const dayAgo = Date.now() - 24 * 60 * 60 * 1000;
  const ranked = competitorList
    .map((c) => ({
      competitor: c,
      count: signalGroups.filter((g) => g.competitor_id === c.id && new Date(g.detected_at).getTime() > dayAgo)
        .reduce((s, g) => s + g.count, 0),
    }))
    .filter((r) => r.count > 0)
    .sort((a, b) => b.count - a.count);

  if (ranked.length === 0) return null;

  const top = ranked[0];
  return (
    <div
      className="rounded-xl px-4 py-3 mb-3 flex items-center gap-3"
      style={{ background: "rgba(239,68,68,.05)", border: "1px solid rgba(239,68,68,.18)" }}
    >
      <span className="text-base shrink-0">🔥</span>
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-wider mb-0.5" style={{ color: "var(--red)" }}>Most active today</p>
        <p className="text-xs font-semibold truncate" style={{ color: "var(--text)" }}>
          {top.competitor.hostname} · <span style={{ color: "var(--muted)" }}>{top.count} change{top.count !== 1 ? "s" : ""}</span>
        </p>
      </div>
    </div>
  );
}

// ── Watch list panel ──────────────────────────────────────────────────────

function WatchPanel({ competitorList }: { competitorList: Competitor[] }) {
  return (
    <div className="rounded-xl overflow-hidden mb-3" style={{ border: "1px solid var(--border)" }}>
      <div className="px-4 py-2.5 flex items-center gap-2" style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}>
        <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "var(--emerald)" }} />
        <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>Watching</p>
      </div>
      <div style={{ background: "var(--bg-card)" }}>
        {competitorList.map((c) => {
          const color = c.scan_status === "scanning" ? "var(--accent)" : c.scan_status === "error" ? "var(--red)" : "var(--emerald)";
          return (
            <Link
              key={c.id}
              href={`/dashboard/${c.id}`}
              className="flex items-center justify-between px-4 py-2.5 border-b last:border-0 hover:bg-white/[0.02] transition-colors"
              style={{ borderColor: "var(--border)" }}
            >
              <div className="min-w-0">
                <p className="text-xs font-semibold truncate" style={{ color: "var(--text)" }}>
                  {c.display_name || c.hostname}
                </p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", c.scan_status === "scanning" && "animate-pulse")} style={{ background: color }} />
                  <span className="text-[11px]" style={{ color: "var(--muted)" }}>
                    {c.scan_status === "scanning" ? "Scanning now" : `Next: ${formatNextScan(c.next_scan_at)}`}
                  </span>
                </div>
              </div>
              {c.product_count != null && (
                <span className="text-[11px] font-mono shrink-0 ml-2" style={{ color: "var(--muted)" }}>
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

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] text-center px-6 fade-in">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6" style={{ background: "rgba(168,255,0,.08)", border: "1px solid rgba(168,255,0,.18)" }}>
        <TrendingUp className="w-8 h-8" style={{ color: "var(--accent)" }} />
      </div>
      <h2 className="text-2xl font-bold mb-3" style={{ color: "var(--text)" }}>Track your first competitor</h2>
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
          <span className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold" style={{ background: "rgba(168,255,0,.12)", color: "var(--accent)" }}>
            AI matched
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
                style={{ background: "var(--accent)", color: "#0a0a0f" }}
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

export default function DashboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [competitorList, setCompetitorList] = useState<Competitor[]>([]);
  const [alertList, setAlertList] = useState<AlertEvent[]>([]);
  const [suggestions, setSuggestions] = useState<DiscoverySuggestion[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [addPrefilledUrl, setAddPrefilledUrl] = useState("");
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [trackingHostname, setTrackingHostname] = useState<string | null>(null);

  // Auto-open upgrade modal when onboarding sends ?upgrade=pro or ?upgrade=agency
  useEffect(() => {
    const plan = searchParams.get("upgrade");
    if (plan === "pro" || plan === "agency") {
      setUpgradeOpen(true);
      router.replace("/dashboard");
    }
    // ?add=hostname — pre-open Add Competitor modal (from shareable report CTA)
    const addHostname = searchParams.get("add");
    if (addHostname) {
      const normalizedHostname = addHostname.replace(/^https?:\/\//, "");
      setAddPrefilledUrl(`https://${normalizedHostname}`);
      setShowModal(true);
      router.replace("/dashboard");
    }
  }, [searchParams, router]);

  const load = useCallback(async () => {
    try { const { data } = await api.list(); setCompetitorList(data); }
    catch {}
    finally { setLoading(false); }
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
      if ((err as { status?: number })?.status === 403) setUpgradeOpen(true);
    } finally {
      setTrackingHostname(null);
    }
  }

  function handleDismiss(hostname: string) {
    setDismissed((prev) => new Set([...prev, hostname]));
  }

  // Compute signal groups once from loaded alerts
  const signalGroups = alertsLoading ? [] : groupAlertEvents(alertList);
  const narrative = generateNarrative(signalGroups);

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

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
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

      {competitorList.length === 0 ? (
        <>
          <EmptyState onAdd={() => setShowModal(true)} />
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
          {!alertsLoading && <StatsBar competitorList={competitorList} signalGroups={signalGroups} />}

          {/* Narrative bar */}
          {!alertsLoading && <NarrativeBar narrative={narrative} signalGroups={signalGroups} />}

          {/* ── 3-column layout ── */}
          <div className="flex gap-5 items-start">

            {/* ── Center: intelligence stream ── */}
            <div className="flex-1 min-w-0">
              {/* Competitor monitors */}
              <div className="space-y-2 mb-5">
                {competitorList.map((c) => (
                  <CompetitorMonitor key={c.id} competitor={c} signalGroups={signalGroups} />
                ))}
              </div>

              {/* Signal feed — the hero */}
              {!alertsLoading && (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Activity className="w-4 h-4" style={{ color: "var(--accent)" }} />
                      <p className="text-sm font-bold" style={{ color: "var(--text)" }}>Intelligence Stream</p>
                    </div>
                    <Link
                      href="/alerts"
                      className="text-xs font-medium flex items-center gap-1 hover:opacity-80"
                      style={{ color: "var(--accent)" }}
                    >
                      Full feed <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                  {signalGroups.length === 0 ? (
                    <div
                      className="rounded-xl p-6 text-center"
                      style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                    >
                      <p className="text-sm font-medium mb-1" style={{ color: "var(--muted)" }}>All quiet</p>
                      <p className="text-xs leading-relaxed" style={{ color: "var(--muted)", opacity: 0.7 }}>
                        We&apos;ll surface signals here the moment a competitor makes a move.
                      </p>
                    </div>
                  ) : (
                    <SignalFeed groups={signalGroups} />
                  )}
                </>
              )}

            </div>

            {/* ── Right: context panel (desktop only) ── */}
            <div className="hidden lg:block w-64 shrink-0 space-y-3">
              {/* 7-day chart */}
              {!alertsLoading && <WeeklyChart alertList={alertList} />}

              {/* Most active today */}
              {!alertsLoading && <MostActive competitorList={competitorList} signalGroups={signalGroups} />}

              {/* Watch list */}
              <WatchPanel competitorList={competitorList} />

              {/* Discovery suggestions */}
              <DiscoverySuggestions
                suggestions={suggestions}
                onTrack={handleTrack}
                tracking={trackingHostname}
                dismissed={dismissed}
                onDismiss={handleDismiss}
              />
            </div>
          </div>

          {/* Mobile: context panel stacked below */}
          <div className="lg:hidden mt-6 space-y-3">
            {!alertsLoading && <WeeklyChart alertList={alertList} />}
            {!alertsLoading && <MostActive competitorList={competitorList} signalGroups={signalGroups} />}
            <WatchPanel competitorList={competitorList} />
            {/* Discovery on mobile — below the rest */}
            <DiscoverySuggestions
              suggestions={suggestions}
              onTrack={handleTrack}
              tracking={trackingHostname}
              dismissed={dismissed}
              onDismiss={handleDismiss}
            />
          </div>
        </>
      )}

      {showModal && (
        <AddCompetitorModal
          onClose={() => { setShowModal(false); setAddPrefilledUrl(""); }}
          onAdded={handleAdded}
          initialUrl={addPrefilledUrl || undefined}
        />
      )}
      {upgradeOpen && <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="competitor_limit" />}
    </div>
  );
}
