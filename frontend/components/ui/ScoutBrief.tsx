"use client";

import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

interface ScoutBriefProps {
  competitorCount: number;
  productCount: number;
  nextScan?: string;
  onRefresh?: () => void;
  refreshing?: boolean;
}

export function ScoutBrief({ competitorCount, productCount, nextScan, onRefresh, refreshing }: ScoutBriefProps) {
  const greeting = getGreeting();

  return (
    <div
      className="flex items-center justify-between gap-4 mb-5 pb-5"
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      <div>
        <h1 className="text-2xl font-black" style={{ color: "var(--text)" }}>{greeting}</h1>
        <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 mt-1">
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            <span className="font-semibold tabular-nums" style={{ color: "var(--text-2)" }}>{competitorCount}</span>
            {" "}competitor{competitorCount !== 1 ? "s" : ""} tracked
          </span>
          {productCount > 0 && (
            <>
              <span className="text-xs" style={{ color: "var(--border)" }}>·</span>
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                <span className="font-semibold tabular-nums" style={{ color: "var(--text-2)" }}>{productCount.toLocaleString()}</span>
                {" "}products
              </span>
            </>
          )}
          {nextScan && (
            <>
              <span className="text-xs" style={{ color: "var(--border)" }}>·</span>
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                next scan in{" "}
                <span className="font-semibold" style={{ color: "var(--text-2)" }}>{nextScan}</span>
              </span>
            </>
          )}
        </div>
      </div>

      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="shrink-0 flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-lg transition-all disabled:opacity-40"
          style={{ color: "var(--muted)", border: "1px solid var(--border)", background: "transparent" }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,255,255,.04)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
        >
          <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
          {refreshing ? "Scanning…" : "Refresh all"}
        </button>
      )}
    </div>
  );
}
