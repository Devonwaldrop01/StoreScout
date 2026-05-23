"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, RefreshCw, Trash2, Cpu, Share2, Check, Download } from "lucide-react";
import Link from "next/link";
import { competitors as api, type Snapshot, type ChangeEvent, type AiSummary } from "@/lib/api";
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

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div
      className="rounded-2xl p-4 space-y-1"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <p className="text-xs font-medium" style={{ color: "var(--muted)" }}>{label}</p>
      <p className="text-2xl font-bold font-mono" style={{ color: "var(--text)" }}>{value}</p>
      {sub && <p className="text-xs" style={{ color: "var(--muted)" }}>{sub}</p>}
    </div>
  );
}

function PositioningScore({ label, score, scoreLabel }: { label: string; score: number; scoreLabel: string }) {
  const color = score < 34 ? "#22d3ee" : score < 67 ? "#a3f000" : "#f87171";
  return (
    <div
      className="rounded-xl p-4"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <p className="text-xs mb-2" style={{ color: "var(--muted)" }}>{label}</p>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-sm" style={{ color }}>{scoreLabel}</span>
        <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>{score}/100</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,.08)" }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
    </div>
  );
}

function ChangeRow({ change }: { change: ChangeEvent }) {
  const icon = changeTypeIcon(change.change_type);
  const colorClass = severityColor(change.severity);
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

  return (
    <div
      className="flex items-start gap-3 py-3 border-b"
      style={{ borderColor: "var(--border)" }}
    >
      <span className="text-lg leading-none mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
          {change.product_title || change.change_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </p>
        {detail && <p className={cn("text-xs font-mono mt-0.5", colorClass)}>{detail}</p>}
      </div>
      <p className="text-xs shrink-0" style={{ color: "var(--muted)" }}>
        {formatRelativeTime(change.detected_at)}
      </p>
    </div>
  );
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
    }
    load();
    // Poll fast (3s) while scan is pending, slow (15s) once data loaded
    const interval = setInterval(load, scanPending ? 3000 : 15000);
    return () => clearInterval(interval);
  }, [id, scanPending]);

  useEffect(() => {
    if (tab === "ai" && !aiSummary) {
      api.aiSummary(id).then((r) => setAiSummary(r.data)).catch(() => {});
    }
  }, [tab, aiSummary, id]);

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

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link href="/dashboard" className="flex items-center gap-1.5 text-sm mb-3 hover:opacity-80 transition-opacity" style={{ color: "var(--muted)" }}>
            <ArrowLeft className="w-4 h-4" />
            Back to dashboard
          </Link>
          <h1 className="text-2xl font-bold" style={{ color: "var(--text)" }}>
            {(snapshot?.snapshot_data as Record<string, unknown>)?.hostname as string || id}
          </h1>
          {snapshot && (
            <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
              Last scanned {formatRelativeTime(snapshot.scanned_at)} · {snapshot.product_count?.toLocaleString()} products
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {snapshot && (
            <button
              onClick={handleShare}
              className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-xl transition-colors hover:bg-white/10"
              style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Share2 className="w-3.5 h-3.5" />}
              {copied ? "Copied!" : "Share"}
            </button>
          )}
          <button
            onClick={handleExportCsv}
            disabled={exporting}
            className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-xl transition-colors hover:bg-white/10 disabled:opacity-50"
            style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
          >
            <Download className="w-3.5 h-3.5" />
            {exporting ? "…" : "CSV"}
          </button>
          <button
            onClick={handleRescan}
            className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-xl transition-colors hover:bg-white/10"
            style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
          >
            <RefreshCw className={cn("w-3.5 h-3.5", rescanning && "animate-spin")} />
            Rescan
          </button>
          <button
            onClick={handleDelete}
            className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-xl transition-colors hover:bg-red-500/10"
            style={{ color: "#f87171", border: "1px solid rgba(248,113,113,.3)" }}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
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
          hostname={(snapshot?.snapshot_data as Record<string, unknown>)?.hostname as string || id}
          cards={(() => {
            try { return (JSON.parse((brief as BriefData).summary_text) as { cards: BriefCard[] }).cards; }
            catch { return []; }
          })()}
          onDismiss={handleDismissBrief}
        />
      ) : (
        <>
          {/* Tab nav */}
          <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  "px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors",
                  tab === t.id ? "text-white" : "hover:bg-white/5"
                )}
                style={
                  tab === t.id
                    ? { background: "rgba(163,240,0,.12)", color: "var(--green)" }
                    : { color: "var(--muted)" }
                }
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Overview tab */}
          {tab === "overview" && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard label="Products" value={(catalog.total_products as number)?.toLocaleString() ?? "—"} />
                <KpiCard label="Median Price" value={formatPrice(pricing.median as number)} />
                <KpiCard label="Promo Rate" value={formatPct(discounts.discounted_pct as number)} />
                <KpiCard
                  label="New (30d)"
                  value={((launch as Record<string, Record<string, Record<string, number>>>)?.launch_counts?.["30d"]?.count ?? "—").toString()}
                />
              </div>

              <QuickWins competitorId={id} />

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: "Market Position", pos: positioning.market_position as Record<string, unknown> },
                  { label: "Promo Intensity", pos: positioning.promo_intensity as Record<string, unknown> },
                  { label: "Launch Velocity", pos: positioning.launch_velocity as Record<string, unknown> },
                  { label: "Catalog Complexity", pos: positioning.catalog_complexity as Record<string, unknown> },
                ].map(({ label, pos }) => pos ? (
                  <PositioningScore
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
                  style={{ background: "rgba(59,130,246,.08)", border: "1px solid rgba(59,130,246,.2)" }}
                >
                  <h3 className="font-semibold mb-3 text-sm" style={{ color: "#93c5fd" }}>Key insights</h3>
                  <ul className="space-y-2">
                    {takeaways.map((t, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm" style={{ color: "#bfdbfe" }}>
                        <span className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                        {t}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {changes.length > 0 && (
                <div
                  className="rounded-2xl p-5"
                  style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
                >
                  <h3 className="font-semibold mb-3 text-sm" style={{ color: "var(--text)" }}>Recent changes</h3>
                  {changes.slice(0, 5).map((c) => <ChangeRow key={c.id} change={c} />)}
                  {changes.length > 5 && (
                    <button
                      onClick={() => setTab("history")}
                      className="mt-3 text-sm hover:underline"
                      style={{ color: "var(--blue)" }}
                    >
                      View all {changes.length} changes →
                    </button>
                  )}
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
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  ["Discounted", formatPct(discounts.discounted_pct as number)],
                  ["Avg Discount", formatPct(discounts.avg_discount_pct as number)],
                  ["Median Discount", formatPct(discounts.median_discount_pct as number)],
                  ["Max Discount", formatPct(discounts.max_discount_pct as number)],
                ].map(([label, value]) => (
                  <KpiCard key={label} label={label} value={value} />
                ))}
              </div>
            </div>
          )}

          {/* History tab */}
          {tab === "history" && (
            <div
              className="rounded-2xl p-5"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              {changes.length === 0 ? (
                <p className="text-sm text-center py-8" style={{ color: "var(--muted)" }}>
                  No changes detected yet. Check back after the next scan.
                </p>
              ) : (
                <>
                  <h3 className="font-semibold mb-4 text-sm" style={{ color: "var(--text)" }}>
                    {changes.length} change{changes.length !== 1 ? "s" : ""} detected
                  </h3>
                  {changes.map((c) => <ChangeRow key={c.id} change={c} />)}
                </>
              )}
            </div>
          )}

          {/* AI Insights tab */}
          {tab === "ai" && (
            <div
              className="rounded-2xl p-6"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
            >
              <div className="flex items-center gap-2 mb-4">
                <Cpu className="w-5 h-5" style={{ color: "var(--green)" }} />
                <h3 className="font-semibold" style={{ color: "var(--text)" }}>AI Strategic Summary</h3>
              </div>
              {!aiSummary ? (
                <div className="space-y-2">
                  <div className="h-4 rounded animate-pulse w-full" style={{ background: "rgba(255,255,255,.06)" }} />
                  <div className="h-4 rounded animate-pulse w-4/5" style={{ background: "rgba(255,255,255,.06)" }} />
                  <div className="h-4 rounded animate-pulse w-3/5" style={{ background: "rgba(255,255,255,.06)" }} />
                </div>
              ) : (
                <>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--text)" }}>
                    {aiSummary.summary_text}
                  </p>
                  <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>
                    Generated {formatRelativeTime(aiSummary.generated_at)} · {aiSummary.model}
                  </p>
                </>
              )}
            </div>
          )}
        </>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
