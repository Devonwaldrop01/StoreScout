"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface Props {
  pricingData: Record<string, unknown>;
}

export function PriceDistributionChart({ pricingData }: Props) {
  const buckets = (pricingData?.price_buckets as Record<string, unknown>) || {};
  const bucketData = (buckets?.buckets as Record<string, number>) || {};
  const bucketOrder = (buckets?.bucket_order as string[]) || Object.keys(bucketData);

  const data = bucketOrder
    .filter((key) => key in bucketData)
    .map((key) => ({ name: key, count: bucketData[key] || 0 }));

  if (!data.length) {
    return (
      <div
        className="panel p-8 text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <p className="text-sm" style={{ color: "var(--muted)" }}>No pricing data available</p>
      </div>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count));
  const totalCount = data.reduce((sum, d) => sum + d.count, 0);
  const dominantEntry = data.find((d) => d.count === maxCount);
  const dominantPct = totalCount > 0 && dominantEntry
    ? Math.round((dominantEntry.count / totalCount) * 100)
    : 0;

  return (
    <div
      className="panel p-5"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <div className="mb-4">
        <h3 className="tick-label">Price distribution</h3>
        <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
          {totalCount} products across {data.length} price bands
        </p>
        {dominantEntry && (
          <span
            className="inline-flex items-center text-[11px] font-semibold px-2.5 py-1 rounded mt-2"
            style={{ background: "var(--bg3)", color: "var(--text-2)", border: "1px solid var(--border)" }}
          >
            Dominant band: {dominantEntry.name} · {dominantPct}% of products
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
          <XAxis
            dataKey="name"
            tick={{ fill: "#6C7164", fontSize: 10, fontFamily: "var(--font-mono)" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#6C7164", fontSize: 10, fontFamily: "var(--font-mono)" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "#161814",
              border: "1px solid #262A22",
              borderRadius: 6,
              color: "#ECEEE6",
              fontSize: 12,
              fontFamily: "var(--font-mono)",
            }}
            cursor={{ fill: "rgba(255,255,255,.04)" }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.count === maxCount ? "#FFB224" : "#4A4E44"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
