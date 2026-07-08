"use client";

import { useEffect, useState, use, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft, RefreshCw, Trash2, Share2, Check, Download,
  Sparkles, Lock, Zap, ChevronDown, ChevronUp, Bell, TrendingUp,
  Package, Tag, Clock, Brain,
} from "lucide-react";
import Link from "next/link";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import {
  competitors as api, user as userApi,
  type Snapshot, type SnapshotMeta, type ChangeEvent, type AiSummary,
  type PriceHistoryPoint,
} from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import {
  cn, formatRelativeTime, formatPrice, formatPct, formatDelta,
  changeTypeIcon, changeTypeColor, changeTypeLabel, getChangeAction,
} from "@/lib/utils";
import { PriceDistributionChart } from "@/components/charts/PriceDistributionChart";
import { PriceHistoryChart } from "@/components/charts/PriceHistoryChart";
import { LaunchVelocityChart } from "@/components/charts/LaunchVelocityChart";
import WinningProductsTab from "@/components/competitors/WinningProductsTab";
import GapsTab from "@/components/competitors/GapsTab";
import { WatchlistPanel } from "@/components/dashboard/WatchlistPanel";
import StoreProfileTab from "@/components/competitors/StoreProfileTab";
import ComparisonTab from "@/components/competitors/ComparisonTab";
import { ProAnalysis, type ProAnalysisData } from "@/components/competitors/ProAnalysis";
import { QuickWins } from "@/components/competitors/QuickWins";
import UpgradeModal from "@/components/UpgradeModal";
import { LockedValueCard } from "@/components/ui";
import { type BriefData } from "@/lib/api";
import { SaveToPlaybook } from "@/components/SaveToPlaybook";

// ── Types ─────────────────────────────────────────────────────────────────────
type Tab = "overview" | "catalog" | "pricing" | "changes" | "intelligence";
type CatalogSub = "winning" | "gaps";
type IntelSub = "ai" | "brand" | "compare";

