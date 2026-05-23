"use client";

import { Target, TrendingUp, Eye, Sparkles, ArrowRight } from "lucide-react";
import { type BriefCard } from "@/lib/api";

const CARD_CONFIG = {
  signal: {
    Icon: Target,
    color: "#a3f000",
    label: "Most notable signal",
    bg: "rgba(163,240,0,.08)",
    border: "rgba(163,240,0,.2)",
  },
  opportunity: {
    Icon: TrendingUp,
    color: "#60a5fa",
    label: "Your opening",
    bg: "rgba(96,165,250,.08)",
    border: "rgba(96,165,250,.2)",
  },
  watch: {
    Icon: Eye,
    color: "#facc15",
    label: "Watch this",
    bg: "rgba(250,204,21,.08)",
    border: "rgba(250,204,21,.2)",
  },
} as const;

interface Props {
  hostname: string;
  cards: BriefCard[];
  onDismiss: () => void;
}

export function IntelligenceBrief({ hostname, cards, onDismiss }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2">
        <Sparkles className="w-5 h-5 mt-0.5" style={{ color: "#a3f000" }} />
        <div>
          <h3 className="font-semibold" style={{ color: "var(--text)" }}>
            Intelligence Brief — {hostname}
          </h3>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            3 things you should know about this store right now
          </p>
        </div>
      </div>

      {cards.map((card, i) => {
        const config = CARD_CONFIG[card.type] ?? CARD_CONFIG.signal;
        const { Icon } = config;
        return (
          <div
            key={i}
            className="rounded-2xl p-5"
            style={{ background: config.bg, border: `1px solid ${config.border}` }}
          >
            <div className="flex items-start gap-3">
              <div
                className="rounded-lg p-2 shrink-0"
                style={{ background: `${config.color}18` }}
              >
                <Icon className="w-4 h-4" style={{ color: config.color }} />
              </div>
              <div>
                <span
                  className="text-[10px] font-bold uppercase tracking-wide"
                  style={{ color: config.color }}
                >
                  {config.label}
                </span>
                <h4
                  className="font-semibold text-sm mt-0.5"
                  style={{ color: "var(--text)" }}
                >
                  {card.headline}
                </h4>
                <p
                  className="text-sm mt-1 leading-relaxed"
                  style={{ color: "var(--muted)" }}
                >
                  {card.body}
                </p>
              </div>
            </div>
          </div>
        );
      })}

      <button
        onClick={onDismiss}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all hover:brightness-110"
        style={{ background: "#a3f000", color: "#060d18" }}
      >
        View full analysis
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
