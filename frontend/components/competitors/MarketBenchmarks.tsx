"use client";

/**
 * Market Benchmarks — where this competitor sits versus its category's norms,
 * computed from StoreScout's verified store index. Turns a raw number into
 * market understanding: "priced 34% above the Fitness Apparel average."
 */

import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { competitors as api, type BenchmarksData, type BenchmarkItem } from "@/lib/api";

function fmt(v: number, unit: string) {
  if (unit === "$") return `$${Math.round(v).toLocaleString()}`;
  if (unit === "%") return `${Math.round(v)}%`;
  return Math.round(v).toLocaleString();
}

function Row({ b }: { b: BenchmarkItem }) {
  const pct = Math.max(2, Math.min(100, b.percentile));
  const above = b.diff_pct >= 8;
  const below = b.diff_pct <= -8;
  const color = above ? "#FFB224" : below ? "#7DB8C9" : "#4CC38A";
  // Marker position for the category average on the 0–100 percentile track ≈ 50th.
  return (
    <div className="py-3" style={{ borderTop: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-medium" style={{ color: "var(--text)" }}>{b.label}</span>
        <span className="num text-sm font-bold" style={{ color }}>
          {fmt(b.value, b.unit)}
          <span className="text-[11px] font-normal ml-1.5" style={{ color: "var(--muted)" }}>vs {fmt(b.average, b.unit)} avg</span>
        </span>
      </div>
      {/* Percentile track with the category-average marker at ~50% */}
      <div className="relative h-2 rounded-full" style={{ background: "var(--bg3)" }}>
        <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${pct}%`, background: color }} />
        <div className="absolute inset-y-[-2px] w-px" style={{ left: "50%", background: "var(--muted)" }} title="category average" />
      </div>
      <p className="text-[11px] mt-1" style={{ color: "var(--muted)" }}>{b.read}</p>
    </div>
  );
}

export function MarketBenchmarks({ competitorId }: { competitorId: string }) {
  const [data, setData] = useState<BenchmarksData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.benchmarks(competitorId).then((r) => setData(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, [competitorId]);

  if (loading) return <div className="h-40 rounded-md animate-pulse" style={{ background: "var(--bg-card)" }} />;
  if (!data || !data.category || data.benchmarks.length === 0) return null;

  return (
    <div className="rounded-md p-4 sm:p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2 mb-1">
        <BarChart3 className="w-4 h-4" style={{ color: "var(--accent)" }} />
        <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>Where they sit in {data.category}</h3>
      </div>
      <p className="text-[11px] mb-2" style={{ color: "var(--muted)" }}>
        Benchmarked against {data.sample_size ?? "verified"} {data.category} stores in StoreScout&apos;s index. The tick marks the category average.
      </p>
      <div>
        {data.benchmarks.map((b) => <Row key={b.key} b={b} />)}
      </div>
    </div>
  );
}
