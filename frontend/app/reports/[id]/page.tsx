"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { Zap, Share2, Check, ArrowRight } from "lucide-react";
import { reports, type PublicReport } from "@/lib/api";
import { formatRelativeTime, formatPrice, formatPct } from "@/lib/utils";
import { PriceDistributionChart } from "@/components/charts/PriceDistributionChart";

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl p-4 space-y-1" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <p className="text-xs font-medium" style={{ color: "var(--muted)" }}>{label}</p>
      <p className="text-2xl font-bold font-mono" style={{ color: "var(--text)" }}>{value}</p>
    </div>
  );
}

function PositioningBar({ label, pos }: { label: string; pos: Record<string, unknown> | undefined }) {
  if (!pos) return null;
  const score = (pos.score as number) ?? 50;
  const scoreLabel = (pos.label as string) ?? "—";
  const color = score < 34 ? "#22d3ee" : score < 67 ? "#a3f000" : "#f87171";
  return (
    <div className="rounded-xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <p className="text-xs mb-2" style={{ color: "var(--muted)" }}>{label}</p>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-sm" style={{ color }}>{scoreLabel}</span>
        <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>{score}/100</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,.08)" }}>
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: color }} />
      </div>
    </div>
  );
}

export default function PublicReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [report, setReport] = useState<PublicReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    reports.get(id)
      .then((r) => setReport(r.data))
      .catch((e) => {
        if (e?.status === 404) setNotFound(true);
      })
      .finally(() => setLoading(false));
  }, [id]);

  function handleShare() {
    navigator.clipboard.writeText(window.location.href).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}>
        <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--green)" }} />
      </div>
    );
  }

  if (notFound || !report) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center px-6" style={{ background: "var(--bg)" }}>
        <p className="text-xl font-bold mb-2" style={{ color: "var(--text)" }}>Report not found</p>
        <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>This link may have expired or be invalid.</p>
        <Link
          href="/auth/signup"
          className="flex items-center gap-2 font-semibold px-6 py-3 rounded-xl transition-all hover:brightness-110"
          style={{ background: "#a3f000", color: "#060d18" }}
        >
          Track your own competitors free
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    );
  }

  const { hostname, scanned_at, product_count, pricing, discounts, launch, positioning, takeaways } = report;

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      {/* Nav */}
      <nav
        className="flex items-center justify-between px-6 py-4 border-b"
        style={{ borderColor: "var(--border)", background: "var(--bg2)" }}
      >
        <Link href="/" className="flex items-center gap-2">
          <Zap className="w-5 h-5" style={{ color: "#a3f000" }} />
          <span className="font-bold" style={{ color: "var(--text)" }}>StoreScout</span>
        </Link>
        <div className="flex items-center gap-3">
          <button
            onClick={handleShare}
            className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-xl transition-colors hover:bg-white/10"
            style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
          >
            {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Share2 className="w-3.5 h-3.5" />}
            {copied ? "Copied!" : "Share"}
          </button>
          <Link
            href="/auth/signup"
            className="text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Track your competitors
          </Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="mb-8">
          <div
            className="inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full mb-4"
            style={{ background: "rgba(163,240,0,.1)", color: "#a3f000", border: "1px solid rgba(163,240,0,.2)" }}
          >
            <span className="w-2 h-2 rounded-full bg-current" />
            StoreScout Intelligence Report
          </div>
          <h1 className="text-3xl font-black mb-1" style={{ color: "var(--text)", letterSpacing: "-0.03em" }}>
            {hostname}
          </h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Scanned {formatRelativeTime(scanned_at)} · {product_count?.toLocaleString() ?? "—"} products analyzed
          </p>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <KpiCard label="Products" value={product_count?.toLocaleString() ?? "—"} />
          <KpiCard label="Median Price" value={formatPrice(pricing.median)} />
          <KpiCard label="Promo Rate" value={formatPct(discounts.discounted_pct)} />
          <KpiCard label="New (30d)" value={launch.new_30d?.toString() ?? "—"} />
        </div>

        {/* Positioning scores */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          <PositioningBar label="Market Position" pos={positioning.market_position as Record<string, unknown>} />
          <PositioningBar label="Promo Intensity" pos={positioning.promo_intensity as Record<string, unknown>} />
          <PositioningBar label="Launch Velocity" pos={positioning.launch_velocity as Record<string, unknown>} />
          <PositioningBar label="Catalog Complexity" pos={positioning.catalog_complexity as Record<string, unknown>} />
        </div>

        {/* Price distribution */}
        {Object.keys(pricing.bucket_counts).length > 0 && (
          <div className="mb-8">
            <PriceDistributionChart pricingData={pricing as Record<string, unknown>} />
          </div>
        )}

        {/* Pricing stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
          {[
            ["Min", formatPrice(pricing.min)],
            ["P25", formatPrice(pricing.p25)],
            ["Median", formatPrice(pricing.median)],
            ["P75", formatPrice(pricing.p75)],
            ["Max", formatPrice(pricing.max)],
          ].map(([label, value]) => (
            <KpiCard key={label} label={label} value={value} />
          ))}
        </div>

        {/* Key takeaways */}
        {takeaways.length > 0 && (
          <div
            className="rounded-2xl p-5 mb-8"
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

        {/* CTA */}
        <div
          className="rounded-2xl p-8 text-center"
          style={{ background: "rgba(163,240,0,.05)", border: "1px solid rgba(163,240,0,.2)" }}
        >
          <h2 className="text-xl font-bold mb-2" style={{ color: "var(--text)" }}>
            Track {hostname} yourself
          </h2>
          <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
            Get alerted when they change prices, launch products, or run discounts. Free to start.
          </p>
          <Link
            href="/auth/signup"
            className="inline-flex items-center gap-2 font-bold px-6 py-3 rounded-xl transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Start tracking free
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Footer attribution */}
        <div className="mt-8 flex items-center justify-center gap-2 text-xs" style={{ color: "var(--muted)" }}>
          <span>Powered by</span>
          <Link href="/" className="flex items-center gap-1 font-semibold hover:opacity-80" style={{ color: "#a3f000" }}>
            <Zap className="w-3 h-3" />
            StoreScout
          </Link>
          <span>· Shopify competitor intelligence</span>
        </div>
      </div>
    </div>
  );
}
