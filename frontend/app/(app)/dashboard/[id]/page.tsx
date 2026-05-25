"use client";

import { useEffect, useState, use, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, RefreshCw, Trash2, Share2, Check, Download,
  Sparkles, Lock, Zap, ChevronDown, ChevronUp, Bell, TrendingUp,
  Package, Tag, Clock, Brain,
} from "lucide-react";
import Link from "next/link";
import {
  competitors as api, user as userApi,
  type Snapshot, type ChangeEvent, type AiSummary,
} from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import {
  cn, formatRelativeTime, formatPrice, formatPct, formatDelta,
  changeTypeIcon,
} from "@/lib/utils";
import { PriceDistributionChart } from "@/components/charts/PriceDistributionChart";
import { PriceHistoryChart } from "@/components/charts/PriceHistoryChart";
import { LaunchVelocityChart } from "@/components/charts/LaunchVelocityChart";
import WinningProductsTab from "@/components/competitors/WinningProductsTab";
import GapsTab from "@/components/competitors/GapsTab";
import StoreProfileTab from "@/components/competitors/StoreProfileTab";
import ComparisonTab from "@/components/competitors/ComparisonTab";
import { IntelligenceBrief } from "@/components/competitors/IntelligenceBrief";
import { QuickWins } from "@/components/competitors/QuickWins";
import UpgradeModal from "@/components/UpgradeModal";
import { type BriefData, type BriefCard } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────
type Tab = "overview" | "catalog" | "pricing" | "changes" | "intelligence";
type CatalogSub = "winning" | "gaps";
type IntelSub = "ai" | "brand" | "compare";

