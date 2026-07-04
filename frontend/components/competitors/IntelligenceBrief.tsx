"use client";

import { Target, TrendingUp, Eye, Zap, Sparkles, ArrowRight, X } from "lucide-react";
import { type BriefCard } from "@/lib/api";

const CARD_CONFIG = {
  signal: {
    Icon: Target,
    color: "#FFB224",
    label: "Notable Signal",
  },
  opportunity: {
    Icon: TrendingUp,
    color: "#FFB224",
    label: "Opportunity",
  },
  watch: {
    Icon: Eye,
    color: "#FFB224",
    label: "Watch Closely",
  },
  action: {
    Icon: Zap,
    color: "#4CC38A",
    label: "Your Move",
  },
} as const;

interface Props {
  hostname: string;
  cards: BriefCard[];
  onDismiss: () => void;
}

export function IntelligenceBrief({ hostname, cards, onDismiss }: Props) {
  return (
    <div
      className="rounded-2xl overflow-hidden mb-8 fade-in"
      style={{ background: "var(--bg3)", border: "1px solid var(--border)" }}
    >
      <div className="p-6 sm:p-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: "rgba(255,178,36,.10)", border: "1px solid var(--border)" }}
            >
              <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
            </div>
            <div>
              <span className="label-caps" style={{ color: "var(--accent)" }}>Scout Brief</span>
              <h3 className="text-sm font-bold mt-0.5" style={{ color: "var(--text)" }}>
                Scout Brief · <span style={{ color: "var(--text-2)" }}>{hostname}</span>
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

        {/* 3-card grid — hero layout */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          {cards.filter((c) => c.type !== "action").map((card, i) => {
            const config = CARD_CONFIG[card.type] ?? CARD_CONFIG.signal;
            const { Icon } = config;
            return (
              <div
                key={i}
                className={`rounded-xl p-5 fade-up-${i + 1}`}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderLeft: `3px solid ${config.color}`,
                }}
              >
                {/* Icon + label row */}
                <div className="flex items-center gap-2 mb-4">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                    style={{ background: `${config.color}14` }}
                  >
                    <Icon className="w-4 h-4" style={{ color: config.color }} />
                  </div>
                  <span className="label-caps" style={{ color: config.color }}>
                    {config.label}
                  </span>
                </div>

                {/* Content */}
                <h4 className="font-bold text-sm leading-snug mb-2" style={{ color: "var(--text)" }}>
                  {card.headline}
                </h4>
                <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
                  {card.body}
                </p>
              </div>
            );
          })}
        </div>

        {/* Action card — full-width, prominent */}
        {cards.find((c) => c.type === "action") && (() => {
          const actionCard = cards.find((c) => c.type === "action")!;
          const config = CARD_CONFIG.action;
          return (
            <div
              className="rounded-xl p-5 mb-6 fade-up-3"
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderLeft: `3px solid ${config.color}`,
              }}
            >
              <div className="flex items-start gap-4">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{ background: `${config.color}14` }}
                >
                  <Zap className="w-4 h-4" style={{ color: config.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="label-caps" style={{ color: config.color }}>
                    {config.label}
                  </span>
                  <h4 className="font-bold text-sm leading-snug mt-1 mb-1.5" style={{ color: "var(--text)" }}>
                    {actionCard.headline}
                  </h4>
                  <p className="text-sm leading-relaxed" style={{ color: "var(--muted)" }}>
                    {actionCard.body}
                  </p>
                </div>
              </div>
            </div>
          );
        })()}

        {/* CTA */}
        <button
          onClick={onDismiss}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all hover:brightness-110"
          style={{ background: "var(--accent)", color: "var(--ink)" }}
        >
          View full analysis
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
