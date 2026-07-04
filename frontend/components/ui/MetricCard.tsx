"use client";

import { AreaChart, Area, ResponsiveContainer } from "recharts";

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: number | null;
  deltaLabel?: string;
  deltaText?: string;       // fully custom delta text, overrides computed delta
  color?: string;
  icon?: React.ElementType;
  sparkline?: number[];
}

export function MetricCard({ label, value, delta, deltaLabel = "vs last week", deltaText, color = "var(--accent)", icon: Icon, sparkline }: MetricCardProps) {
  function renderDelta() {
    if (deltaText) {
      return <span className="text-[10px]" style={{ color: "var(--muted)" }}>{deltaText}</span>;
    }
    if (delta === null || delta === undefined) return null;
    const up = delta > 0;
    const down = delta < 0;
    const arrow = up ? "↑" : down ? "↓" : "→";
    const abs = Math.abs(delta);
    return (
      <span className="text-[10px]" style={{ color: "var(--muted)" }}>
        {arrow}{abs}% {deltaLabel}
      </span>
    );
  }

  return (
    <div
      className="rounded-xl px-4 py-3.5"
      style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-2xl font-bold font-mono leading-none tracking-tight" style={{ color: "var(--text)" }}>
            {value}
          </p>
          <p className="text-[11px] mt-1.5 truncate" style={{ color: "var(--muted)" }}>{label}</p>
          {renderDelta()}
        </div>
        {Icon && (
          <div className="w-7 h-7 rounded-md flex items-center justify-center shrink-0" style={{ background: `${color}14` }}>
            <Icon className="w-3.5 h-3.5" style={{ color }} />
          </div>
        )}
      </div>
      {sparkline && sparkline.some((v) => v > 0) && (
        <div className="mt-2 -mx-1">
          <ResponsiveContainer width="100%" height={28}>
            <AreaChart data={sparkline.map((v, i) => ({ v, i }))} margin={{ top: 1, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="mc-spark" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FFB224" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#FFB224" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke="#FFB224" strokeWidth={1.5}
                fill="url(#mc-spark)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
