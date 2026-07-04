"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

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
        className="panel p-8 text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <p className="text-sm" style={{ color: "var(--muted)" }}>No launch timeline data</p>
      </div>
    );
  }

  // Trend: compare last 3 months avg vs prior 3 months avg
  const last3 = data.slice(-3).map((d) => d.count);
  const prior3 = data.slice(-6, -3).map((d) => d.count);
  const last3Avg = last3.length > 0 ? last3.reduce((s, v) => s + v, 0) / last3.length : 0;
  const prior3Avg = prior3.length > 0 ? prior3.reduce((s, v) => s + v, 0) / prior3.length : 0;

  let trendLabel = "→ Stable";
  let trendColor = "var(--muted)";
  if (prior3Avg > 0) {
    const changePct = ((last3Avg - prior3Avg) / prior3Avg) * 100;
    if (changePct > 10) {
      trendLabel = "↑ Accelerating";
      trendColor = "var(--emerald)";
    } else if (changePct < -10) {
      trendLabel = "↓ Decelerating";
      trendColor = "var(--red)";
    }
  }

  const mostRecentCount = data[data.length - 1]?.count ?? 0;
  const lastIndex = data.length - 1;

  return (
    <div
      className="panel p-5"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <div className="mb-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="tick-label">Monthly launches · 12 mo</h3>
          <span className="num text-xs font-semibold shrink-0" style={{ color: trendColor }}>
            {trendLabel}
          </span>
        </div>
        <p className="num text-xs mt-1 font-semibold" style={{ color: "var(--accent)" }}>
          {mostRecentCount} new this month
        </p>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
          <XAxis
            dataKey="month"
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
          <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={28}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={index === lastIndex ? "#FFB224" : "#C47F00"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
