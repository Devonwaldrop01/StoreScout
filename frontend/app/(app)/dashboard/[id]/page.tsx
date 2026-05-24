"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, RefreshCw, Trash2, Cpu, Share2, Check, Download, Sparkles, Lock, TrendingUp, TrendingDown, Zap } from "lucide-react";
import Link from "next/link";
import { competitors as api, user as userApi, type Snapshot, type ChangeEvent, type AiSummary } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { cn, formatRelativeTime, formatPrice, formatPct, formatDelta, changeTypeIcon, severityColor } from "@/lib/utils";
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

type Tab = "overview" | "compare" | "winning" | "gaps" | "brand" | "pricing" | "launches" | "discounts" | "history" | "ai";

function KpiCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div
      className="rounded-2xl p-5"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderTop: accent ? `2px solid ${accent}` : "1px solid var(--border)",
      }}
    >
      <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--muted)" }}>{label}</p>
      <p className="text-2xl font-bold font-mono" style={{ color: "var(--text)" }}>{value}</p>
      {sub && <p className="text-xs mt-1.5" style={{ color: "var(--muted)" }}>{sub}</p>}
    </div>
  );
}

function SignalBadge({ label, scoreLabel, score }: { label: string; scoreLabel: string; score: number }) {
  const color = score < 34 ? "var(--cyan)" : score < 67 ? "var(--accent)" : "var(--red)";
  const bg = score < 34 ? "rgba(34,211,238,.1)" : score < 67 ? "rgba(168,255,0,.1)" : "rgba(239,68,68,.1)";
  return (
    <div
      className="flex items-center justify-between px-4 py-3 rounded-xl"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>{label}</span>
      <span
        className="text-xs font-bold px-2.5 py-1 rounded-full"
        style={{ color, background: bg }}
      >
        {scoreLabel}
      </span>
    </div>
  );
}

