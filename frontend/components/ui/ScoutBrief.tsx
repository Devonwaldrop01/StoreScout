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
  firstName?: string | null;
  competitorCount: number;
  lastScan?: string;
  nextScan?: string;
  changesThisWeek: number;
  requireAction: number;
  onRefresh?: () => void;
  refreshing?: boolean;
  refreshLabel?: string;   // truthful aggregate ("2 running · 1 done"), no fake %
}

export function ScoutBrief({ firstName, competitorCount, lastScan, nextScan, changesThisWeek, requireAction, onRefresh, refreshing, refreshLabel }: ScoutBriefProps) {
  const greeting = firstName ? `${getGreeting()}, ${firstName}` : getGreeting();

  const metaLine = (
    <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
      <span className="text-xs" style={{ color: "var(--muted)" }}>
        <span className="font-semibold tabular-nums" style={{ color: "var(--text-2)" }}>{competitorCount}</span>
        {" "}competitor{competitorCount !== 1 ? "s" : ""} tracked
      </span>
      {lastScan && (
        <>
          <span className="text-xs" style={{ color: "var(--border)" }}>·</span>
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            last scan{" "}
            <span className="font-semibold" style={{ color: "var(--text-2)" }}>{lastScan}</span>
          </span>
        </>
      )}
      {nextScan && (
        <>
          <span className="text-xs" style={{ color: "var(--border)" }}>·</span>
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            next in{" "}
            <span className="font-semibold" style={{ color: "var(--text-2)" }}>{nextScan}</span>
          </span>
        </>
      )}
    </div>
  );

  return (
    <div
      className="flex items-center justify-between gap-4 mb-5 pb-5"
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      <div className="min-w-0">
        <p className="tick-label mb-2">
          Daily brief · {new Date().toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
        </p>
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: "var(--text)" }}>{greeting}</h1>
        <div className="mt-1.5">
          {changesThisWeek > 0 && requireAction > 0 ? (
            <p className="text-sm leading-snug" style={{ color: "var(--text-2)" }}>
              Your competitors generated{" "}
              <span className="font-bold" style={{ color: "var(--text)" }}>{changesThisWeek} changes</span>{" "}
              this week —{" "}
              <span className="font-bold" style={{ color: "var(--red)" }}>{requireAction} require action</span>.
            </p>
          ) : changesThisWeek > 0 ? (
            <p className="text-sm leading-snug" style={{ color: "var(--text-2)" }}>
              <span className="font-bold" style={{ color: "var(--text)" }}>{changesThisWeek} changes</span>{" "}
              across your competitors this week — nothing needs action right now.
            </p>
          ) : (
            <p className="text-sm leading-snug" style={{ color: "var(--muted)" }}>
              All quiet across your{" "}
              <span className="font-semibold" style={{ color: "var(--text-2)" }}>{competitorCount}</span>{" "}
              competitor{competitorCount !== 1 ? "s" : ""} this week.
            </p>
          )}
          <div className="mt-1">{metaLine}</div>
        </div>
      </div>

      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className={cn(
            "shrink-0 flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded transition-colors disabled:opacity-40 hover:bg-white/[.04]",
            refreshing && "scan-shimmer"
          )}
          style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
        >
          <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
          {refreshing ? (refreshLabel || "Scanning…") : "Rescan all"}
        </button>
      )}
    </div>
  );
}
