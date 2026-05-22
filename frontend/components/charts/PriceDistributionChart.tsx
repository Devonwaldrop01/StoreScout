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
        className="rounded-2xl p-8 text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <p className="text-sm" style={{ color: "var(--muted)" }}>No pricing data available</p>
      </div>
    );
  }

  const maxCount = Math.max(...data.map((d) => d.count));

  return (
    <div
      className="rounded-2xl p-5"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <h3 className="font-semibold text-sm mb-4" style={{ color: "var(--text)" }}>
        Price Distribution
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
          <XAxis
            dataKey="name"
            tick={{ fill: "#7d92aa", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#7d92aa", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "#0e1d35",
              border: "1px solid rgba(255,255,255,.09)",
              borderRadius: 10,
              color: "#eef3fa",
              fontSize: 13,
            }}
            cursor={{ fill: "rgba(255,255,255,.04)" }}
          />
          <Bar dataKey="count" radius={[6, 6, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.count === maxCount ? "#a3f000" : "#3b82f6"}
                fillOpacity={entry.count === maxCount ? 1 : 0.6}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
