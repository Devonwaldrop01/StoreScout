"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface Props {
  launchData: Record<string, unknown>;
}

export function LaunchVelocityChart({ launchData }: Props) {
  const monthly = (launchData?.monthly_distribution as Record<string, unknown>) || {};
  const counts = (monthly?.counts as Record<string, number>) || {};

  const data = Object.entries(counts)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([month, count]) => ({ month, count }));

  if (!data.length) {
    return (
      <div
        className="rounded-2xl p-8 text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <p className="text-sm" style={{ color: "var(--muted)" }}>No launch timeline data</p>
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl p-5"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <h3 className="font-semibold text-sm mb-4" style={{ color: "var(--text)" }}>
        Monthly Product Launches (last 12 months)
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
          <XAxis
            dataKey="month"
            tick={{ fill: "#7d92aa", fontSize: 10 }}
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
          <Bar dataKey="count" fill="#3b82f6" fillOpacity={0.8} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