// ── Expandable KPI card ───────────────────────────────────────────────────────
function KpiCard({
  label, value, sub, accent, delta, insight, actionLabel, onAction, locked = false,
  sparkline,
}: {
  label: string; value: string; sub?: string; accent?: string;
  delta?: { label: string; up: boolean | null };
  insight?: string; actionLabel?: string; onAction?: () => void; locked?: boolean;
  sparkline?: number[];
}) {
  const [expanded, setExpanded] = useState(false);
  const clickable = !!insight;
  const deltaUp   = delta?.up === true;
  const deltaDown = delta?.up === false;
  const accentHex = accent?.startsWith("var(") ? "#FFB224" : (accent ?? "#FFB224");
  // Data marks use the validated series step, not the UI accent (dataviz)
  const sparkHex = "#6C7164";

  // Extract the numeric part: "▲ +5 vs last scan" → "+5"
  const badgeText = delta
    ? delta.label.replace(/^[▲▼±→\s]+/, "").replace(/ vs last scan$/, "").trim()
    : null;

  const sparkId = `sg-${label.replace(/\W+/g, "-").toLowerCase()}`;
  const showSpark = sparkline && sparkline.filter(v => v > 0).length >= 3;

  return (
    <div
      className={cn("rounded-md overflow-hidden transition-all", clickable && "cursor-pointer hover:ring-1 hover:ring-white/10")}
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderTop: accent ? `2px solid ${accentHex}` : "1px solid var(--border)",
      }}
      onClick={() => clickable && setExpanded((v) => !v)}
    >
      <div className="p-4">
        {/* Header: label + delta pill */}
        <div className="flex items-center justify-between mb-2">
          <p className="label-caps">{label}</p>
          {badgeText && (
            <span
              className="text-[10px] font-bold px-1.5 py-0.5 rounded-md"
              style={{
                background: deltaUp
                  ? "rgba(76,195,138,.15)"
                  : deltaDown
                  ? "rgba(242,85,90,.15)"
                  : "rgba(255,255,255,.06)",
                color: deltaUp ? "var(--emerald)" : deltaDown ? "#F2555A" : "var(--muted)",
              }}
            >
              {deltaUp ? "↑" : deltaDown ? "↓" : "→"} {badgeText}
            </span>
          )}
        </div>

        {/* Value */}
        <p className="text-2xl font-bold font-mono" style={{ color: "var(--text)" }}>{value}</p>

        {!delta && sub && <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>{sub}</p>}

        {/* Sparkline */}
        {showSpark && (
          <div className="mt-2 -mx-1">
            <ResponsiveContainer width="100%" height={36}>
              <AreaChart
                data={sparkline!.map((v, i) => ({ v, i }))}
                margin={{ top: 2, right: 0, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id={sparkId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={sparkHex} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={sparkHex} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={sparkHex}
                  strokeWidth={2}
                  fill={`url(#${sparkId})`}
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Expand toggle */}
        {clickable && (
          <div className="flex items-center gap-1 mt-2">
            {expanded
              ? <ChevronUp className="w-3 h-3" style={{ color: "var(--muted)" }} />
              : <ChevronDown className="w-3 h-3" style={{ color: "var(--muted)" }} />}
            <span className="text-[10px]" style={{ color: "var(--muted)" }}>
              {expanded ? "Hide" : "See details"}
            </span>
          </div>
        )}
      </div>

      {expanded && (
        <div
          className="px-4 pb-4 border-t"
          style={{ borderColor: "var(--border)", background: "rgba(0,0,0,.25)" }}
        >
          <p className="text-xs leading-relaxed mt-3" style={{ color: "var(--text-2)" }}>
            {insight}
          </p>
          {actionLabel && (
            <button
              onClick={(e) => { e.stopPropagation(); onAction?.(); }}
              className="mt-3 flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all"
              style={
                locked
                  ? { background: "rgba(255,255,255,.04)", color: "var(--muted)", border: "1px solid var(--border)" }
                  : { background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)" }
              }
            >
              {locked && <Lock className="w-3 h-3" />}
              {actionLabel}
              {locked && (
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded-full ml-0.5"
                  style={{ background: "rgba(255,178,36,.15)", color: "var(--accent)" }}
                >
                  Pro
                </span>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Positioning bar ───────────────────────────────────────────────────────────
function positioningDescription(label: string, score: number): string {
  switch (label) {
    case "Market Position":
      return score < 34 ? "Budget-focused — price is their primary lever."
           : score < 67 ? "Mid-market — competes on value and quality."
           :               "Premium — margin-focused, aspirational positioning.";
    case "Promo Intensity":
      return score < 34 ? "Rarely discounts — full-price brand."
           : score < 67 ? "Selective discounting — strategic promotions."
           :               "Heavy discounter — frequent sales and markdowns.";
    case "Launch Velocity":
      return score < 34 ? "Slow launches — stable, focused catalog."
           : score < 67 ? "Steady launch pace — measured expansion."
           :               "Aggressive expansion — launching frequently.";
    case "Catalog Complexity":
      return score < 34 ? "Focused catalog — tight product range."
           : score < 67 ? "Moderate variety — several categories."
           :               "Very broad catalog — many categories and variants.";
    default: return "";
  }
}

function PositioningBar({ label, score, scoreLabel }: { label: string; score: number; scoreLabel: string }) {
  const color = "#A8AC9E";
  const desc  = positioningDescription(label, score);
  return (
    <div
      className="rounded-md p-4"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>{label}</span>
        <span className="text-xs font-semibold" style={{ color }}>{scoreLabel}</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden mb-2" style={{ background: "var(--bg3)" }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
      {desc && <p className="text-[11px] leading-snug" style={{ color: "var(--muted)" }}>{desc}</p>}
    </div>
  );
}

// ── Top alert banner ──────────────────────────────────────────────────────────
// ── Change row ────────────────────────────────────────────────────────────────
function ChangeRow({ change, hostname, competitorId }: { change: ChangeEvent; hostname?: string; competitorId?: string }) {
  const Icon    = changeTypeIcon(change.change_type);
  const color   = changeTypeColor(change.change_type);
  const label   = changeTypeLabel(change.change_type);
  const old_v = change.old_value || {};
  const new_v = change.new_value || {};
  let detail  = "";
  if (change.change_type === "price_change" && change.delta_pct != null) {
    detail = `${formatPrice(old_v.price as number)} → ${formatPrice(new_v.price as number)} (${formatDelta(change.delta_pct)})`;
  } else if (change.change_type === "new_product") {
    detail = new_v.price_min ? `from ${formatPrice(new_v.price_min as number)}` : "added to catalog";
  } else if (change.change_type === "discount_start") {
    const pct = new_v.discounted_pct as number;
    detail = pct ? `${formatPct(pct)} of catalog on sale` : "";
  } else if (change.change_type === "discount_end") {
    const pct = old_v.discounted_pct as number;
    detail = pct ? `${formatPct(pct)} back to full price` : "";
  } else if (change.change_type === "product_removed") {
    detail = "removed from catalog";
  } else if (change.change_type === "availability_change") {
    const inStock = new_v.available as boolean;
    detail = inStock === false ? "went out of stock" : inStock === true ? "back in stock" : "";
  }
  const borderColor =
    change.severity === "critical" ? "var(--red)" :
    change.severity === "warning"  ? "var(--amber)" : "transparent";

  const action = getChangeAction(change.change_type, change.delta_pct, change.severity, hostname);

  return (
    <div
      className="flex items-start gap-3 py-3 pl-3 border-b last:border-0"
      style={{ borderColor: "var(--border)", borderLeft: `3px solid ${borderColor}`, marginLeft: "-1px" }}
    >
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
        style={{ background: `color-mix(in srgb, ${color} 12%, transparent)` }}
      >
        <Icon className="w-3.5 h-3.5" style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold" style={{ color }}>{label}</span>
          {change.product_title && (
            <span className="text-xs truncate" style={{ color: "var(--text-2)" }}>· {change.product_title}</span>
          )}
        </div>
        {detail && (
          <p className="text-[11px] mt-0.5" style={{ color: "var(--muted)" }}>{detail}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {action && competitorId && (
          <SaveToPlaybook
            size="xs"
            item={{
              source_type: "signal",
              source_ref: change.id,
              competitor_id: competitorId,
              hostname,
              title: action,
              reason: `${label}${change.product_title ? ` — ${change.product_title}` : ""} on ${hostname}`,
              evidence: detail || label,
              priority: change.severity === "critical" ? "high" : change.severity === "warning" ? "medium" : "low",
            }}
          />
        )}
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          {formatRelativeTime(change.detected_at)}
        </p>
      </div>
    </div>
  );
}

// ── Pro gate wrapper ──────────────────────────────────────────────────────────
function ProGate({ children, onUpgrade, label = "Unlock with Pro" }: {
  children: React.ReactNode; onUpgrade: () => void; label?: string;
}) {
  return (
    <div className="relative">
      <div className="blur-sm pointer-events-none select-none opacity-60">{children}</div>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div
          className="flex flex-col items-center gap-3 px-6 py-5 rounded-md text-center"
          style={{ background: "rgba(10,10,15,.85)", border: "1px solid rgba(255,178,36,.2)", backdropFilter: "blur(8px)" }}
        >
          <Lock className="w-5 h-5" style={{ color: "var(--accent)" }} />
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>{label}</p>
          <button
            onClick={onUpgrade}
            className="text-xs font-bold px-4 py-2 rounded-md transition-all hover:brightness-110"
            style={{ background: "var(--accent)", color: "var(--ink)" }}
          >
            <Zap className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" />
            Upgrade to Pro — $29/mo
          </button>
        </div>
      </div>
    </div>
  );
}

// ── AI summary parser ─────────────────────────────────────────────────────────
type BriefCardParsed = { type: string; headline: string; body: string };
function parseSummaryText(text: string): { type: "cards"; cards: BriefCardParsed[] } | { type: "text"; text: string } {
  try {
    const parsed = JSON.parse(text) as { cards?: BriefCardParsed[] };
    if (parsed.cards && Array.isArray(parsed.cards)) return { type: "cards", cards: parsed.cards };
  } catch {}
  return { type: "text", text };
}

function parseProAnalysis(text: string): ProAnalysisData | null {
  try {
    const parsed = JSON.parse(text) as ProAnalysisData;
    if (parsed && typeof parsed === "object" && (parsed.threat || parsed.predictions || parsed.impact)) return parsed;
  } catch {}
  return null;
}

// ── Scout Brief digest (free) ─────────────────────────────────────────────────
// The free brief answers "what happened?" in under 30 seconds: threat level,
// factual highlights, one move. The deep "what does it mean for MY business?"
// analysis lives in Intelligence Pro — a different product, not a longer brief.

const DIGEST_THREAT: Record<string, { color: string; label: string }> = {
  high:   { color: "#F2555A", label: "High threat" },
  medium: { color: "#FFB224", label: "Medium threat" },
  low:    { color: "#4CC38A", label: "Low threat" },
};

// The dossier's lead: an executive briefing, not a summary. One panel that
// answers "what is this business doing right now?" — threat verdict, the
// facts behind it, the biggest opening, the biggest risk, and your move.
function ExecutiveBriefing({
  hostname, briefText, changes, fallbackHighlights, onOpenPro, isFree, competitorId, gapsTotal,
}: {
  hostname: string;
  briefText: string;
  changes: ChangeEvent[];
  fallbackHighlights: string[];
  onOpenPro: () => void;
  isFree: boolean;
  competitorId: string;
  gapsTotal?: number;
}) {
  let threatLevel: string | undefined;
  let highlights: string[] = [];
  let oneMove: string | undefined;
  let opportunity: { headline: string } | undefined;
  try {
    const parsed = JSON.parse(briefText) as {
      threat_level?: string; highlights?: string[]; one_move?: string;
      cards?: BriefCardParsed[];
    };
    threatLevel = parsed.threat_level?.toLowerCase();
    highlights = Array.isArray(parsed.highlights) ? parsed.highlights.slice(0, 4) : [];
    oneMove = parsed.one_move
      // Older briefs pre-date the digest fields — fall back to the action card
      || parsed.cards?.find((c) => c.type === "action")?.headline;
    const opp = parsed.cards?.find((c) => c.type === "opportunity");
    if (opp) opportunity = { headline: opp.headline };
  } catch { /* fall back below */ }

  // Biggest risk: the most severe strategic change of the last 7 days — real
  // detection output, never invented.
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const recent = changes.filter((c) => new Date(c.detected_at).getTime() > weekAgo);
  const riskEvent =
    recent.find((c) => c.severity === "critical") ?? recent.find((c) => c.severity === "warning");
  const risk = riskEvent
    ? `${changeTypeLabel(riskEvent.change_type)}${riskEvent.product_title ? ` — ${riskEvent.product_title}` : ""}`
    : null;

  if (!threatLevel) {
    // Heuristic from real signal severity — truthful, no AI needed
    threatLevel = recent.some((c) => c.severity === "critical") ? "high"
      : recent.some((c) => c.severity === "warning") ? "medium" : "low";
  }
  if (highlights.length === 0) highlights = fallbackHighlights;
  const threat = DIGEST_THREAT[threatLevel] ?? DIGEST_THREAT.low;

  return (
    <div
      className="mb-6 rounded-md p-4"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: `3px solid ${threat.color}` }}
    >
      <div className="flex items-center gap-2.5 flex-wrap">
        <span className="label-caps" style={{ color: "var(--muted)" }}>Executive briefing · {hostname}</span>
        <span
          className="text-[11px] font-bold px-2 py-0.5 rounded"
          style={{ background: `${threat.color}14`, color: threat.color, border: `1px solid ${threat.color}33` }}
        >
          {threat.label}
        </span>
        <span className="num text-[10px] ml-auto shrink-0" style={{ color: "var(--muted)" }}>
          {recent.length} change{recent.length === 1 ? "" : "s"} · 7d
        </span>
      </div>

      {/* Factual highlights — scannable in seconds */}
      <div className="flex items-center gap-x-4 gap-y-1 flex-wrap mt-2.5">
        {highlights.map((h, i) => (
          <span key={i} className="num text-xs" style={{ color: "var(--text-2)" }}>{h}</span>
        ))}
      </div>

      {/* Opening · Risk — the two things an executive asks about first */}
      <div className="grid sm:grid-cols-2 gap-2.5 mt-3">
        <div className="rounded px-3 py-2" style={{ background: "var(--bg3)", borderLeft: "2px solid #4CC38A" }}>
          <p className="label-caps mb-0.5" style={{ color: "#4CC38A" }}>Biggest opening</p>
          <p className="text-xs leading-snug" style={{ color: "var(--text-2)" }}>
            {opportunity?.headline
              ?? (gapsTotal ? `${gapsTotal} market opening${gapsTotal === 1 ? "" : "s"} detected — see Catalog · Openings` : "No clear opening yet — this sharpens with scan history")}
          </p>
        </div>
        <div className="rounded px-3 py-2" style={{ background: "var(--bg3)", borderLeft: `2px solid ${risk ? "#F2555A" : "var(--border)"}` }}>
          <p className="label-caps mb-0.5" style={{ color: risk ? "#F2555A" : "var(--muted)" }}>Biggest risk</p>
          <p className="text-xs leading-snug" style={{ color: "var(--text-2)" }}>
            {risk ?? "No active threats this week — steady state"}
          </p>
        </div>
      </div>

      {oneMove && (
        <div className="flex items-start justify-between gap-3 mt-3">
          <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>
            <Zap className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5" style={{ color: "var(--accent)" }} />
            {oneMove}
          </p>
          <SaveToPlaybook
            size="xs"
            item={{
              source_type: "brief",
              source_ref: competitorId,
              competitor_id: competitorId,
              hostname,
              title: oneMove,
              reason: `Executive briefing move for ${hostname}`,
              evidence: highlights.slice(0, 4).join(" · "),
              priority: threatLevel === "high" ? "high" : "medium",
            }}
          />
        </div>
      )}

      <button
        onClick={onOpenPro}
        className="mt-3 text-xs font-semibold flex items-center gap-1 transition-colors hover:brightness-125"
        style={{ color: "var(--accent)" }}
      >
        {isFree ? "What does this mean for your business? Unlock Intelligence Pro →" : "Full strategist analysis → Intelligence Pro"}
      </button>
    </div>
  );
}

// ── Tab bar ───────────────────────────────────────────────────────────────────
function TabBar<T extends string>({
  tabs, active, onChange, size = "md",
}: {
  tabs: { id: T; label: string; icon?: React.ReactNode; pro?: boolean }[];
  active: T;
  onChange: (t: T) => void;
  size?: "sm" | "md";
}) {
  return (
    <div className="flex gap-0 overflow-x-auto border-b" style={{ borderColor: "var(--border)" }}>
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={cn(
            "relative flex items-center gap-1.5 whitespace-nowrap transition-colors",
            size === "sm" ? "px-3 py-2 text-xs" : "px-4 py-2.5 text-sm",
            "font-medium"
          )}
          style={{ color: active === t.id ? "var(--accent)" : "var(--muted)" }}
        >
          {t.icon && <span className="opacity-70">{t.icon}</span>}
          {t.label}
          {t.pro && (
            <span
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
              style={{ background: "rgba(255,178,36,.12)", color: "var(--accent)" }}
            >
              PRO
            </span>
          )}
          {active === t.id && (
            <span
              className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full"
              style={{ background: "var(--accent)" }}
            />
          )}
        </button>
      ))}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function CompetitorDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id }       = use(params);
  const router       = useRouter();
  const searchParams = useSearchParams();

  function resolveInitialTab(): Tab {
    const raw = searchParams.get("tab");
    const valid: Tab[] = ["overview", "catalog", "pricing", "changes", "intelligence"];
    return valid.includes(raw as Tab) ? (raw as Tab) : "overview";
  }

  function resolveInitialCatalogSub(): CatalogSub {
    const raw = searchParams.get("catalogSub");
    return raw === "gaps" ? "gaps" : "winning";
  }

  function resolveInitialIntelSub(): IntelSub {
    const raw = searchParams.get("intelSub");
    return (["ai", "brand", "compare"] as IntelSub[]).includes(raw as IntelSub)
      ? (raw as IntelSub)
      : "ai";
  }

  const [competitor,     setCompetitor]     = useState<import("@/lib/api").Competitor | null>(null);
  const [snapshot,       setSnapshot]       = useState<Snapshot | null>(null);
  const [changes,        setChanges]        = useState<ChangeEvent[]>([]);
  const [aiSummary,      setAiSummary]      = useState<AiSummary | null>(null);
  const [aiStatus,       setAiStatus]       = useState<"idle" | "loading" | "generating" | "error" | "none">("idle");
  const aiPollRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const aiPollCount  = useRef(0);
  const [loading,        setLoading]        = useState(true);
  const [prevMeta,       setPrevMeta]       = useState<SnapshotMeta | null>(null);
  const [tab,            setTab]            = useState<Tab>(resolveInitialTab);
  const [catalogSub,     setCatalogSub]     = useState<CatalogSub>(resolveInitialCatalogSub);
  const [intelSub,       setIntelSub]       = useState<IntelSub>(resolveInitialIntelSub);
  const [rescanning,     setRescanning]     = useState(false);
  const [scanPending,    setScanPending]    = useState(true);
  const [brief,          setBrief]          = useState<BriefData | null | false>(null);
  const [aiRefreshing,   setAiRefreshing]   = useState(false);
  const [copied,         setCopied]         = useState(false);
  const [exporting,      setExporting]      = useState(false);
  const [upgradeOpen,    setUpgradeOpen]    = useState(false);
  const [tier,           setTier]           = useState<string>("free");
  const [showAllChanges, setShowAllChanges] = useState(false);
  const [priceHistory,   setPriceHistory]   = useState<PriceHistoryPoint[]>([]);

  const isFree = tier === "free";

  // Load competitor record for hostname/display_name before the first snapshot exists
  useEffect(() => {
    api.get(id).then((r) => setCompetitor(r.data)).catch(() => {});
  }, [id]);

  useEffect(() => {
    async function load() {
      try {
        const snapRes = await api.latestSnapshot(id);
        setSnapshot(snapRes.data);
        setScanPending(false);
      } catch { /* scan pending */ }
      try {
        const changesRes = await api.changes(id, 50);
        setChanges(changesRes.data);
      } catch { /* non-fatal */ }
      setLoading(false);
      userApi.subscription().then((r) => setTier(r.data.tier)).catch(() => {});
    }
    load();
    const interval = setInterval(load, scanPending ? 3000 : 15000);
    return () => clearInterval(interval);
  }, [id, scanPending]);

  // Fetch previous snapshot meta for trend deltas (once per page load)
  useEffect(() => {
    if (!snapshot) return;
    api.snapshots(id, 2)
      .then((r) => { if (r.data.length >= 2) setPrevMeta(r.data[1]); })
      .catch(() => {});
  }, [id, snapshot?.id]);

  // Fetch price history for KPI sparklines (Pro: up to 90 days; free: 2 points)
  useEffect(() => {
    api.priceHistory(id)
      .then((r) => setPriceHistory(r.data.points))
      .catch(() => {});
  }, [id]);

  // Fetch AI summary when landing on the AI insights sub-tab
  useEffect(() => {
    if (tab !== "intelligence" || intelSub !== "ai" || isFree || aiStatus !== "idle" || aiSummary) return;
    setAiStatus("loading");
    api.aiSummary(id)
      .then((r) => {
        if (r.status === "generating") {
          setAiStatus("generating");
        } else if (r.data) {
          setAiSummary(r.data);
          setAiRefreshing(r.status === "refreshing");
          setAiStatus("idle");
        } else {
          // No summary generated yet — not an error, just hasn't been run
          setAiStatus("none");
        }
      })
      .catch(() => setAiStatus("error"));
  }, [tab, intelSub, isFree, id, aiStatus]);

  // Poll every 8 s while Claude is generating; give up after 15 attempts (~2 min)
  useEffect(() => {
    if (aiStatus !== "generating") {
      if (aiPollRef.current) clearInterval(aiPollRef.current);
      aiPollCount.current = 0;
      return;
    }
    aiPollCount.current = 0;
    aiPollRef.current = setInterval(async () => {
      aiPollCount.current += 1;
      if (aiPollCount.current > 15) {
        setAiStatus("error");
        clearInterval(aiPollRef.current!);
        return;
      }
      try {
        const r = await api.aiSummary(id);
        if (r.status !== "generating" && r.data) {
          setAiSummary(r.data);
          setAiStatus("idle");
        }
      } catch { /* keep polling */ }
    }, 8000);
    return () => { if (aiPollRef.current) clearInterval(aiPollRef.current); };
  }, [aiStatus, id]);

  useEffect(() => {
    if (scanPending || brief !== null) return;
    let cancelled = false;
    let attempts  = 0;
    const tryFetch = async () => {
      if (cancelled || attempts >= 12) { if (!cancelled) setBrief(false); return; }
      attempts++;
      try {
        const r     = await api.brief(id);
        if (cancelled) return;
        setBrief(r.data);
      } catch (e: unknown) {
        const status = (e as { status?: number })?.status;
        if (status === 404 && !cancelled) setTimeout(tryFetch, 5000);
        else if (!cancelled) setBrief(false);
      }
    };
    tryFetch();
    return () => { cancelled = true; };
  }, [id, scanPending, brief]);

  const isScanning = competitor?.scan_status === "scanning" || competitor?.scan_status === "pending";

  // Clear queued state once the scan actually picks up
  useEffect(() => {
    if (isScanning) setRescanning(false);
  }, [isScanning]);

  async function handleRescan() {
    setRescanning(true);
    await api.rescan(id).catch(() => { setRescanning(false); });
  }


  function handleShare() {
    if (!snapshot) return;
    navigator.clipboard.writeText(`${window.location.origin}/reports/${snapshot.id}`).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleExportCsv() {
    setExporting(true);
    try {
      const supabase = createClient();
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      const res = await fetch(`/api/v1/competitors/${id}/export/products.csv`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.status === 403) { setUpgradeOpen(true); return; }
      if (!res.ok) return;
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `${hostname.replace(/\./g, "_")}_products.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  async function handleRegenerate() {
    if (aiPollRef.current) clearInterval(aiPollRef.current);
    setAiSummary(null);
    setAiStatus("generating");
    aiPollCount.current = 0;
    await api.regenerateSummary(id).catch(() => {});
  }

  async function handleDelete() {
    if (!confirm("Remove this competitor? All history will be deleted.")) return;
    await api.remove(id).catch(() => {});
    router.push("/dashboard");
  }

  const data        = snapshot?.snapshot_data as Record<string, unknown> | undefined;
  const catalog     = (data?.catalog     || {}) as Record<string, unknown>;
  const pricing     = (data?.pricing     || {}) as Record<string, unknown>;
  const discounts   = (data?.discounts   || {}) as Record<string, unknown>;
  const positioning = (data?.positioning || {}) as Record<string, unknown>;
  const launch      = (data?.launch_timeline || {}) as Record<string, unknown>;

  // KPI trend deltas vs previous scan
  function kpiDelta(curr: number | null | undefined, prev: number | null | undefined, fmt: (n: number) => string): { label: string; up: boolean | null } | undefined {
    if (curr == null || prev == null || curr === prev) return undefined;
    const diff = curr - prev;
    const sign = diff > 0 ? "▲ +" : "▼ ";
    return { label: `${sign}${fmt(Math.abs(diff))} vs last scan`, up: diff > 0 ? true : false };
  }
  const deltaProd   = kpiDelta(snapshot?.product_count, prevMeta?.product_count, (n) => n.toLocaleString());
  const deltaPrice  = kpiDelta(snapshot?.median_price,  prevMeta?.median_price,  formatPrice);
  const deltaPromo  = kpiDelta(snapshot?.promo_rate,    prevMeta?.promo_rate,    formatPct);
  const deltaNew30d = kpiDelta(snapshot?.new_30d,       prevMeta?.new_30d,       (n) => n.toLocaleString());

  // Sparkline arrays from price history (oldest → newest)
  const sparkProducts = priceHistory.map((p) => p.product_count ?? 0);
  const sparkPrice    = priceHistory.map((p) => p.median_price ?? 0);
  const sparkPromo    = priceHistory.map((p) => (p.promo_rate ?? 0) * 100);

  // Top critical/warning change for the alert banner
  const topAlert = changes.find((c) => c.severity === "critical" || c.severity === "warning");
  const takeaways   = (data?.takeaways   || []) as string[];
  const hostname    = (data?.hostname as string) || competitor?.display_name || competitor?.hostname || id;

  const MAIN_TABS: { id: Tab; label: string; icon: React.ReactNode; pro?: boolean }[] = [
    { id: "overview",      label: "Overview",      icon: <TrendingUp className="w-3.5 h-3.5" /> },
    { id: "catalog",       label: "Catalog",        icon: <Package className="w-3.5 h-3.5" /> },
    { id: "pricing",       label: "Pricing",        icon: <Tag className="w-3.5 h-3.5" /> },
    { id: "changes",       label: "Changes",        icon: <Clock className="w-3.5 h-3.5" />, },
    { id: "intelligence",  label: "Intelligence",   icon: <Brain className="w-3.5 h-3.5" />, pro: true },
  ];

  const CATALOG_TABS: { id: CatalogSub; label: string }[] = [
    { id: "winning", label: "Product Intelligence" },
    { id: "gaps",    label: "Market Openings" },
  ];

  const INTEL_TABS: { id: IntelSub; label: string }[] = [
    { id: "ai",      label: "Scout Brief" },
    { id: "brand",   label: "Brand Intel" },
    { id: "compare", label: "vs You" },
  ];

  // Changes visibility
  const FREE_CHANGES_LIMIT = 5;
  const visibleChanges = isFree && !showAllChanges ? changes.slice(0, FREE_CHANGES_LIMIT) : changes;
  const hiddenCount    = isFree ? Math.max(0, changes.length - FREE_CHANGES_LIMIT) : 0;

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-48 rounded-md" style={{ background: "var(--bg-card)" }} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-28 rounded-md" style={{ background: "var(--bg-card)" }} />)}
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div
        className="-mx-4 sm:-mx-6 px-4 sm:px-6 pt-6 pb-5 mb-6 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(236,238,230,.04) 0%, transparent 60%)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs font-medium mb-4 hover:opacity-80 transition-opacity"
          style={{ color: "var(--muted)" }}
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          All competitors
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="tick-label mb-1.5">Target dossier</p>
            <h1 className="num text-xl font-bold truncate tracking-tight" style={{ color: "var(--text)" }}>
              {hostname}
            </h1>
            {snapshot && (
              <p className="text-sm mt-1.5" style={{ color: "var(--muted)" }}>
                Last scanned {formatRelativeTime(snapshot.scanned_at)}
                {snapshot.product_count != null && ` · ${snapshot.product_count.toLocaleString()} products`}
                {changes.length > 0 && ` · ${changes.length} change${changes.length !== 1 ? "s" : ""} detected`}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {snapshot && (
              <button
                onClick={handleShare}
                className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06]"
                style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
              >
                {copied ? <Check className="w-3.5 h-3.5" style={{ color: "var(--emerald)" }} /> : <Share2 className="w-3.5 h-3.5" />}
                {copied ? "Copied" : "Share"}
              </button>
            )}
            <button
              onClick={handleExportCsv}
              disabled={exporting}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-md transition-all hover:bg-white/[0.06] disabled:opacity-50"
              style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
            >
              <Download className="w-3.5 h-3.5" />
              {exporting ? "…" : "CSV"}
            </button>
            <button
              onClick={handleRescan}
              disabled={rescanning || isScanning}
              className="flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-md transition-all hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: "rgba(255,178,36,.1)", color: "var(--accent)", border: "1px solid rgba(255,178,36,.2)" }}
            >
              <RefreshCw className={cn("w-3.5 h-3.5", (rescanning || isScanning) && "animate-spin")} />
              {isScanning ? "Scanning…" : rescanning ? "Queued…" : "Rescan"}
            </button>
            <button
              onClick={handleDelete}
              className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-md transition-all hover:bg-red-500/10"
              style={{ color: "var(--red)", border: "1px solid rgba(242,85,90,.25)" }}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* ── No snapshot yet ───────────────────────────────────────────────── */}
      {!snapshot ? (
        competitor?.scan_status === "error" ? (
          <div
            className="rounded-md p-8 text-center space-y-3"
            style={{ background: "var(--bg-card)", border: "1px solid rgba(242,85,90,.25)" }}
          >
            <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>Scan failed</p>
            <p className="text-xs max-w-xs mx-auto" style={{ color: "var(--muted)" }}>
              {competitor.error_message || "We couldn't reach this store. It may be offline or blocking our scanner."}
            </p>
            <button
              onClick={handleRescan}
              disabled={rescanning || isScanning}
              className="text-xs font-bold px-4 py-2 rounded-md transition-all hover:brightness-110 disabled:opacity-50"
              style={{ background: "rgba(255,178,36,.1)", color: "var(--accent)", border: "1px solid rgba(255,178,36,.2)" }}
            >
              {rescanning ? "Queued…" : "Try again"}
            </button>
          </div>
        ) : (
          <div
            className="rounded-md p-10 text-center space-y-4 analyzing-sweep"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-center gap-2 mx-auto">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full animate-bounce"
                  style={{ background: "var(--accent)", animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
            <div>
              <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>
                Scanning {hostname}…
              </p>
              <p className="text-xs" style={{ color: "var(--muted)" }}>
                We&apos;re pulling their full catalog. Usually takes 20–60 seconds.
              </p>
            </div>
          </div>
        )

      ) : (
        <>
          {/* ── Scout Brief — 30-second "what happened" digest (free) ──────── */}
          {brief && (
            <ExecutiveBriefing
              hostname={hostname}
              gapsTotal={((data?.gap_analysis as Record<string, unknown> | undefined)?.total as number | undefined)}
              briefText={(brief as BriefData).summary_text}
              changes={changes}
              fallbackHighlights={[
                catalog.total_products != null ? `${(catalog.total_products as number).toLocaleString()} products` : "",
                pricing.median != null ? `median ${formatPrice(pricing.median as number)}` : "",
                discounts.discounted_pct != null ? `${formatPct(discounts.discounted_pct as number)} discounted` : "",
                `${(launch as Record<string, Record<string, Record<string, number>>>)?.launch_counts?.["30d"]?.count ?? 0} launches · 30d`,
              ].filter(Boolean)}
              isFree={isFree}
              competitorId={id}
              onOpenPro={() => {
                if (isFree) { setUpgradeOpen(true); return; }
                setTab("intelligence");
                setIntelSub("ai");
              }}
            />
          )}

          {/* ── Tab navigation ────────────────────────────────────────────── */}
          <TabBar tabs={MAIN_TABS} active={tab} onChange={setTab} />

          <div className="mt-6">

            {/* ══════════════════════════════════════════════════════════════
                OVERVIEW
            ══════════════════════════════════════════════════════════════ */}
            {tab === "overview" && (
              <div className="space-y-6 fade-up">

                {/* KPI cards with trend deltas */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <KpiCard
                    label="Products"
                    value={(catalog.total_products as number)?.toLocaleString() ?? "—"}
                    delta={deltaProd}
                    insight={`This store has ${(catalog.total_products as number)?.toLocaleString() ?? "an unknown number of"} active products. Compare this to your own catalog size to gauge competitive breadth.`}
                    actionLabel="Alert me when count changes"
                    onAction={() => isFree ? setUpgradeOpen(true) : router.push("/settings#notifications")}
                    locked={isFree}
                  />
                  <KpiCard
                    label="Median Price"
                    value={formatPrice(pricing.median as number)}
                    delta={deltaPrice}
                    sparkline={sparkPrice}
                    insight={`Their median price is ${formatPrice(pricing.median as number)}, ranging from ${formatPrice(pricing.min as number)} to ${formatPrice(pricing.max as number)}. This positions them in the ${(positioning.market_position as Record<string, unknown>)?.label ?? "mid-market"} segment.`}
                    actionLabel="See 90-day price history"
                    onAction={() => { if (isFree) setUpgradeOpen(true); else setTab("pricing"); }}
                    locked={isFree}
                  />
                  <KpiCard
                    label="Promo Rate"
                    value={formatPct(discounts.discounted_pct as number)}
                    delta={deltaPromo}
                    sparkline={sparkPromo}
                    insight={`${formatPct(discounts.discounted_pct as number)} of their catalog is currently discounted — average discount depth is ${formatPct(discounts.avg_discount_pct as number)}. A high promo rate can signal pricing pressure or clearance cycles.`}
                    actionLabel="Alert me on flash sales"
                    onAction={() => isFree ? setUpgradeOpen(true) : router.push("/settings#notifications")}
                    locked={isFree}
                  />
                  <KpiCard
                    label="New (30d)"
                    value={((launch as Record<string, Record<string, Record<string, number>>>)?.launch_counts?.["30d"]?.count ?? "—").toString()}
                    delta={deltaNew30d}
                    insight={`They launched ${((launch as Record<string, Record<string, Record<string, number>>>)?.launch_counts?.["30d"]?.count ?? 0)} products in the last 30 days. A high velocity often signals an aggressive growth phase or seasonal push.`}
                    actionLabel="Alert me when they launch"
                    onAction={() => isFree ? setUpgradeOpen(true) : router.push("/settings#notifications")}
                    locked={isFree}
                  />
                </div>

                {/* Recent changes — moved up, most time-sensitive after KPIs */}
                {changes.length > 0 && (
                  <div className="rounded-md overflow-hidden" style={{ border: "1px solid var(--border)" }}>
                    <div
                      className="flex items-center justify-between px-5 py-3.5"
                      style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}
                    >
                      <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Latest Signals</h3>
                      <button
                        onClick={() => setTab("changes")}
                        className="text-xs font-medium hover:underline"
                        style={{ color: "var(--text-2)" }}
                      >
                        View all {changes.length} →
                      </button>
                    </div>
                    {topAlert && (() => {
                      const action = getChangeAction(topAlert.change_type, topAlert.delta_pct, topAlert.severity, hostname);
                      return action ? (
                        <div className="px-5 py-3" style={{ background: "rgba(255,178,36,.05)", borderBottom: "1px solid var(--border)" }}>
                          <p className="tick-label tick-label--live mb-1">Your move</p>
                          <p className="text-xs leading-relaxed" style={{ color: "var(--text-2)" }}>{action}</p>
                        </div>
                      ) : null;
                    })()}
                    <div className="px-5" style={{ background: "var(--bg-card)" }}>
                      {changes.slice(0, 4).map((c) => <ChangeRow key={c.id} change={c} hostname={hostname} competitorId={id} />)}
                    </div>
                  </div>
                )}

                {/* Quick wins */}
                <QuickWins competitorId={id} />

                {/* Competitive positioning bars */}
                {[positioning.market_position, positioning.promo_intensity, positioning.launch_velocity, positioning.catalog_complexity].some(Boolean) && (
                  <div>
                    <p className="tick-label mb-3" style={{ color: "var(--muted)" }}>
                      Competitive positioning
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { label: "Market Position",    pos: positioning.market_position    as Record<string, unknown> },
                        { label: "Promo Intensity",    pos: positioning.promo_intensity    as Record<string, unknown> },
                        { label: "Launch Velocity",    pos: positioning.launch_velocity    as Record<string, unknown> },
                        { label: "Catalog Complexity", pos: positioning.catalog_complexity as Record<string, unknown> },
                      ].map(({ label, pos }) => pos ? (
                        <PositioningBar
                          key={label}
                          label={label}
                          score={(pos.score as number) ?? 50}
                          scoreLabel={(pos.label as string) ?? "—"}
                        />
                      ) : null)}
                    </div>
                  </div>
                )}

                {/* Key insights */}
                {takeaways.length > 0 && (
                  <div
                    className="rounded-md p-5"
                    style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                  >
                    <div className="flex items-center gap-2 mb-4">
                      <Sparkles className="w-4 h-4" style={{ color: "var(--text-2)" }} />
                      <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>What This Means</h3>
                    </div>
                    <ul className="space-y-3">
                      {takeaways.map((t, i) => (
                        <li key={i} className="flex items-start gap-3 text-sm leading-snug" style={{ color: "var(--text-2)" }}>
                          <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ background: "var(--muted)" }} />
                          {t}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Integration nudge */}
                <Link
                  href="/settings?tab=integrations"
                  className="flex items-center gap-3 px-4 py-3 rounded-md transition-all hover:bg-white/[0.03]"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                >
                  <div className="w-8 h-8 rounded flex items-center justify-center shrink-0" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
                    <Zap className="w-4 h-4" style={{ color: "var(--text-2)" }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold" style={{ color: "var(--text)" }}>Connect Shopify, GA4, or Klaviyo</p>
                    <p className="text-xs" style={{ color: "var(--muted)" }}>Playbook recommendations become personalized to your actual store data</p>
                  </div>
                  <span className="text-xs font-semibold shrink-0" style={{ color: "var(--text-2)" }}>Set up →</span>
                </Link>

                {/* Watched products for this competitor */}
                <WatchlistPanel competitorId={id} />
              </div>
            )}

            {/* ══════════════════════════════════════════════════════════════
                CATALOG
            ══════════════════════════════════════════════════════════════ */}
            {tab === "catalog" && (
              <div className="space-y-5 fade-up">
                <TabBar tabs={CATALOG_TABS} active={catalogSub} onChange={setCatalogSub} size="sm" />
                <div className="pt-1">
                  {catalogSub === "winning" && <WinningProductsTab competitorId={id} />}
                  {catalogSub === "gaps"    && <GapsTab competitorId={id} />}
                </div>
              </div>
            )}

            {/* ══════════════════════════════════════════════════════════════
                PRICING
            ══════════════════════════════════════════════════════════════ */}
            {tab === "pricing" && (
              <div className="space-y-6 fade-up">
                {/* Stats row */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {([
                    ["Min",    formatPrice(pricing.min    as number)],
                    ["P25",    formatPrice(pricing.p25    as number)],
                    ["Median", formatPrice(pricing.median as number)],
                    ["P75",    formatPrice(pricing.p75    as number)],
                    ["Max",    formatPrice(pricing.max    as number)],
                  ] as [string, string][]).map(([label, value]) => (
                    <KpiCard key={label} label={label} value={value} />
                  ))}
                </div>

                {/* Distribution chart */}
                <PriceDistributionChart pricingData={pricing} />

                {/* Discounts section */}
                <div
                  className="rounded-md p-5"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                >
                  <div className="flex items-center gap-2 mb-4">
                    <Tag className="w-4 h-4" style={{ color: "var(--text-2)" }} />
                    <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Discount activity</h3>
                  </div>
                  <div className="flex flex-col sm:flex-row items-center gap-6">
                    {/* Gauge */}
                    <div className="shrink-0 relative w-32 h-20">
                      {(() => {
                        const pct  = Math.min(100, Math.max(0, (discounts.discounted_pct as number) || 0));
                        const r    = 48; const cx = 64; const cy = 64;
                        const sA   = Math.PI; const eA = 2 * Math.PI;
                        const filled = sA + (eA - sA) * (pct / 100);
                        const toXY = (a: number) => ({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
                        const s    = toXY(sA); const e = toXY(eA - 0.001); const f = toXY(filled);
                        const la   = (eA - sA) * (pct / 100) > Math.PI ? 1 : 0;
                        const color = pct > 50 ? "#F2555A" : pct > 25 ? "#FFB224" : "#7DB8C9";
                        return (
                          <svg viewBox="0 0 128 70" className="w-full h-full">
                            <path d={`M ${s.x} ${s.y} A ${r} ${r} 0 1 1 ${e.x} ${e.y}`} fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="10" strokeLinecap="round" />
                            {pct > 0 && <path d={`M ${s.x} ${s.y} A ${r} ${r} 0 ${la} 1 ${f.x} ${f.y}`} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" />}
                            <text x={cx} y={cy - 2} textAnchor="middle" fontSize="20" fontWeight="bold" fill="var(--text)" fontFamily="monospace">{Math.round(pct)}%</text>
                            <text x={cx} y={cy + 16} textAnchor="middle" fontSize="9" fill="var(--muted)" fontFamily="system-ui">discounted</text>
                          </svg>
                        );
                      })()}
                    </div>
                    <div className="flex-1 space-y-3 w-full">
                      {([
                        ["Avg Discount",    formatPct(discounts.avg_discount_pct    as number)],
                        ["Median Discount", formatPct(discounts.median_discount_pct as number)],
                        ["Max Discount",    formatPct(discounts.max_discount_pct    as number)],
                      ] as [string, string][]).map(([label, value]) => (
                        <div key={label} className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--border)" }}>
                          <span className="text-sm" style={{ color: "var(--muted)" }}>{label}</span>
                          <span className="text-sm font-bold font-mono" style={{ color: "var(--text)" }}>{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Action: set discount alert */}
                  {isFree ? (
                    <button
                      onClick={() => setUpgradeOpen(true)}
                      className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 text-xs font-semibold rounded-md transition-all"
                      style={{ background: "rgba(255,255,255,.04)", color: "var(--muted)", border: "1px solid var(--border)" }}
                    >
                      <Lock className="w-3.5 h-3.5" />
                      Get alerted when they run a flash sale
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: "rgba(255,178,36,.15)", color: "var(--accent)" }}>Pro</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => router.push("/settings#notifications")}
                      className="mt-4 flex items-center gap-2 px-3 py-2 text-xs font-medium rounded transition-colors hover:bg-white/[.04]"
                      style={{ color: "var(--text-2)", border: "1px solid var(--border)" }}
                    >
                      <Bell className="w-3.5 h-3.5" />
                      Set flash sale alert
                    </button>
                  )}
                </div>

                {/* Launch velocity */}
                <div
                  className="rounded-md p-5"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                >
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingUp className="w-4 h-4" style={{ color: "var(--emerald)" }} />
                    <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Launch velocity</h3>
                  </div>
                  <LaunchVelocityChart launchData={launch} />
                </div>

                {/* Price history */}
                <div
                  className="rounded-md p-5"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                >
                  <div className="flex items-center gap-2 mb-4">
                    <Clock className="w-4 h-4" style={{ color: "var(--blue)" }} />
                    <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Price history</h3>
                    {isFree && (
                      <span
                        className="text-[10px] font-bold px-1.5 py-0.5 rounded-full ml-auto"
                        style={{ background: "rgba(255,178,36,.12)", color: "var(--accent)" }}
                      >
                        PRO
                      </span>
                    )}
                  </div>
                  <PriceHistoryChart
                    competitorId={id}
                    isFree={isFree}
                    onUpgrade={() => setUpgradeOpen(true)}
                  />
                </div>

                {/* ── What their pricing tells us — the tab's closing argument ── */}
                {(() => {
                  const promo = discounts.discounted_pct as number | undefined;
                  const med = pricing.median as number | undefined;
                  const depth = discounts.median_discount_pct as number | undefined;
                  if (promo == null && med == null) return null;
                  const strategy =
                    promo != null && promo >= 30
                      ? `They discount ${formatPct(promo)} of the catalog${depth ? ` at a median ${formatPct(depth)} off` : ""} — a promotion-led model. Their customers are being trained to wait for markdowns, which quietly erodes full-price demand.`
                      : promo != null && promo >= 10
                      ? `Selective discounting (${formatPct(promo)} of catalog) — they protect most of the range and use markdowns as a lever, not an identity.`
                      : `Almost no discounting${promo != null ? ` (${formatPct(promo)})` : ""} — a full-price brand that competes on desirability, not deals.`;
                  const move =
                    promo != null && promo >= 30
                      ? "Own the full-price lane: hold pricing, lead with quality and guarantees, and let them squeeze their own margin."
                      : promo != null && promo >= 10
                      ? "Watch which collections they mark down — those are the categories where their conviction is weakest and your entry is cheapest."
                      : `Don't start the discount fight — differentiate on range and service, or position deliberately against their ${med != null ? formatPrice(med) : ""} median.`;
                  return (
                    <div className="rounded-md p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: "3px solid var(--accent)" }}>
                      <p className="label-caps mb-1.5" style={{ color: "var(--accent)" }}>What this tells us</p>
                      <p className="text-sm leading-relaxed mb-2.5" style={{ color: "var(--text-2)" }}>{strategy}</p>
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-semibold leading-snug" style={{ color: "var(--text)" }}>→ {move}</p>
                        <SaveToPlaybook
                          size="xs"
                          item={{
                            source_type: "pricing",
                            source_ref: `${id}:pricing-strategy`,
                            competitor_id: id,
                            hostname,
                            title: move,
                            reason: strategy,
                            evidence: [
                              promo != null && `${formatPct(promo)} of catalog discounted`,
                              depth != null && `median depth ${formatPct(depth)}`,
                              med != null && `median price ${formatPrice(med)}`,
                            ].filter(Boolean).join(" · "),
                            priority: promo != null && promo >= 30 ? "high" : "medium",
                          }}
                        />
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* ══════════════════════════════════════════════════════════════
                CHANGES
            ══════════════════════════════════════════════════════════════ */}
            {tab === "changes" && (
              <div className="fade-up">
                <div
                  className="rounded-md overflow-hidden"
                  style={{ border: "1px solid var(--border)" }}
                >
                  <div
                    className="flex items-center justify-between px-5 py-3.5"
                    style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}
                  >
                    <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>
                      {changes.length} change{changes.length !== 1 ? "s" : ""} detected
                    </h3>
                    {isFree && changes.length > FREE_CHANGES_LIMIT && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: "rgba(255,178,36,.12)", color: "var(--accent)" }}>
                        PRO for full history
                      </span>
                    )}
                  </div>

                  {changes.length === 0 ? (
                    <div className="px-5 py-10 text-center space-y-6" style={{ background: "var(--bg-card)" }}>
                      <div>
                        <div className="w-10 h-10 rounded-md mx-auto mb-3 flex items-center justify-center" style={{ background: "rgba(255,255,255,.04)", border: "1px solid var(--border)" }}>
                          <Clock className="w-5 h-5" style={{ color: "var(--muted)", opacity: 0.4 }} />
                        </div>
                        <p className="text-sm font-semibold mb-1.5" style={{ color: "var(--text)" }}>No changes detected yet</p>
                        <p className="text-xs leading-relaxed max-w-xs mx-auto" style={{ color: "var(--muted)" }}>
                          We compare each scan to the previous one. Price shifts, new product launches, and removed items will appear here.
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-2 max-w-xs mx-auto">
                        {[
                          { icon: "↓", label: "Price drop",       color: "#4CC38A" },
                          { icon: "↑", label: "Price increase",   color: "#F2555A" },
                          { icon: "+", label: "New product",      color: "#2F9FC9" },
                          { icon: "✕", label: "Product removed",  color: "#6C7164" },
                        ].map(({ icon, label, color }) => (
                          <div key={label} className="flex items-center gap-2 px-3 py-2 rounded-md" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
                            <span className="text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{ background: `${color}15`, color }}>{icon}</span>
                            <span className="text-xs" style={{ color: "var(--muted)" }}>{label}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="px-5" style={{ background: "var(--bg-card)" }}>
                        {visibleChanges.map((c) => <ChangeRow key={c.id} change={c} hostname={hostname} competitorId={id} />)}
                      </div>

                      {/* Free tier gate */}
                      {isFree && hiddenCount > 0 && (
                        <div className="p-4" style={{ borderTop: "1px solid var(--border)" }}>
                          <LockedValueCard
                            title={`+${hiddenCount} more change${hiddenCount !== 1 ? "s" : ""} detected`}
                            teaser="Unlock 90-day change history and get alerts within 15 minutes of detection."
                            plan="pro"
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ══════════════════════════════════════════════════════════════
                INTELLIGENCE (Pro)
            ══════════════════════════════════════════════════════════════ */}
            {tab === "intelligence" && (
              <div className="space-y-5 fade-up">
                <TabBar tabs={INTEL_TABS} active={intelSub} onChange={setIntelSub} size="sm" />

                <div className="pt-1">
                  {/* ── AI Insights ── */}
                  {intelSub === "ai" && (
                    <div>
                      {isFree ? (
                        <div
                          className="rounded-md p-8 text-center relative overflow-hidden"
                          style={{ background: "var(--bg-card)", border: "1px solid rgba(255,178,36,.2)" }}
                        >
                          <div className="relative">
                            <div className="w-12 h-12 rounded-md mx-auto mb-4 flex items-center justify-center" style={{ background: "rgba(255,178,36,.1)", border: "1px solid rgba(255,178,36,.2)" }}>
                              <Sparkles className="w-6 h-6" style={{ color: "var(--accent)" }} />
                            </div>
                            <h3 className="text-lg font-bold mb-2" style={{ color: "var(--text)" }}>Intelligence Pro</h3>
                            <p className="text-sm mb-6 max-w-sm mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
                              Your free Scout Brief tells you what happened. Intelligence Pro is a strategist&apos;s read of {hostname}: threat score, momentum, predicted next moves with confidence, and what it all means for your business.
                            </p>
                            <div className="mb-6 text-left rounded-md p-4 space-y-2 select-none pointer-events-none" style={{ background: "var(--bg3)" }}>
                              {[
                                snapshot?.promo_rate != null
                                  ? `${(snapshot.promo_rate * 100).toFixed(1)}% of catalog is discounted — ${snapshot.promo_rate > 0.3 ? "aggressive pricing strategy" : "selective discounting"}`
                                  : "Catalog discount rate signals pricing strategy",
                                snapshot?.product_count != null
                                  ? `${snapshot.product_count.toLocaleString()} products tracked — ${snapshot.product_count > 500 ? "large catalog, broad positioning" : snapshot.product_count > 100 ? "mid-size catalog" : "focused niche catalog"}`
                                  : "Launch velocity and catalog depth analyzed",
                                snapshot?.median_price != null
                                  ? `${formatPrice(snapshot.median_price)} median price point — ${snapshot.median_price < 30 ? "budget positioning" : snapshot.median_price < 80 ? "mid-market" : "premium segment"}`
                                  : "Price positioning relative to market analyzed",
                              ].map((line, i) => (
                                <div key={i} className="flex items-start gap-2">
                                  <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: "var(--muted)" }} />
                                  <p className="text-sm blur-sm" style={{ color: "var(--text-2)" }}>{line}</p>
                                </div>
                              ))}
                            </div>
                            <button
                              onClick={() => setUpgradeOpen(true)}
                              className="font-semibold text-sm px-6 py-3 rounded-md transition-all hover:brightness-110"
                              style={{ background: "var(--accent)", color: "var(--ink)" }}
                            >
                              <Zap className="w-4 h-4 inline mr-1.5 -mt-0.5" />
                              Unlock Intelligence Pro — from $29/mo
                            </button>
                          </div>
                        </div>

                      ) : aiStatus === "error" ? (
                        <div
                          className="rounded-md p-8 text-center"
                          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                        >
                          <p className="text-sm font-semibold mb-2" style={{ color: "var(--text)" }}>Couldn&apos;t generate analysis</p>
                          <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>This can happen if Celery workers aren&apos;t running. Try again in a moment.</p>
                          <button
                            onClick={() => setAiStatus("idle")}
                            className="text-xs font-bold px-4 py-2 rounded-md transition-all hover:brightness-110"
                            style={{ background: "var(--accent)", color: "var(--ink)" }}
                          >
                            Try again
                          </button>
                        </div>
                      ) : (aiStatus === "loading" || aiStatus === "generating") ? (
                        <div className="rounded-md p-6 analyzing-sweep" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                          <div className="flex items-center gap-3 mb-5">
                            <div
                              className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
                              style={{ background: "rgba(255,178,36,.1)", border: "1px solid rgba(255,178,36,.15)" }}
                            >
                              <Sparkles className="w-4 h-4 animate-pulse" style={{ color: "var(--accent)" }} />
                            </div>
                            <div>
                              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                                {aiStatus === "loading" ? "Loading Intelligence Pro…" : `Building strategist report on ${hostname}…`}
                              </p>
                              <p className="text-xs" style={{ color: "var(--muted)" }}>
                                {aiStatus === "generating" ? "Reviewing 30 days of catalog history, pricing moves, and launch cadence — then interpreting what it means for your business" : "Checking for existing analysis"}
                              </p>
                            </div>
                          </div>
                          <div className="space-y-3">
                            {[100, 82, 91, 67, 76].map((w, i) => (
                              <div key={i} className="h-3.5 rounded-full animate-pulse" style={{ background: "rgba(255,255,255,.06)", width: `${w}%` }} />
                            ))}
                          </div>
                          {aiStatus === "generating" && (
                            <p className="text-xs mt-4" style={{ color: "var(--muted)", opacity: 0.6 }}>Usually takes 20–30 seconds</p>
                          )}
                        </div>

                      ) : aiStatus === "none" ? (
                        <div
                          className="rounded-md p-8 text-center"
                          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                        >
                          <div className="w-12 h-12 rounded-md mx-auto mb-4 flex items-center justify-center" style={{ background: "rgba(255,178,36,.06)", border: "1px solid rgba(255,178,36,.14)" }}>
                            <Sparkles className="w-6 h-6" style={{ color: "var(--accent)" }} />
                          </div>
                          <h3 className="text-base font-bold mb-2" style={{ color: "var(--text)" }}>No strategist report yet</h3>
                          <p className="text-sm mb-6 max-w-sm mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
                            Generate a strategist&apos;s read of {hostname} — not a summary, an interpretation.
                          </p>
                          <div className="mb-6 text-left rounded-md p-4 space-y-2.5" style={{ background: "var(--bg3)" }}>
                            {[
                              "Threat score and momentum — is this competitor accelerating?",
                              "Predicted next moves, each with a confidence score",
                              "What their behavior means for YOUR business, with evidence",
                            ].map((line, i) => (
                              <div key={i} className="flex items-start gap-2">
                                <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: "var(--muted)" }} />
                                <p className="text-xs" style={{ color: "var(--text-2)" }}>{line}</p>
                              </div>
                            ))}
                          </div>
                          <button
                            onClick={handleRegenerate}
                            className="font-semibold text-sm px-6 py-3 rounded-md transition-all hover:brightness-110"
                            style={{ background: "var(--accent)", color: "var(--ink)" }}
                          >
                            <Sparkles className="w-4 h-4 inline mr-1.5 -mt-0.5" />
                            Generate analysis
                          </button>
                          <p className="text-xs mt-3" style={{ color: "var(--muted)", opacity: 0.6 }}>Usually takes 20–30 seconds</p>
                        </div>

                      ) : (() => {
                        if (!aiSummary) return null;
                        const pro = parseProAnalysis(aiSummary.summary_text);
                        if (pro) {
                          return (
                            <ProAnalysis
                              hostname={hostname}
                              competitorId={id}
                              data={pro}
                              generatedAt={aiSummary.generated_at}
                              model={aiSummary.model}
                              refreshing={aiRefreshing}
                              onRegenerate={handleRegenerate}
                            />
                          );
                        }
                        // Legacy plain-text summary (pre-Pro rows) — shown once
                        // while the strategist report generates in the background.
                        const parsed = parseSummaryText(aiSummary.summary_text);
                        return (
                          <div className="space-y-4">
                            <div className="flex items-center justify-between gap-3 pb-3" style={{ borderBottom: "1px solid var(--border)" }}>
                              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                                Intelligence · {hostname}
                                <span className="label-caps ml-2" style={{ color: "var(--muted)" }}>
                                  strategist report generating…
                                </span>
                              </p>
                              <button
                                onClick={handleRegenerate}
                                className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg transition-all hover:bg-white/5 shrink-0"
                                style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
                              >
                                <RefreshCw className="w-3 h-3" /> Refresh
                              </button>
                            </div>
                            <div className="space-y-3">
                              {(parsed.type === "text" ? parsed.text.split(/\n\n+/).filter(Boolean) : []).map((para, i) => (
                                <p key={i} className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>{para}</p>
                              ))}
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  )}

                  {/* ── Brand Profile ── */}
                  {intelSub === "brand" && <StoreProfileTab competitorId={id} />}

                  {/* ── vs You ── */}
                  {intelSub === "compare" && <ComparisonTab competitorId={id} />}
                </div>
              </div>
            )}

          </div>
        </>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" currentTier={tier} />
    </div>
  );
}
