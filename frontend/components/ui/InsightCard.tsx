"use client";

/**
 * The recognizable intelligence card — StoreScout's one recommendation motif.
 * Left tick in the category color, icon chip, label-caps category, headline,
 * body. Used wherever an insight is presented as a card (briefs, reveal,
 * landing mocks) so the language reads identically everywhere.
 */

import { INSIGHT_LANGUAGE, insightKind } from "@/lib/insight";

export function InsightCard({
  type, headline, body, className = "", prominent = false, children,
}: {
  type: string;
  headline: string;
  body?: string;
  className?: string;
  /** Larger icon treatment for the act-now / hero card */
  prominent?: boolean;
  children?: React.ReactNode;
}) {
  const cfg = INSIGHT_LANGUAGE[insightKind(type)];
  const { Icon } = cfg;

  return (
    <div
      className={`rounded-md ${prominent ? "p-5" : "p-4"} ${className}`}
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${cfg.color}`,
      }}
    >
      <div className={`flex items-center gap-2 ${prominent ? "mb-3" : "mb-2"}`}>
        <div
          className={`${prominent ? "w-8 h-8" : "w-6 h-6"} rounded-md flex items-center justify-center shrink-0`}
          style={{ background: `${cfg.color}14` }}
        >
          <Icon className={prominent ? "w-4 h-4" : "w-3.5 h-3.5"} style={{ color: cfg.color }} />
        </div>
        <span className="label-caps" style={{ color: cfg.color }}>{cfg.label}</span>
      </div>
      <h4 className="font-semibold text-sm leading-snug mb-1.5" style={{ color: "var(--text)" }}>
        {headline}
      </h4>
      {body && (
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-2)" }}>
          {body}
        </p>
      )}
      {children}
    </div>
  );
}
