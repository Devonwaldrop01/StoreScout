"use client";

import { X, ArrowRight } from "lucide-react";
import Link from "next/link";

type ActionCardType = "threat" | "opportunity" | "gap";

const TYPE_CONFIG: Record<ActionCardType, { color: string; label: string }> = {
  threat:      { color: "var(--red)",     label: "Threat" },
  opportunity: { color: "var(--emerald)", label: "Opportunity" },
  gap:         { color: "#7c8aa0",        label: "Gap" },
};

interface ActionCardProps {
  type: ActionCardType;
  headline: string;
  action_text: string;
  context?: string;
  hostname: string;
  competitor_id: string;
  tab?: string;
  onDismiss?: () => void;
}

export function ActionCard({ type, headline, action_text, context, hostname, competitor_id, tab, onDismiss }: ActionCardProps) {
  const cfg = TYPE_CONFIG[type] ?? TYPE_CONFIG.opportunity;
  return (
    <div
      className="relative rounded-xl p-4 flex flex-col fade-in"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderLeft: `3px solid ${cfg.color}` }}
    >
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="absolute top-3 right-3 p-0.5 rounded opacity-40 hover:opacity-80 transition-opacity"
          style={{ color: "var(--muted)" }}
          aria-label="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}

      <div className="flex items-center gap-2 mb-2.5 pr-5">
        <span className="label-caps" style={{ color: cfg.color }}>{cfg.label}</span>
        <span className="text-[11px] truncate" style={{ color: "var(--muted)" }}>{hostname}</span>
      </div>

      <p className="text-xs font-semibold leading-snug mb-1.5 line-clamp-2" style={{ color: "var(--text)" }}>
        {headline}
      </p>

      <p className="text-[11px] leading-relaxed mb-3 flex-1 line-clamp-3" style={{ color: "var(--muted)" }}>
        {action_text}
      </p>

      <div className="flex items-center justify-between">
        <span className="text-[10px]" style={{ color: "var(--muted)" }}>{context}</span>
        <Link
          href={`/dashboard/${competitor_id}?tab=${tab ?? "overview"}`}
          className="flex items-center gap-1 text-[11px] font-semibold transition-opacity hover:opacity-70"
          style={{ color: "var(--accent)" }}
        >
          View <ArrowRight className="w-2.5 h-2.5" />
        </Link>
      </div>
    </div>
  );
}