function ChangeRow({ change }: { change: ChangeEvent }) {
  const icon = changeTypeIcon(change.change_type);
  const old_v = change.old_value || {};
  const new_v = change.new_value || {};
  let detail = "";
  if (change.change_type === "price_change" && change.delta_pct != null) {
    detail = `${formatPrice(old_v.price as number)} → ${formatPrice(new_v.price as number)} (${formatDelta(change.delta_pct)})`;
  } else if (change.change_type === "new_product") {
    detail = new_v.price_min ? `$${new_v.price_min}` : "";
  } else if (change.change_type === "discount_start" || change.change_type === "discount_end") {
    detail = `${formatPct(old_v.discounted_pct as number)} → ${formatPct(new_v.discounted_pct as number)} of catalog`;
  }
  const borderColor = change.severity === "critical" ? "var(--red)" : change.severity === "warning" ? "var(--amber)" : "transparent";
  return (
    <div
      className="flex items-start gap-3 py-3 pl-3 border-b"
      style={{ borderColor: "var(--border)", borderLeft: `3px solid ${borderColor}`, marginLeft: "-1px" }}
    >
      <span className="text-base leading-none mt-0.5 shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
          {change.product_title || change.change_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </p>
        {detail && <p className="text-xs font-mono mt-0.5" style={{ color: change.delta_pct != null && change.delta_pct < 0 ? "var(--red)" : "var(--emerald)" }}>{detail}</p>}
      </div>
      <p className="text-xs shrink-0" style={{ color: "var(--muted)" }}>
        {formatRelativeTime(change.detected_at)}
      </p>
    </div>
  );
}

function parseSummaryText(text: string): { type: "cards"; cards: BriefCard[] } | { type: "text"; text: string } {
  try {
    const parsed = JSON.parse(text) as { cards?: BriefCard[] };
    if (parsed.cards && Array.isArray(parsed.cards)) {
      return { type: "cards", cards: parsed.cards };
    }
  } catch {}
  return { type: "text", text };
}

export default function CompetitorDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [changes, setChanges] = useState<ChangeEvent[]>([]);
  const [aiSummary, setAiSummary] = useState<AiSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");
  const [rescanning, setRescanning] = useState(false);
  const [scanPending, setScanPending] = useState(true);
  const [brief, setBrief] = useState<BriefData | null | false>(null);
  const [briefDismissed, setBriefDismissed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [tier, setTier] = useState<string>("free");

  useEffect(() => {
    async function load() {
      try {
        const snapRes = await api.latestSnapshot(id);
        setSnapshot(snapRes.data);
        setScanPending(false);
      } catch {
        // 404 = scan not done yet, keep polling fast
      }
      // Load changes separately — don't let a 500 here block snapshot display
      try {
        const changesRes = await api.changes(id, 20);
        setChanges(changesRes.data);
      } catch {
        // changes table may be empty or erroring — non-fatal
      }
      setLoading(false);
      userApi.subscription().then((r) => setTier(r.data.tier)).catch(() => {});
    }
    load();
    // Poll fast (3s) while scan is pending, slow (15s) once data loaded
    const interval = setInterval(load, scanPending ? 3000 : 15000);
    return () => clearInterval(interval);
  }, [id, scanPending]);

  useEffect(() => {
    if (tab === "ai" && !aiSummary && tier !== "free") {
      api.aiSummary(id).then((r) => setAiSummary(r.data)).catch(() => {});
    }
  }, [tab, aiSummary, id, tier]);

  // Poll for Intelligence Brief once scan is done — brief is generated async via Claude
  useEffect(() => {
    if (scanPending || brief !== null || briefDismissed) return;
    let cancelled = false;
    let attempts = 0;

    const tryFetch = async () => {
      if (cancelled || attempts >= 12) {
        if (!cancelled) setBrief(false);
        return;
      }
      attempts++;
      try {
        const r = await api.brief(id);
        if (cancelled) return;
        // Check if this specific brief was already dismissed this session
        const storedId = typeof window !== "undefined"
          ? sessionStorage.getItem(`brief_${id}`) : null;
        if (storedId === r.data.id) {
          setBriefDismissed(true);
          setBrief(false);
        } else {
          setBrief(r.data);
        }
      } catch (e: unknown) {
        const status = (e as { status?: number })?.status;
        if (status === 404 && !cancelled) {
          setTimeout(tryFetch, 5000);
        } else if (!cancelled) {
          setBrief(false);
        }
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
    if (brief && typeof window !== "undefined") {
      sessionStorage.setItem(`brief_${id}`, (brief as BriefData).id);
    }
    setBriefDismissed(true);
  }

  function handleShare() {
    if (!snapshot) return;
    const url = `${window.location.origin}/reports/${snapshot.id}`;
    navigator.clipboard.writeText(url).catch(() => {});
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
      if (res.status === 403) {
        setUpgradeOpen(true);
        return;
      }
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const hostname = (snapshot?.snapshot_data as Record<string, unknown>)?.hostname as string || id;
      a.download = `${hostname.replace(/\./g, "_")}_products.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Remove this competitor? All history will be deleted.")) return;
    await api.remove(id).catch(() => {});
    router.push("/dashboard");
  }

  const data = snapshot?.snapshot_data as Record<string, unknown> | undefined;
  const catalog = (data?.catalog || {}) as Record<string, unknown>;
  const pricing = (data?.pricing || {}) as Record<string, unknown>;
  const discounts = (data?.discounts || {}) as Record<string, unknown>;
  const positioning = (data?.positioning || {}) as Record<string, unknown>;
  const launch = (data?.launch_timeline || {}) as Record<string, unknown>;
  const takeaways = (data?.takeaways || []) as string[];

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "compare", label: "vs You" },
    { id: "winning", label: "Winning Products" },
    { id: "gaps", label: "Gaps" },
    { id: "brand", label: "Brand" },
    { id: "pricing", label: "Pricing" },
    { id: "launches", label: "Launches" },
    { id: "discounts", label: "Discounts" },
    { id: "history", label: "History" },
    { id: "ai", label: "AI Insights" },
  ];

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-48 rounded-xl" style={{ background: "var(--bg-card)" }} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 rounded-2xl" style={{ background: "var(--bg-card)" }} />)}
        </div>
      </div>
    );
  }

  const hostname = (snapshot?.snapshot_data as Record<string, unknown>)?.hostname as string || id;

  return (
    <div>
      {/* Header — gradient strip */}
      <div
        className="-mx-4 sm:-mx-6 px-4 sm:px-6 pt-6 pb-5 mb-6 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(168,255,0,.05) 0%, transparent 60%)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        {/* Back link */}
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

      {!snapshot ? (
        <div
          className="rounded-2xl p-8 text-center"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
        >
          <p style={{ color: "var(--muted)" }}>
            Scan in progress — usually takes about 20 seconds.
          </p>
        </div>
      ) : brief && !briefDismissed ? (
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
          {/* Tab nav */}
          <div
            className="flex gap-0 mb-6 overflow-x-auto border-b"
            style={{ borderColor: "var(--border)" }}
          >
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className="relative px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors"
                style={{ color: tab === t.id ? "var(--accent)" : "var(--muted)" }}
              >
                {t.label}
                {tab === t.id && (
                  <span
                    className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full"
                    style={{ background: "var(--accent)" }}
                  />
                )}
              </button>
            ))}
          </div>

          {/* Overview tab */}
          {tab === "overview" && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard label="Products" value={(catalog.total_products as number)?.toLocaleString() ?? "—"} accent="var(--blue)" />
                <KpiCard label="Median Price" value={formatPrice(pricing.median as number)} accent="var(--accent)" />
                <KpiCard label="Promo Rate" value={formatPct(discounts.discounted_pct as number)} accent="var(--amber)" />
                <KpiCard
                  label="New (30d)"
                  value={((launch as Record<string, Record<string, Record<string, number>>>)?.launch_counts?.["30d"]?.count ?? "—").toString()}
                  accent="var(--emerald)"
                />
              </div>

              <QuickWins competitorId={id} />

              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: "Market Position", pos: positioning.market_position as Record<string, unknown> },
                  { label: "Promo Intensity", pos: positioning.promo_intensity as Record<string, unknown> },
                  { label: "Launch Velocity", pos: positioning.launch_velocity as Record<string, unknown> },
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
                        <span
                          className="mt-1.5 w-1 h-1 rounded-full shrink-0"
                          style={{ background: "var(--accent)" }}
                        />
                        {t}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

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
                    {changes.length > 5 && (
                      <button
                        onClick={() => setTab("history")}
                        className="text-xs font-medium hover:underline"
                        style={{ color: "var(--accent)" }}
                      >
                        View all {changes.length} →
                      </button>
                    )}
                  </div>
                  <div className="px-5" style={{ background: "var(--bg-card)" }}>
                    {changes.slice(0, 5).map((c) => <ChangeRow key={c.id} change={c} />)}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* vs You comparison tab */}
          {tab === "compare" && <ComparisonTab competitorId={id} />}

          {/* Winning Products tab */}
          {tab === "winning" && <WinningProductsTab competitorId={id} />}

          {/* Gaps tab */}
          {tab === "gaps" && <GapsTab competitorId={id} />}

          {/* Brand Intelligence tab */}
          {tab === "brand" && <StoreProfileTab competitorId={id} />}

          {/* Pricing tab */}
          {tab === "pricing" && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                  ["Min", formatPrice(pricing.min as number)],
                  ["P25", formatPrice(pricing.p25 as number)],
                  ["Median", formatPrice(pricing.median as number)],
                  ["P75", formatPrice(pricing.p75 as number)],
                  ["Max", formatPrice(pricing.max as number)],
                ].map(([label, value]) => (
                  <KpiCard key={label} label={label} value={value} />
                ))}
              </div>
              <PriceDistributionChart pricingData={pricing} />
              <PriceHistoryChart competitorId={id} />
            </div>
          )}

          {/* Launches tab */}
          {tab === "launches" && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  ["7 days", ((launch as Record<string, Record<string, Record<string, unknown>>>)?.launch_counts?.["7d"]?.count ?? "—").toString()],
                  ["30 days", ((launch as Record<string, Record<string, Record<string, unknown>>>)?.launch_counts?.["30d"]?.count ?? "—").toString()],
                  ["90 days", ((launch as Record<string, Record<string, Record<string, unknown>>>)?.launch_counts?.["90d"]?.count ?? "—").toString()],
                  ["12 months", ((launch as Record<string, Record<string, Record<string, unknown>>>)?.launch_counts?.["1yr"]?.count ?? "—").toString()],
                ].map(([label, value]) => (
                  <KpiCard key={label} label={`New (${label})`} value={value} />
                ))}
              </div>
              <LaunchVelocityChart launchData={launch} />
            </div>
          )}

          {/* Discounts tab */}
          {tab === "discounts" && (
            <div className="space-y-5">
              {/* Visual gauge for promo rate */}
              <div
                className="rounded-2xl p-6 flex flex-col sm:flex-row items-center gap-6"
                style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
              >
                {/* SVG arc gauge */}
                <div className="shrink-0 relative w-32 h-20">
                  {(() => {
                    const pct = Math.min(100, Math.max(0, (discounts.discounted_pct as number) || 0));
                    const radius = 48;
                    const cx = 64;
                    const cy = 64;
                    const startAngle = Math.PI;
                    const endAngle = 2 * Math.PI;
                    const filled = startAngle + (endAngle - startAngle) * (pct / 100);
                    const toXY = (a: number) => ({ x: cx + radius * Math.cos(a), y: cy + radius * Math.sin(a) });
                    const s = toXY(startAngle);
                    const e = toXY(endAngle - 0.001);
                    const f = toXY(filled);
                    const largeArc = (endAngle - startAngle) * (pct / 100) > Math.PI ? 1 : 0;
                    const trackPath = `M ${s.x} ${s.y} A ${radius} ${radius} 0 1 1 ${e.x} ${e.y}`;
                    const fillPath = `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${largeArc} 1 ${f.x} ${f.y}`;
                    const color = pct > 50 ? "#f59e0b" : pct > 25 ? "#a8ff00" : "#22d3ee";
                    return (
                      <svg viewBox="0 0 128 70" className="w-full h-full">
                        <path d={trackPath} fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="10" strokeLinecap="round" />
                        {pct > 0 && <path d={fillPath} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round" />}
                        <text x={cx} y={cy - 2} textAnchor="middle" fontSize="20" fontWeight="bold" fill="var(--text)" fontFamily="monospace">
                          {Math.round(pct)}%
                        </text>
                        <text x={cx} y={cy + 16} textAnchor="middle" fontSize="9" fill="var(--muted)" fontFamily="system-ui">discounted</text>
                      </svg>
                    );
                  })()}
                </div>
                <div className="flex-1 space-y-3 w-full">
                  {[
                    ["Avg Discount", formatPct(discounts.avg_discount_pct as number)],
                    ["Median Discount", formatPct(discounts.median_discount_pct as number)],
                    ["Max Discount", formatPct(discounts.max_discount_pct as number)],
                  ].map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--border)" }}>
                      <span className="text-sm" style={{ color: "var(--muted)" }}>{label}</span>
                      <span className="text-sm font-bold font-mono" style={{ color: "var(--text)" }}>{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* History tab */}
          {tab === "history" && (
            <div
              className="rounded-2xl overflow-hidden"
              style={{ border: "1px solid var(--border)" }}
            >
              <div
                className="px-5 py-4"
                style={{ background: "var(--bg3)", borderBottom: "1px solid var(--border)" }}
              >
                <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>
                  {changes.length} change{changes.length !== 1 ? "s" : ""} detected
                </h3>
              </div>
              {changes.length === 0 ? (
                <div className="px-5 py-12 text-center" style={{ background: "var(--bg-card)" }}>
                  <p className="text-sm" style={{ color: "var(--muted)" }}>
                    No changes detected yet. Check back after the next scan.
                  </p>
                </div>
              ) : (
                <div className="px-5" style={{ background: "var(--bg-card)" }}>
                  {changes.map((c) => <ChangeRow key={c.id} change={c} />)}
                </div>
              )}
            </div>
          )}

          {/* AI Insights tab */}
          {tab === "ai" && (
            <div>
              {tier === "free" ? (
                /* Upgrade gate */
                <div
                  className="rounded-2xl p-8 text-center relative overflow-hidden"
                  style={{ background: "var(--bg-card)", border: "1px solid rgba(168,255,0,.2)" }}
                >
                  <div
                    className="absolute -top-16 left-1/2 -translate-x-1/2 w-48 h-48 rounded-full blur-3xl pointer-events-none"
                    style={{ background: "rgba(168,255,0,.06)" }}
                  />
                  <div className="relative">
                    <div
                      className="w-12 h-12 rounded-2xl mx-auto mb-4 flex items-center justify-center"
                      style={{ background: "rgba(168,255,0,.1)", border: "1px solid rgba(168,255,0,.2)" }}
                    >
                      <Sparkles className="w-6 h-6" style={{ color: "var(--accent)" }} />
                    </div>
                    <h3 className="text-lg font-bold mb-2" style={{ color: "var(--text)" }}>AI Strategic Summary</h3>
                    <p className="text-sm mb-6 max-w-sm mx-auto leading-relaxed" style={{ color: "var(--muted)" }}>
                      Get weekly AI-generated insights on {hostname}&apos;s pricing strategy, launch patterns, and competitive positioning.
                    </p>
                    {/* Blurred preview */}
                    <div className="mb-6 text-left rounded-xl p-4 space-y-2 select-none pointer-events-none" style={{ background: "var(--bg3)" }}>
                      {["44.6% catalog discounted signals aggressive positioning", "Minimal 1 product monthly launch velocity", "Budget positioning with $32 median price"].map((line, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: "var(--accent)" }} />
                          <p className="text-sm blur-sm select-none" style={{ color: "var(--text-2)" }}>{line}</p>
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
              ) : !aiSummary ? (
                /* Loading state */
                <div
                  className="rounded-2xl p-6"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                >
                  <div className="flex items-center gap-2 mb-6">
                    <Sparkles className="w-5 h-5" style={{ color: "var(--accent)" }} />
                    <h3 className="font-semibold" style={{ color: "var(--text)" }}>AI Strategic Summary</h3>
                  </div>
                  <div className="space-y-3">
                    {[100, 80, 90, 65, 75].map((w, i) => (
                      <div key={i} className="h-3.5 rounded-full animate-pulse" style={{ background: "rgba(255,255,255,.06)", width: `${w}%` }} />
                    ))}
                  </div>
                  <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>Generating your AI brief…</p>
                </div>
              ) : (() => {
                /* Render based on format */
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
                      <p className="text-xs ml-auto" style={{ color: "var(--muted)" }}>
                        {formatRelativeTime(aiSummary.generated_at)}
                      </p>
                    </div>
                    {parsed.type === "cards" ? (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {parsed.cards.map((card, i) => {
                          const cfg = CARD_CONFIG[card.type] ?? CARD_CONFIG.signal;
                          return (
                            <div
                              key={i}
                              className="rounded-xl p-5"
                              style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}
                            >
                              <span
                                className="text-[10px] font-bold uppercase tracking-wider block mb-3"
                                style={{ color: cfg.color }}
                              >
                                {cfg.label}
                              </span>
                              <h4 className="font-bold text-sm mb-2 leading-snug" style={{ color: "var(--text)" }}>
                                {card.headline}
                              </h4>
                              <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
                                {card.body}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div
                        className="rounded-2xl p-5 space-y-4"
                        style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
                      >
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
        </>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
