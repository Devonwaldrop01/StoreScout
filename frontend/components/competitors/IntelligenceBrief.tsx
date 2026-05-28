"use client";

import { Target, TrendingUp, Eye, Zap, Sparkles, ArrowRight, X } from "lucide-react";
import { type BriefCard } from "@/lib/api";

const CARD_CONFIG = {
  signal: {
    Icon: Target,
    color: "#3b82f6",
    label: "Most notable signal",
    bg: "rgba(59,130,246,.07)",
    border: "rgba(59,130,246,.18)",
    glow: "rgba(59,130,246,.15)",
  },
  opportunity: {
    Icon: TrendingUp,
    color: "#60a5fa",
    label: "Your opening",
    bg: "rgba(96,165,250,.07)",
    border: "rgba(96,165,250,.18)",
    glow: "rgba(96,165,250,.15)",
  },
  watch: {
    Icon: Eye,
    color: "#f59e0b",
    label: "Watch this",
    bg: "rgba(245,158,11,.07)",
    border: "rgba(245,158,11,.18)",
    glow: "rgba(245,158,11,.15)",
  },
  action: {
    Icon: Zap,
    color: "#4ade80",
    label: "Your move",
    bg: "rgba(74,222,128,.07)",
    border: "rgba(74,222,128,.18)",
    glow: "rgba(74,222,128,.15)",
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
      className="relative rounded-2xl overflow-hidden mb-8 fade-in"
      style={{
        background: "linear-gradient(135deg, rgba(59,130,246,.06) 0%, rgba(59,130,246,.02) 40%, transparent 70%), var(--bg3)",
        border: "1px solid rgba(59,130,246,.2)",
        boxShadow: "0 0 0 1px rgba(59,130,246,.06), 0 20px 60px rgba(0,0,0,.5)",
      }}
    >
      {/* Ambient glow behind the card */}
      <div
        className="absolute -top-20 -left-20 w-64 h-64 rounded-full blur-3xl pointer-events-none"
        style={{ background: "rgba(59,130,246,.08)" }}
      />

      <div className="relative p-6 sm:p-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: "rgba(59,130,246,.12)", border: "1px solid rgba(59,130,246,.2)" }}
            >
              <Sparkles className="w-4 h-4" style={{ color: "var(--accent)" }} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span
                  className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
                  style={{ background: "rgba(59,130,246,.12)", color: "var(--accent)" }}
                >
                  AI Intelligence Brief
                </span>
              </div>
              <h3 className="text-base font-bold mt-1" style={{ color: "var(--text)" }}>
                {cards.length >= 4 ? "4" : "3"} things you should know about{" "}
                <span style={{ color: "var(--accent)" }}>{hostname}</span>
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
                className={`relative rounded-xl p-5 fade-up-${i + 1}`}
                style={{
                  background: config.bg,
                  border: `1px solid ${config.border}`,
                }}
              >
                {/* Card glow on hover — CSS only */}
                <div
                  className="absolute inset-0 rounded-xl opacity-0 transition-opacity duration-300 pointer-events-none hover:opacity-100"
                  style={{ boxShadow: `inset 0 0 30px ${config.glow}` }}
                />

                <div className="relative">
                  {/* Icon + label row */}
                  <div className="flex items-center gap-2 mb-4">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                      style={{ background: `${config.color}18` }}
                    >
                      <Icon className="w-4 h-4" style={{ color: config.color }} />
                    </div>
                    <span
                      className="text-[10px] font-bold uppercase tracking-wider"
                      style={{ color: config.color }}
                    >
                      {config.label}
                    </span>
                  </div>

                  {/* Content */}
                  <h4
                    className="font-bold text-sm leading-snug mb-2"
                    style={{ color: "var(--text)" }}
                  >
                    {card.headline}
                  </h4>
                  <p
                    className="text-sm leading-relaxed"
                    style={{ color: "var(--muted)" }}
                  >
                    {card.body}
                  </p>
                </div>
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
              className="relative rounded-xl p-5 mb-6 fade-up-3"
              style={{
                background: config.bg,
                border: `2px solid ${config.border}`,
              }}
            >
              <div className="flex items-start gap-4">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{ background: `${config.color}18` }}
                >
                  <Zap className="w-4 h-4" style={{ color: config.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <span
                    className="text-[10px] font-bold uppercase tracking-wider"
                    style={{ color: config.color }}
                  >
                    {config.label}
                  </span>
                  <h4
                    className="font-bold text-sm leading-snug mt-1 mb-1.5"
                    style={{ color: "var(--text)" }}
                  >
                    {actionCard.headline}
                  </h4>
                  <p
                    className="text-sm leading-relaxed"
                    style={{ color: "var(--muted)" }}
                  >
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
          style={{ background: "var(--accent)", color: "#ffffff" }}
        >
          View full analysis
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
