"use client";

/**
 * Expanded 4-card brief layout. Rendered on the landing page as a marketing
 * component; uses the shared intelligence language so the marketing motif is
 * pixel-identical to the in-app one.
 */

import { Sparkles, ArrowRight, X, Zap } from "lucide-react";
import { type BriefCard } from "@/lib/api";
import { INSIGHT_LANGUAGE } from "@/lib/insight";
import { InsightCard } from "@/components/ui/InsightCard";

interface Props {
  hostname: string;
  cards: BriefCard[];
  onDismiss: () => void;
}

export function IntelligenceBrief({ hostname, cards, onDismiss }: Props) {
  const actionCard = cards.find((c) => c.type === "action");
  const action = INSIGHT_LANGUAGE.action;

  return (
    <div
      className="rounded-md overflow-hidden mb-8 fade-in"
      style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
    >
      <div className="p-6 sm:p-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
              style={{ background: "rgba(255,178,36,.10)", border: "1px solid var(--border)" }}
            >
              <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
            </div>
            <div>
              <span className="label-caps" style={{ color: "var(--accent)" }}>Scout Brief</span>
              <h3 className="text-sm font-bold mt-0.5" style={{ color: "var(--text)" }}>
                <span style={{ color: "var(--text-2)" }}>{hostname}</span>
              </h3>
            </div>
          </div>

          <button
            onClick={onDismiss}
            className="p-1.5 rounded-lg transition-colors hover:bg-white/10 shrink-0"
            style={{ color: "var(--muted)" }}
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 3-card grid — the shared intelligence-language motif */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          {cards.filter((c) => c.type !== "action").map((card, i) => (
            <InsightCard
              key={i}
              type={card.type}
              headline={card.headline}
              body={card.body}
              className={`fade-up-${i + 1}`}
            />
          ))}
        </div>

        {/* Your Move — full-width act-now card */}
        {actionCard && (
          <div
            className="rounded-md p-5 mb-6 fade-up-3"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderLeft: `3px solid ${action.color}`,
            }}
          >
            <div className="flex items-start gap-4">
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                style={{ background: `${action.color}14` }}
              >
                <Zap className="w-4 h-4" style={{ color: action.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <span className="label-caps" style={{ color: action.color }}>{action.label}</span>
                <h4 className="font-bold text-sm leading-snug mt-1 mb-1.5" style={{ color: "var(--text)" }}>
                  {actionCard.headline}
                </h4>
                <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
                  {actionCard.body}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* CTA */}
        <button
          onClick={onDismiss}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-md font-semibold text-sm transition-all hover:brightness-110"
          style={{ background: "var(--accent)", color: "var(--ink)" }}
        >
          View full analysis
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