// ── Expandable KPI card ───────────────────────────────────────────────────────
function KpiCard({
  label, value, sub, accent, insight, actionLabel, onAction, locked = false,
}: {
  label: string; value: string; sub?: string; accent?: string;
  insight?: string; actionLabel?: string; onAction?: () => void; locked?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const clickable = !!insight;

  return (
    <div
      className={cn("rounded-2xl overflow-hidden transition-all", clickable && "cursor-pointer hover:ring-1 hover:ring-white/10")}
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderTop: accent ? `2px solid ${accent}` : "1px solid var(--border)",
      }}
      onClick={() => clickable && setExpanded((v) => !v)}
    >
      <div className="p-5">
        <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--muted)" }}>
          {label}
        </p>
        <p className="text-2xl font-bold font-mono" style={{ color: "var(--text)" }}>{value}</p>
        {sub && <p className="text-xs mt-1.5" style={{ color: "var(--muted)" }}>{sub}</p>}
        {clickable && (
          <div className="flex items-center gap-1 mt-2.5">
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
          className="px-5 pb-4 border-t"
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
                  : { background: "rgba(168,255,0,.1)", color: "var(--accent)", border: "1px solid rgba(168,255,0,.2)" }
              }
            >
              {locked && <Lock className="w-3 h-3" />}
              {actionLabel}
              {locked && (
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded-full ml-0.5"
                  style={{ background: "rgba(168,255,0,.15)", color: "var(--accent)" }}
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

// ── Signal badge ──────────────────────────────────────────────────────────────
function SignalBadge({ label, scoreLabel, score }: { label: string; scoreLabel: string; score: number }) {
  const color = score < 34 ? "var(--cyan)" : score < 67 ? "var(--accent)" : "var(--red)";
  const bg    = score < 34 ? "rgba(34,211,238,.1)" : score < 67 ? "rgba(168,255,0,.1)" : "rgba(239,68,68,.1)";
  return (
    <div
      className="flex items-center justify-between px-4 py-3 rounded-xl"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>{label}</span>
      <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{ color, background: bg }}>
        {scoreLabel}
      </span>
    </div>
  );
}

// ── Change row ────────────────────────────────────────────────────────────────
function ChangeRow({ change }: { change: ChangeEvent }) {
  const icon  = changeTypeIcon(change.change_type);
  const old_v = change.old_value || {};
  const new_v = change.new_value || {};
  let detail  = "";
  if (change.change_type === "price_change" && change.delta_pct != null) {
    detail = `${formatPrice(old_v.price as number)} → ${formatPrice(new_v.price as number)} (${formatDelta(change.delta_pct)})`;
  } else if (change.change_type === "new_product") {
    detail = new_v.price_min ? `from ${formatPrice(new_v.price_min as number)}` : "";
  } else if (change.change_type === "discount_start" || change.change_type === "discount_end") {
    detail = `${formatPct(old_v.discounted_pct as number)} → ${formatPct(new_v.discounted_pct as number)} of catalog`;
  }
  const borderColor =
    change.severity === "critical" ? "var(--red)" :
    change.severity === "warning"  ? "var(--amber)" : "transparent";
  const detailColor = change.delta_pct != null && change.delta_pct < 0 ? "var(--red)" : "var(--emerald)";

  return (
    <div
      className="flex items-start gap-3 py-3 pl-3 border-b last:border-0"
      style={{ borderColor: "var(--border)", borderLeft: `3px solid ${borderColor}`, marginLeft: "-1px" }}
    >
      <span className="text-base leading-none mt-0.5 shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
          {change.product_title || change.change_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </p>
        {detail && (
          <p className="text-xs font-mono mt-0.5" style={{ color: detailColor }}>{detail}</p>
        )}
      </div>
      <p className="text-xs shrink-0" style={{ color: "var(--muted)" }}>
        {formatRelativeTime(change.detected_at)}
      </p>
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
          className="flex flex-col items-center gap-3 px-6 py-5 rounded-2xl text-center"
          style={{ background: "rgba(10,10,15,.85)", border: "1px solid rgba(168,255,0,.2)", backdropFilter: "blur(8px)" }}
        >
          <Lock className="w-5 h-5" style={{ color: "var(--accent)" }} />
          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>{label}</p>
          <button
            onClick={onUpgrade}
            className="text-xs font-bold px-4 py-2 rounded-xl transition-all hover:brightness-110"
            style={{ background: "var(--accent)", color: "#0a0a0f" }}
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
              style={{ background: "rgba(168,255,0,.12)", color: "var(--accent)" }}
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
  const { id }   = use(params);
  const router   = useRouter();

  const [competitor,     setCompetitor]     = useState<import("@/lib/api").Competitor | null>(null);
  const [snapshot,       setSnapshot]       = useState<Snapshot | null>(null);
  const [changes,        setChanges]        = useState<ChangeEvent[]>([]);
  const [aiSummary,      setAiSummary]      = useState<AiSummary | null>(null);
  const [aiStatus,       setAiStatus]       = useState<"idle" | "loading" | "generating" | "error">("idle");
  const aiPollRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const aiPollCount  = useRef(0);
  const [loading,        setLoading]        = useState(true);
  const [tab,            setTab]            = useState<Tab>("overview");
  const [catalogSub,     setCatalogSub]     = useState<CatalogSub>("winning");
  const [intelSub,       setIntelSub]       = useState<IntelSub>("ai");
  const [rescanning,     setRescanning]     = useState(false);
  const [scanPending,    setScanPending]    = useState(true);
  const [brief,          setBrief]          = useState<BriefData | null | false>(null);
  const [briefDismissed, setBriefDismissed] = useState(false);
  const [copied,         setCopied]         = useState(false);
  const [exporting,      setExporting]      = useState(false);
  const [upgradeOpen,    setUpgradeOpen]    = useState(false);
  const [tier,           setTier]           = useState<string>("free");
  const [showAllChanges, setShowAllChanges] = useState(false);

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
          setAiStatus("idle");
        } else {
          setAiStatus("error");
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
    if (scanPending || brief !== null || briefDismissed) return;
    let cancelled = false;
    let attempts  = 0;
    const tryFetch = async () => {
      if (cancelled || attempts >= 12) { if (!cancelled) setBrief(false); return; }
      attempts++;
      try {
        const r     = await api.brief(id);
        if (cancelled) return;
        const stored = typeof window !== "undefined" ? sessionStorage.getItem(`brief_${id}`) : null;
        if (stored === r.data.id) { setBriefDismissed(true); setBrief(false); }
        else setBrief(r.data);
      } catch (e: unknown) {
        const status = (e as { status?: number })?.status;
        if (status === 404 && !cancelled) setTimeout(tryFetch, 5000);
        else if (!cancelled) setBrief(false);
      }
    };
    tryFetch();
    return () => { cancelled = true; };
  }, [id, scanPending, brief, briefDismissed]);

  async function handleRescan() {
    setRescanning(true);
    await api.rescan(id).catch(() => {});
    setTimeout(() => setRescanning(false), 3000);
  }

  function handleDismissBrief() {
    if (brief && typeof window !== "undefined") sessionStorage.setItem(`brief_${id}`, (brief as BriefData).id);
    setBriefDismissed(true);
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
    { id: "winning", label: "Winning Products" },
    { id: "gaps",    label: "Gaps to Fill" },
  ];

  const INTEL_TABS: { id: IntelSub; label: string }[] = [
    { id: "ai",      label: "AI Insights" },
    { id: "brand",   label: "Brand Profile" },
    { id: "compare", label: "vs You" },
  ];

  // Changes visibility
  const FREE_CHANGES_LIMIT = 3;
  const visibleChanges = isFree && !showAllChanges ? changes.slice(0, FREE_CHANGES_LIMIT) : changes;
  const hiddenCount    = isFree ? Math.max(0, changes.length - FREE_CHANGES_LIMIT) : 0;

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-48 rounded-xl" style={{ background: "var(--bg-card)" }} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-28 rounded-2xl" style={{ background: "var(--bg-card)" }} />)}
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
          background: "linear-gradient(135deg, rgba(168,255,0,.05) 0%, transparent 60%)",
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
            <h1 className="text-3xl font-bold tracking-tight truncate" style={{ color: "var(--text)" }}>
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
                className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-xl transition-all hover:bg-white/[0.06]"
                style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
              >
                {copied ? <Check className="w-3.5 h-3.5" style={{ color: "var(--emerald)" }} /> : <Share2 className="w-3.5 h-3.5" />}
                {copied ? "Copied" : "Share"}
              </button>
            )}
            <button
              onClick={handleExportCsv}
              disabled={exporting}
              className="flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-xl transition-all hover:bg-white/[0.06] disabled:opacity-50"
              style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
            >
              <Download className="w-3.5 h-3.5" />
              {exporting ? "…" : "CSV"}
            </button>
            <button
              onClick={handleRescan}
              className="flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-xl transition-all hover:brightness-110"
              style={{ background: "rgba(168,255,0,.1)", color: "var(--accent)", border: "1px solid rgba(168,255,0,.2)" }}
            >
              <RefreshCw className={cn("w-3.5 h-3.5", rescanning && "animate-spin")} />
              Rescan
            </button>
            <button
              onClick={handleDelete}
              className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-xl transition-all hover:bg-red-500/10"
              style={{ color: "var(--red)", border: "1px solid rgba(239,68,68,.25)" }}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* ── No snapshot yet ───────────────────────────────────────────────── */}
      {!snapshot ? (
        <div
          className="rounded-2xl p-8 text-center"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <p style={{ color: "var(--muted)" }}>Scan in progress — usually takes about 20 seconds.</p>
        </div>

      ) : brief && !briefDismissed ? (
        /* Intelligence brief banner */
        <IntelligenceBrief
          hostname={hostname}
          cards={(() => {
            try { return (JSON.parse((brief as BriefData).summary_text) as { cards: BriefCard[] }).cards; }
            catch { return []; }
          })()}
          onDismiss={handleDismissBrief}
        />

      ) : (
        <>
          {/* ── Tab navigation ────────────────────────────────────────────── */}
          <TabBar tabs={MAIN_TABS} active={tab} onChange={setTab} />

          <div className="mt-6">

            {/* ══════════════════════════════════════════════════════════════
                OVERVIEW
            ══════════════════════════════════════════════════════════════ */}
            {tab === "overview" && (
              <div className="space-y-6 fade-up">
                {/* Expandable KPI cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <KpiCard
                    label="Products"
                    value={(catalog.total_products as number)?.toLocaleString() ?? "—"}
                    accent="var(--blue)"
                    insight={`This store has ${(catalog.total_products as number)?.toLocaleString() ?? "an unknown number of"} active products. Compare this to your own catalog size to gauge competitive breadth.`}
                    actionLabel="Alert me when count changes"
                    onAction={() => setUpgradeOpen(true)}
                    locked={isFree}
                  />
                  <KpiCard
                    label="Median Price"
                    value={formatPrice(pricing.median as number)}
                    accent="var(--accent)"
                    insight={`Their median price is ${formatPrice(pricing.median as number)}, ranging from ${formatPrice(pricing.min as number)} to ${formatPrice(pricing.max as number)}. This positions them in the ${(positioning.market_position as Record<string, unknown>)?.label ?? "mid-market"} segment.`}
                    actionLabel="See 90-day price history"
                    onAction={() => { if (isFree) setUpgradeOpen(true); else setTab("pricing"); }}
                    locked={isFree}
                  />
                  <KpiCard
                    label="Promo Rate"
                    value={formatPct(discounts.discounted_pct as number)}
                    accent="var(--amber)"
                    insight={`${formatPct(discounts.discounted_pct as number)} of their catalog is currently discounted — average discount depth is ${formatPct(discounts.avg_discount_pct as number)}. A high promo rate can signal pricing pressure or clearance cycles.`}
                    actionLabel="Alert me on flash sales"
                    onAction={() => setUpgradeOpen(true)}
                    locked={isFree}
                  />
                  <KpiCard
                    label="New (30d)"
                    value={((launch as Record<string, Record<string, Record<string, number>>>)?.launch_counts?.["30d"]?.count ?? "—").toString()}
                    accent="var(--emerald)"
                    insight={`They launched ${((launch as Record<string, Record<string, Record<string, number>>>)?.launch_counts?.["30d"]?.count ?? 0)} products in the last 30 days. A high velocity often signals an aggressive growth phase or seasonal push.`}
                    actionLabel="Alert me when they launch"
                    onAction={() => setUpgradeOpen(true)}
                    locked={isFree}
                  />
                </div>

                {/* Quick wins */}
                <QuickWins competitorId={id} />

                {/* Positioning signals */}
                {[positioning.market_position, positioning.promo_intensity, positioning.launch_velocity, positioning.catalog_complexity].some(Boolean) && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--muted)" }}>
                      Competitive signals
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { label: "Market Position",    pos: positioning.market_position    as Record<string, unknown> },
                        { label: "Promo Intensity",    pos: positioning.promo_intensity    as Record<string, unknown> },
                        { label: "Launch Velocity",    pos: positioning.launch_velocity    as Record<string, unknown> },
                        { label: "Catalog Complexity", pos: positioning.catalog_complexity as Record<string, unknown> },
                      ].map(({ label, pos }) => pos ? (
                        <SignalBadge
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
                    className="rounded-2xl p-5"
                    style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                  >
                    <div className="flex items-center gap-2 mb-4">
                      <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
                      <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Key insights</h3>
                    </div>
                    <ul className="space-y-3">
                      {takeaways.map((t, i) => (
                        <li key={i} className="flex items-start gap-3 text-sm leading-snug" style={{ color: "var(--text-2)" }}>
                          <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ background: "var(--accent)" }} />
                          {t}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Recent changes preview */}
                {changes.length > 0 && (
                  <div
                    className="rounded-2xl overflow-hidden"
                    style={{ border: "1px solid var(--border)" }}
                  >
                    <div
                      className="flex items-center justify-between px-5 py-3.5"
                      style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}
                    >
                      <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Recent changes</h3>
                      <button
                        onClick={() => setTab("changes")}
                        className="text-xs font-medium hover:underline"
                        style={{ color: "var(--accent)" }}
                      >
                        View all {changes.length} →
                      </button>
                    </div>
                    <div className="px-5" style={{ background: "var(--bg-card)" }}>
                      {changes.slice(0, 4).map((c) => <ChangeRow key={c.id} change={c} />)}
                    </div>
                  </div>
                )}
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
                  className="rounded-2xl p-5"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                >
                  <div className="flex items-center gap-2 mb-4">
                    <Tag className="w-4 h-4" style={{ color: "var(--amber)" }} />
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
                        const color = pct > 50 ? "#f59e0b" : pct > 25 ? "#a8ff00" : "#22d3ee";
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
                      className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 text-xs font-semibold rounded-xl transition-all"
                      style={{ background: "rgba(255,255,255,.04)", color: "var(--muted)", border: "1px solid var(--border)" }}
                    >
                      <Lock className="w-3.5 h-3.5" />
                      Get alerted when they run a flash sale
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: "rgba(168,255,0,.15)", color: "var(--accent)" }}>Pro</span>
                    </button>
                  ) : (
                    <button
                      className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 text-xs font-semibold rounded-xl transition-all hover:brightness-110"
                      style={{ background: "rgba(168,255,0,.1)", color: "var(--accent)", border: "1px solid rgba(168,255,0,.2)" }}
                    >
                      <Bell className="w-3.5 h-3.5" />
                      Set flash sale alert
                    </button>
                  )}
                </div>

                {/* Launch velocity */}
                <div
                  className="rounded-2xl p-5"
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
                  className="rounded-2xl p-5"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                >
                  <div className="flex items-center gap-2 mb-4">
                    <Clock className="w-4 h-4" style={{ color: "var(--blue)" }} />
                    <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Price history</h3>
                    {isFree && (
                      <span
                        className="text-[10px] font-bold px-1.5 py-0.5 rounded-full ml-auto"
                        style={{ background: "rgba(168,255,0,.12)", color: "var(--accent)" }}
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
              </div>
            )}

            {/* ══════════════════════════════════════════════════════════════
                CHANGES
            ══════════════════════════════════════════════════════════════ */}
            {tab === "changes" && (
              <div className="fade-up">
                <div
                  className="rounded-2xl overflow-hidden"
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
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: "rgba(168,255,0,.12)", color: "var(--accent)" }}>
                        PRO for full history
                      </span>
                    )}
                  </div>

                  {changes.length === 0 ? (
                    <div className="px-5 py-12 text-center" style={{ background: "var(--bg-card)" }}>
                      <p className="text-sm" style={{ color: "var(--muted)" }}>
                        No changes detected yet. Check back after the next scan.
                      </p>
                    </div>
                  ) : (
                    <div>
                      <div className="px-5" style={{ background: "var(--bg-card)" }}>
                        {visibleChanges.map((c) => <ChangeRow key={c.id} change={c} />)}
                      </div>

                      {/* Free tier gate */}
                      {isFree && hiddenCount > 0 && (
                        <div
                          className="px-5 py-5 flex flex-col items-center gap-3 border-t"
                          style={{ borderColor: "var(--border)", background: "var(--bg3)" }}
                        >
                          <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                            +{hiddenCount} more change{hiddenCount !== 1 ? "s" : ""} detected
                          </p>
                          <p className="text-xs text-center max-w-xs" style={{ color: "var(--muted)" }}>
                            Upgrade to Pro to see the full change history and get alerts within 15 minutes of detection.
                          </p>
                          <button
                            onClick={() => setUpgradeOpen(true)}
                            className="flex items-center gap-1.5 text-xs font-bold px-5 py-2.5 rounded-xl transition-all hover:brightness-110"
                            style={{ background: "var(--accent)", color: "#0a0a0f" }}
                          >
                            <Zap className="w-3.5 h-3.5" />
                            Unlock full history — $29/mo
                          </button>
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
                          className="rounded-2xl p-8 text-center relative overflow-hidden"
                          style={{ background: "var(--bg-card)", border: "1px solid rgba(168,255,0,.2)" }}
                        >
                          <div className="absolute -top-16 left-1/2 -translate-x-1/2 w-48 h-48 rounded-full blur-3xl pointer-events-none" style={{ background: "rgba(168,255,0,.06)" }} />
                          <div className="relative">
                            <div className="w-12 h-12 rounded-2xl mx-auto mb-4 flex items-center justify-center" style={{ background: "rgba(168,255,0,.1)", border: "1px solid rgba(168,255,0,.2)" }}>
                              <Sparkles className="w-6 h-6" style={{ color: "var(--accent)" }} />
                            </div>
                            <h3 className="text-lg font-bold mb-2" style={{ color: "var(--text)" }}>AI Strategic Summary</h3>
                            <p className="text-sm mb-6 max-w-sm mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
                              Get weekly AI-generated insights on {hostname}&apos;s pricing strategy, launch patterns, and competitive positioning.
                            </p>
                            <div className="mb-6 text-left rounded-xl p-4 space-y-2 select-none pointer-events-none" style={{ background: "var(--bg3)" }}>
                              {["44.6% catalog discounted signals aggressive positioning", "Minimal 1 product monthly launch velocity", "Budget positioning with $32 median price"].map((line, i) => (
                                <div key={i} className="flex items-start gap-2">
                                  <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: "var(--accent)" }} />
                                  <p className="text-sm blur-sm" style={{ color: "var(--text-2)" }}>{line}</p>
                                </div>
                              ))}
                            </div>
                            <button
                              onClick={() => setUpgradeOpen(true)}
                              className="font-semibold text-sm px-6 py-3 rounded-xl transition-all hover:brightness-110"
                              style={{ background: "var(--accent)", color: "#0a0a0f" }}
                            >
                              <Zap className="w-4 h-4 inline mr-1.5 -mt-0.5" />
                              Unlock AI Insights — from $29/mo
                            </button>
                          </div>
                        </div>

                      ) : aiStatus === "error" ? (
                        <div
                          className="rounded-2xl p-8 text-center"
                          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                        >
                          <p className="text-sm font-semibold mb-2" style={{ color: "var(--text)" }}>Couldn&apos;t generate analysis</p>
                          <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>This can happen if Celery workers aren&apos;t running. Try again in a moment.</p>
                          <button
                            onClick={() => setAiStatus("idle")}
                            className="text-xs font-bold px-4 py-2 rounded-xl transition-all hover:brightness-110"
                            style={{ background: "var(--accent)", color: "#0a0a0f" }}
                          >
                            Try again
                          </button>
                        </div>
                      ) : (aiStatus === "loading" || aiStatus === "generating") ? (
                        <div className="rounded-2xl p-6" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                          <div className="flex items-center gap-3 mb-5">
                            <div
                              className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                              style={{ background: "rgba(168,255,0,.1)", border: "1px solid rgba(168,255,0,.15)" }}
                            >
                              <Sparkles className="w-4 h-4 animate-pulse" style={{ color: "var(--accent)" }} />
                            </div>
                            <div>
                              <p className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                                {aiStatus === "loading" ? "Loading intelligence brief…" : `Analyzing ${hostname}…`}
                              </p>
                              <p className="text-xs" style={{ color: "var(--muted)" }}>
                                {aiStatus === "generating" ? "Claude is reviewing their pricing, launch patterns, and competitive positioning" : "Checking for existing analysis"}
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

                      ) : (() => {
                        if (!aiSummary) return null;
                        const parsed = parseSummaryText(aiSummary.summary_text);
                        const CARD_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
                          signal:      { color: "#a8ff00", bg: "rgba(168,255,0,.07)",  border: "rgba(168,255,0,.18)",  label: "Most notable signal" },
                          opportunity: { color: "#60a5fa", bg: "rgba(96,165,250,.07)", border: "rgba(96,165,250,.18)", label: "Your opening" },
                          watch:       { color: "#f59e0b", bg: "rgba(245,158,11,.07)", border: "rgba(245,158,11,.18)", label: "Watch this" },
                        };
                        return (
                          <div className="space-y-5">
                            <div className="flex items-center gap-2">
                              <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
                              <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>AI Strategic Summary</h3>
                              <p className="text-xs" style={{ color: "var(--muted)" }}>{formatRelativeTime(aiSummary.generated_at)}</p>
                              <button
                                onClick={handleRegenerate}
                                className="ml-auto flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg transition-all hover:bg-white/5"
                                style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
                                title="Regenerate analysis"
                              >
                                <RefreshCw className="w-3 h-3" />
                                Refresh
                              </button>
                            </div>
                            {parsed.type === "cards" ? (
                              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                {parsed.cards.map((card, i) => {
                                  const cfg = CARD_CONFIG[card.type] ?? CARD_CONFIG.signal;
                                  return (
                                    <div key={i} className="rounded-xl p-5" style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                                      <span className="text-[10px] font-bold uppercase tracking-wider block mb-3" style={{ color: cfg.color }}>{cfg.label}</span>
                                      <h4 className="font-bold text-sm mb-2 leading-snug" style={{ color: "var(--text)" }}>{card.headline}</h4>
                                      <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>{card.body}</p>
                                    </div>
                                  );
                                })}
                              </div>
                            ) : (
                              <div className="rounded-2xl p-5 space-y-4" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
                                {parsed.text.split(/\n\n+/).filter(Boolean).map((para, i) => (
                                  <p key={i} className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>{para}</p>
                                ))}
                              </div>
                            )}
                            <p className="text-xs" style={{ color: "var(--muted)" }}>{aiSummary.model}</p>
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

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
