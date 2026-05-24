"use client";

import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from "recharts";
import { Lock } from "lucide-react";
import { competitors as api, type PriceHistoryResponse } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

interface Props {
  competitorId: string;
}

export function PriceHistoryChart({ competitorId }: Props) {
  const [data, setData] = useState<PriceHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  useEffect(() => {
    api.priceHistory(competitorId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

  if (loading) {
    return <div className="h-64 rounded-2xl animate-pulse" style={{ background: "var(--bg-card)" }} />;
  }

  if (!data || !data.points || data.points.length < 2) {
    return (
      <div
        className="rounded-2xl p-8 text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Price history builds over time — check back after a few more scans.
        </p>
      </div>
    );
  }

  const chartData = data.points.map((p) => ({
    date: new Date(p.scanned_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    median_price: p.median_price != null ? Number(p.median_price) : null,
    promo_rate: p.promo_rate != null ? Number(p.promo_rate) : null,
  }));

  return (
    <div
      className="rounded-2xl p-5 relative overflow-hidden"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm" style={{ color: "var(--text)" }}>Price History</h3>
        <div className="flex items-center gap-4 text-xs" style={{ color: "var(--muted)" }}>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-0.5 rounded" style={{ background: "#a3f000" }} />
            Median price
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-0.5 rounded" style={{ background: "#facc15" }} />
            Promo rate
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, left: -20, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.04)" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#7d92aa", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            yAxisId="price"
            tick={{ fill: "#7d92aa", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `$${v}`}
          />
          <YAxis
            yAxisId="pct"
            orientation="right"
            tick={{ fill: "#7d92aa", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              background: "#0e1d35",
              border: "1px solid rgba(255,255,255,.09)",
              borderRadius: 10,
              color: "#eef3fa",
              fontSize: 13,
            }}
            formatter={(value, name) =>
              name === "median_price" ? [`$${value}`, "Median price"] : [`${value}%`, "Promo rate"]
            }
          />
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="median_price"
            stroke="#a3f000"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="promo_rate"
            stroke="#facc15"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>

      {data.locked && (
        <div
          className="absolute inset-0 flex flex-col items-center justify-end pb-8 rounded-2xl"
          style={{
            background: "linear-gradient(to top, rgba(6,13,24,.97) 40%, rgba(6,13,24,0) 100%)",
          }}
        >
          <Lock className="w-5 h-5 mb-2" style={{ color: "#a3f000" }} />
          <p className="text-sm font-medium mb-1" style={{ color: "var(--text)" }}>
            {data.locked_count > 0
              ? `${data.locked_count} more scan${data.locked_count !== 1 ? "s" : ""} in history`
              : "Full history locked"}
          </p>
          <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
            Unlock 90 days of price &amp; promo history with Pro
          </p>
          <button
            onClick={() => setUpgradeOpen(true)}
            className="font-semibold text-sm px-5 py-2.5 rounded-xl transition-all hover:brightness-110"
            style={{ background: "#a3f000", color: "#060d18" }}
          >
            Unlock Price History
          </button>
        </div>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
