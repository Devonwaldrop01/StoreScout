"use client";

import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine,
} from "recharts";
import { Lock, Zap } from "lucide-react";
import { competitors as api, type PriceHistoryResponse } from "@/lib/api";

// Demo data shown to free users who haven't accumulated enough scans.
// Tells a recognizable ecommerce story: stable pricing → Black Friday sale →
// holiday period → post-holiday normalization.
const DEMO_DATA = [
  { date: "Nov 4",  median_price: 52.99, promo_rate: 18 },
  { date: "Nov 11", median_price: 54.50, promo_rate: 22 },
  { date: "Nov 18", median_price: 53.00, promo_rate: 28 },
  { date: "Nov 25", median_price: 44.99, promo_rate: 61 },
  { date: "Dec 2",  median_price: 46.00, promo_rate: 45 },
  { date: "Dec 9",  median_price: 51.00, promo_rate: 24 },
  { date: "Dec 16", median_price: 52.00, promo_rate: 28 },
  { date: "Dec 23", median_price: 48.50, promo_rate: 35 },
  { date: "Dec 30", median_price: 53.99, promo_rate: 19 },
  { date: "Jan 6",  median_price: 55.00, promo_rate: 15 },
  { date: "Jan 13", median_price: 54.50, promo_rate: 17 },
  { date: "Jan 20", median_price: 56.00, promo_rate: 14 },
];

interface Props {
  competitorId: string;
  isFree?: boolean;
  onUpgrade?: () => void;
}

const CHART_STYLE = {
  contentStyle: {
    background: "#161814",
    border: "1px solid #262A22",
    borderRadius: 6,
    color: "#ECEEE6",
    fontSize: 12,
    fontFamily: "var(--font-mono)",
  },
};

// Data-series colors — validated against surface #101110 (dataviz six checks).
const SERIES_AMBER = "#C47F00";
const SERIES_CYAN  = "#2F9FC9";

/** Two stacked single-axis panels sharing the same dates — never a dual-axis chart. */
function Chart({ chartData, showBFLine = false }: {
  chartData: { date: string; median_price: number | null; promo_rate: number | null }[];
  showBFLine?: boolean;
}) {
  return (
    <div>
      <p className="label-caps px-1 mb-1">Median price</p>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" vertical={false} />
          <XAxis dataKey="date" tick={false} axisLine={false} tickLine={false} height={4} />
          <YAxis tick={{ fill: "#6C7164", fontSize: 10, fontFamily: "var(--font-mono)" }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} width={52} />
          <Tooltip {...CHART_STYLE} formatter={(value) => [`$${value}`, "Median price"]} />
          {showBFLine && (
            <ReferenceLine x="Nov 25" stroke="rgba(242,85,90,.4)" strokeDasharray="4 2"
              label={{ value: "BF", position: "top", fill: "#F2555A", fontSize: 9 }}
            />
          )}
          <Line type="monotone" dataKey="median_price" stroke={SERIES_AMBER} strokeWidth={2} dot={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
      <p className="label-caps px-1 mt-2 mb-1">Promo rate</p>
      <ResponsiveContainer width="100%" height={90}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, left: -20, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: "#6C7164", fontSize: 10, fontFamily: "var(--font-mono)" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#6C7164", fontSize: 10, fontFamily: "var(--font-mono)" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} width={52} />
          <Tooltip {...CHART_STYLE} formatter={(value) => [`${value}%`, "Promo rate"]} />
          <Line type="monotone" dataKey="promo_rate" stroke={SERIES_CYAN} strokeWidth={2} dot={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PriceHistoryChart({ competitorId, isFree = true, onUpgrade }: Props) {
  const [data, setData] = useState<PriceHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    setFetchError(false);
    api.priceHistory(competitorId)
      .then((r) => setData(r.data))
      .catch(() => setFetchError(true))
      .finally(() => setLoading(false));
  }, [competitorId]);

  if (loading) {
    return <div className="h-64 rounded-md animate-pulse" style={{ background: "var(--bg3)" }} />;
  }

  // Paid user but API call failed — show a neutral message, not the paywall
  if (!isFree && (fetchError || !data || !data.locked)) {
    if (fetchError || !data) {
      return (
        <div className="rounded-md px-5 py-8 text-center" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Price history builds over time — check back after a few more daily scans.
          </p>
        </div>
      );
    }
  }

  // ── Paid: full chart ────────────────────────────────────────────────────────
  if (data && !data.locked) {
    const chartData = data.points.map((p) => ({
      date: new Date(p.scanned_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      median_price: p.median_price != null ? Number(p.median_price) : null,
      promo_rate: p.promo_rate != null ? Number(p.promo_rate) : null,
    }));

    if (chartData.length < 2) {
      return (
        <div className="rounded-md px-5 py-8 text-center" style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Price history builds over time — check back after a few more scans.
          </p>
        </div>
      );
    }

    return (
      <div>
        <Chart chartData={chartData} />
      </div>
    );
  }

  // ── Locked: show real partial data if ≥ 2 points, otherwise demo ───────────
  const hasPartialData = data && data.points.length >= 2;
  const chartData = hasPartialData
    ? data!.points.map((p) => ({
        date: new Date(p.scanned_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        median_price: p.median_price != null ? Number(p.median_price) : null,
        promo_rate: p.promo_rate != null ? Number(p.promo_rate) : null,
      }))
    : DEMO_DATA;

  const lockedCount = data?.locked_count ?? 0;

  return (
    <div className="relative rounded-md overflow-hidden" style={{ border: "1px solid var(--border)" }}>
      {/* Legend */}
      <div className="flex items-center justify-between px-5 pt-4 pb-2">
        <p className="label-caps">Price & promo history</p>
        {!hasPartialData && (
          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: "rgba(255,178,36,.1)", color: "var(--accent)" }}>
            Example
          </span>
        )}
      </div>

      {/* Chart (intentionally rendered behind the overlay) */}
      <div className="px-1 pb-2" style={{ opacity: 0.35, filter: "blur(1px)" }}>
        <Chart chartData={chartData} showBFLine={!hasPartialData} />
      </div>

      {/* Lock overlay — gradient from bottom, but lets the top data breathe */}
      <div
        className="absolute inset-0"
        style={{ background: "linear-gradient(to top, rgba(11,12,10,1) 38%, rgba(11,12,10,.6) 62%, transparent 100%)" }}
      />

      {/* CTA */}
      <div className="absolute bottom-0 left-0 right-0 flex flex-col items-center pb-6 px-6 text-center">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center mb-3"
          style={{ background: "rgba(255,178,36,.1)", border: "1px solid rgba(255,178,36,.2)" }}
        >
          <Lock className="w-4 h-4" style={{ color: "var(--accent)" }} />
        </div>
        <p className="text-sm font-semibold mb-1" style={{ color: "var(--text)" }}>
          {lockedCount > 0
            ? `${lockedCount} more scan${lockedCount !== 1 ? "s" : ""} in history`
            : "90-day price & promo history"}
        </p>
        <p className="text-xs mb-4 max-w-xs" style={{ color: "var(--muted)" }}>
          {hasPartialData
            ? "See how their pricing strategy has evolved over the past 90 days."
            : "Catch flash sales, gradual price increases, and seasonal discount patterns."}
        </p>
        <button
          onClick={onUpgrade}
          className="flex items-center gap-1.5 font-bold text-sm px-5 py-2.5 rounded-md transition-all hover:brightness-110"
          style={{ background: "var(--accent)", color: "var(--ink)" }}
        >
          <Zap className="w-3.5 h-3.5" />
          Unlock history — $29/mo
        </button>
      </div>
    </div>
  );
}
