"use client";

import { useEffect, useState } from "react";
import { TrendingUp, Target, Eye, X, Lock } from "lucide-react";
import { competitors as api, type QuickWin, type QuickWinsResponse } from "@/lib/api";
import UpgradeModal from "@/components/UpgradeModal";

const TYPE_CONFIG = {
  opportunity: { Icon: TrendingUp, color: "#60a5fa", label: "Opportunity", bg: "rgba(96,165,250,.08)", border: "rgba(96,165,250,.2)" },
  signal:      { Icon: Target,     color: "#3b82f6", label: "Signal",      bg: "rgba(59,130,246,.08)",  border: "rgba(59,130,246,.2)"  },
  watch:       { Icon: Eye,        color: "#facc15", label: "Watch",       bg: "rgba(250,204,21,.08)", border: "rgba(250,204,21,.2)"  },
} as const;

function getStoredDismissals(competitorId: string): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(`qw_${competitorId}`) || "[]");
  } catch { return []; }
}

function storeDismissal(competitorId: string, winId: string) {
  if (typeof window === "undefined") return;
  const stored = getStoredDismissals(competitorId);
  if (!stored.includes(winId)) {
    localStorage.setItem(`qw_${competitorId}`, JSON.stringify([...stored, winId]));
  }
}

interface Props {
  competitorId: string;
}

export function QuickWins({ competitorId }: Props) {
  const [data,    setData]    = useState<QuickWinsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  useEffect(() => {
    setDismissed(getStoredDismissals(competitorId));
    api.quickWins(competitorId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [competitorId]);

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-3 w-20 rounded animate-pulse" style={{ background: "var(--bg3)" }} />
        {[1, 2].map((i) => (
          <div key={i} className="h-20 rounded-2xl animate-pulse" style={{ background: "var(--bg3)" }} />
        ))}
      </div>
    );
  }

  if (!data) return null;

  const visible = data.wins.filter((w) => !dismissed.includes(w.id));
  if (visible.length === 0 && !data.locked) return null;

  function dismiss(win: QuickWin) {
    storeDismissal(competitorId, win.id);
    setDismissed((prev) => [...prev, win.id]);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--muted)" }}>
          Quick Wins
        </p>
      </div>

      {visible.map((win) => {
        const cfg = TYPE_CONFIG[win.type] ?? TYPE_CONFIG.signal;
        const { Icon } = cfg;
        return (
          <div
            key={win.id}
            className="rounded-2xl p-4 relative"
            style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}
          >
            <div className="flex items-start gap-3 pr-6">
              <div className="rounded-lg p-1.5 shrink-0" style={{ background: `${cfg.color}18` }}>
                <Icon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
              </div>
              <div>
                <span
                  className="text-[10px] font-bold uppercase tracking-wide"
                  style={{ color: cfg.color }}
                >
                  {cfg.label}
                </span>
                <p className="text-sm font-semibold mt-0.5" style={{ color: "var(--text)" }}>
                  {win.headline}
                </p>
                <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--muted)" }}>
                  {win.detail}
                </p>
              </div>
            </div>
            <button
              onClick={() => dismiss(win)}
              className="absolute top-3 right-3 rounded-md p-1 hover:bg-white/10 transition-colors"
              style={{ color: "var(--muted)" }}
              aria-label="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}

      {data.locked && data.locked_count > 0 && (
        <div
          className="rounded-2xl p-4 flex items-center justify-between"
          style={{ background: "rgba(59,130,246,.06)", border: "1px dashed rgba(59,130,246,.25)" }}
        >
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5" style={{ color: "#3b82f6" }} />
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              {data.locked_count} more quick win{data.locked_count !== 1 ? "s" : ""} identified
            </p>
          </div>
          <button
            onClick={() => setUpgradeOpen(true)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg transition-all hover:brightness-110 shrink-0"
            style={{ background: "#3b82f6", color: "#060d18" }}
          >
            Unlock
          </button>
        </div>
      )}

      <UpgradeModal open={upgradeOpen} onClose={() => setUpgradeOpen(false)} trigger="general" />
    </div>
  );
}
